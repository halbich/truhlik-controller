import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from gpiozero import DigitalOutputDevice

from services.config import get_config


# GPIO Pin


status_path = get_config().get("status_path", ".")

# Local in-memory timestamp (UTC ms) of the last successful update
_last_update_ms: int = 0


def _utc_now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def get_last_update() -> int:
    return _last_update_ms


def _touch_last_update() -> None:
    global _last_update_ms
    _last_update_ms = _utc_now_ms()


class RelayInstance:
    def __init__(self, relay_id: int, description: str = ""):
        self.relay_id = relay_id
        self.dod = DigitalOutputDevice(relay_id, active_high=False)
        if len(description) <= 0:
            description = f"Relé {relay_id}"
        self.description = description

    def get_file_path(self):
        return f"{status_path}/{self.relay_id}.status"

    def get_status(self):
        path = self.get_file_path()
        if not os.path.exists(path):
            self.set_status(False)
            return False
        with open(path, "r") as f:
            return f.read() == "1"

    def set_status(self, is_on: bool):
        path = self.get_file_path()

        if is_on:
            self.dod.on()
        else:
            self.dod.off()

        with open(path, "w") as f:
            f.write("1" if is_on else "0")

    def init_relay(self):
        status = self.get_status()
        self.set_status(status)

    def get_status_obj(self) -> dict:
        return {
            "id": self.relay_id,
            "description": self.description,
            "status": self.get_status(),
        }


Relay = [
    RelayInstance(6, "Voda"),
    RelayInstance(13, "Filtrace"),
    RelayInstance(16, "UV lampa"),
    RelayInstance(19),
    RelayInstance(20),
    RelayInstance(21),
    RelayInstance(26),
]
RelayIndexed = {r.relay_id: r for r in Relay}


def init_relay():
    print(f"Status path: {status_path}")
    Path(status_path).mkdir(parents=True, exist_ok=True)
    for relay in Relay:
        relay.init_relay()
    # after initialization, set the last update to now
    _touch_last_update()


def set_relay(relay_id: int, is_on: bool) -> dict:
    relay = RelayIndexed[relay_id]
    current = relay.get_status()
    if current == is_on:
        # No change needed; do not update hardware or timestamp
        print(f"Relay {relay_id} already {'ON' if is_on else 'OFF'}; no action taken")
        return relay.get_status_obj()
    # Apply change and touch last update
    relay.set_status(is_on)
    _touch_last_update()
    print(f"Relay {relay_id} is set to {is_on}")
    return relay.get_status_obj()


def _parse_hhmm(value: str) -> int:
    """
    Parses 'HH:MM' or 'H:MM' strings into minutes since midnight (0-1439).
    Raises ValueError on invalid input.
    """
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {value}")
    h = int(parts[0])
    m = int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Invalid time value: {value}")
    return h * 60 + m


def _is_now_in_interval(now_min: int, on_min: int, off_min: int) -> bool:
    """
    Returns True if now_min is within [on_min, off_min) considering intervals that may cross midnight.
    """
    if on_min == off_min:
        # zero-length interval, never on
        return False
    if on_min < off_min:
        return on_min <= now_min < off_min
    # overnight interval e.g., 22:00-06:00
    return now_min >= on_min or now_min < off_min


def _load_schedule() -> Dict[str, List[Dict[str, Any]]]:
    cfg = get_config()
    schedule_path = cfg.get("schedule_json", ".schedule.json")
    if not os.path.exists(schedule_path):
        return {}
    with open(schedule_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Ensure structure is dict of relay_id -> list of intervals
    if not isinstance(data, dict):
        return {}
    return data


def _save_schedule(schedule_obj: Dict[str, Any]) -> None:
    cfg = get_config()
    schedule_path = cfg.get("schedule_json", ".schedule.json")
    with open(schedule_path, "w", encoding="utf-8") as f:
        json.dump(schedule_obj, f, ensure_ascii=False, indent=2)


def update_schedule_span(relay_id: int, span_index: int, is_on: bool) -> Dict[str, Any]:
    """
    Update a schedule span's disabled flag for a given relay.
    is_on=True means the span is enabled (disabled=False). is_on=False disables the span.
    Returns a dict with updated relay spans and last timestamp.
    """
    schedule_obj = _load_schedule()
    key = str(relay_id)
    spans = schedule_obj.get(key, [])
    if not isinstance(spans, list):
        spans = []
    # Ensure span exists
    if 0 <= span_index < len(spans):
        span = spans[span_index] or {}
        # maintain on/off keys
        if not isinstance(span, dict):
            span = {}
        span["disabled"] = (not is_on)
        spans[span_index] = span
    else:
        # out of range: no-op
        pass
    schedule_obj[key] = spans
    _save_schedule(schedule_obj)
    _touch_last_update()
    return {"relay_id": relay_id, "spans": spans, "last": get_last_update()}


def check_schedule(now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Check the schedule file and set relays accordingly.
    - Reads schedule path from config 'schedule_json'.
    - For each relay ID key, determines if current time is within any interval.
    - Calls set_relay for that relay to achieve desired state.
    Returns a summary dict with actions taken.
    """
    cfg = get_config()
    schedule_path = cfg.get("schedule_json", ".schedule.json")
    result: Dict[str, Any] = {
        "schedule_path": schedule_path,
        "exists": os.path.exists(schedule_path),
        "processed": [],
        "errors": [],
    }
    if not result["exists"]:
        result["message"] = "Schedule file not found"
        return result

    try:
        schedule_obj = _load_schedule()
    except Exception as e:
        result["errors"].append(f"Failed to read schedule: {e}")
        return result

    # Determine current local time in minutes (assuming schedule is in local time)
    now_dt = now_utc.astimezone() if now_utc else datetime.now().astimezone()
    now_min = now_dt.hour * 60 + now_dt.minute

    for relay_id_str, intervals in schedule_obj.items():
        try:
            relay_id = int(relay_id_str)
        except Exception:
            result["errors"].append(f"Invalid relay id key: {relay_id_str}")
            continue

        if relay_id not in RelayIndexed:
            result["errors"].append(f"Unknown relay id: {relay_id}")
            continue

        desired_on = False
        try:
            if isinstance(intervals, list):
                for it in intervals:
                    # Skip if explicitly disabled
                    if isinstance(it, dict) and it.get("disabled") is True:
                        continue
                    on_s = it.get("on") if isinstance(it, dict) else None
                    off_s = it.get("off") if isinstance(it, dict) else None
                    if not isinstance(on_s, str) or not isinstance(off_s, str):
                        continue
                    on_min = _parse_hhmm(on_s)
                    off_min = _parse_hhmm(off_s)
                    if _is_now_in_interval(now_min, on_min, off_min):
                        desired_on = True
                        break
            else:
                result["errors"].append(f"Invalid intervals for relay {relay_id}")
        except Exception as e:
            result["errors"].append(f"Relay {relay_id} parse error: {e}")

        before = RelayIndexed[relay_id].get_status()
        state_obj = set_relay(relay_id, desired_on)
        after = state_obj.get("status", after if (after := desired_on) is not None else desired_on)
        changed = before != after
        result["processed"].append({
            "id": relay_id,
            "desired": desired_on,
            "before": before,
            "after": after,
            "changed": changed,
        })

    result["last"] = get_last_update()
    result["now"] = now_dt.isoformat()
    return result


def _compute_active_now(span: Dict[str, Any], now_dt: Optional[datetime] = None) -> bool:
    if not isinstance(span, dict):
        return False
    if span.get("disabled") is True:
        return False
    on_s = span.get("on")
    off_s = span.get("off")
    if not isinstance(on_s, str) or not isinstance(off_s, str):
        return False
    now = now_dt or datetime.now().astimezone()
    now_min = now.hour * 60 + now.minute
    try:
        return _is_now_in_interval(now_min, _parse_hhmm(on_s), _parse_hhmm(off_s))
    except Exception:
        return False


def get_relays_status():
    # returns a dict with last timestamp and the list of relays, including schedule spans
    schedule_obj = _load_schedule()
    now = datetime.now().astimezone()
    relays_payload = []
    for relay in Relay:
        base = relay.get_status_obj()
        key = str(relay.relay_id)
        spans_raw = schedule_obj.get(key, [])
        spans = []
        if isinstance(spans_raw, list):
            for it in spans_raw:
                if isinstance(it, dict):
                    spans.append({
                        "on": it.get("on"),
                        "off": it.get("off"),
                        "disabled": bool(it.get("disabled", False)),
                        "active_now": _compute_active_now(it, now)
                    })
        base["spans"] = spans
        relays_payload.append(base)
    return {
        "last": get_last_update(),
        "relays": relays_payload
    }
