import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union

from gpiozero import DigitalOutputDevice

from services.config import get_config


# New schedule data structures
class ScheduleSlot:
    def __init__(self, on: str, off: str, disabled: bool = False):
        self.on = on
        self.off = off
        self.disabled = disabled

    def to_dict(self) -> Dict[str, Any]:
        return {"on": self.on, "off": self.off, "disabled": bool(self.disabled)}


class RelaySchedule:
    def __init__(self, manual_mode: bool = False, time_slots: Optional[List[ScheduleSlot]] = None):
        self.manual_mode = manual_mode
        self.time_slots = time_slots or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manual_mode": bool(self.manual_mode),
            "time_slots": [slot.to_dict() for slot in (self.time_slots or [])]
        }


class Schedule:
    def __init__(self, relays: Optional[Dict[str, RelaySchedule]] = None):
        self.relays = relays or {}

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, rs in (self.relays or {}).items():
            out[key] = rs.to_dict()
        return out


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
    # RelayInstance(5), #controlled by hardware, not though GPIO
    RelayInstance(6, "Voda"),
    RelayInstance(13, "Filtrace"),
    RelayInstance(16, "UV lampa"),
    # RelayInstance(19),  don't need it now
    # RelayInstance(20),  don't need it now
    # RelayInstance(21),  don't need it now
    # RelayInstance(26),  don't need it now
]
RelayIndexed: dict[str, RelayInstance] = {str(r.relay_id): r for r in Relay}


def init_relay():
    print(f"Status path: {status_path}")
    Path(status_path).mkdir(parents=True, exist_ok=True)
    for relay in Relay:
        relay.init_relay()
    # after initialization, set the last update to now
    _touch_last_update()


def set_relay(relay_id: str, is_on: bool) -> dict:
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


def _get_now_min(now_utc: Optional[datetime] = None) -> (datetime, int):
    now_dt = now_utc.astimezone() if now_utc else datetime.now().astimezone()
    now_min = now_dt.hour * 60 + now_dt.minute
    return now_dt, now_min


def _load_schedule() -> Schedule:
    cfg = get_config()
    schedule_path = cfg.get("schedule_json", ".schedule.json")
    if not os.path.exists(schedule_path):
        return Schedule()
    with open(schedule_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    have_to_save = False
    # Upgrade legacy format and construct objects:
    relays: Dict[str, RelaySchedule] = {}
    if isinstance(raw, dict):
        for key, val in raw.items():
            # Legacy: list of slots -> wrap to object
            if isinstance(val, list):
                have_to_save = True
                slots: List[ScheduleSlot] = []
                for it in val:
                    if isinstance(it, dict):
                        on_s = it.get("on")
                        off_s = it.get("off")
                        if isinstance(on_s, str) and isinstance(off_s, str):
                            disabled_flag = bool(it.get("disabled", False))
                            slots.append(ScheduleSlot(on_s, off_s, disabled_flag))
                relays[key] = RelaySchedule(False, slots)
            elif isinstance(val, dict):
                # New format already
                manual = bool(val.get("manual_mode", False))
                slots_list = val.get("time_slots", [])
                slots: List[ScheduleSlot] = []
                if isinstance(slots_list, list):
                    for it in slots_list:
                        if isinstance(it, dict):
                            on_s = it.get("on")
                            off_s = it.get("off")
                            if isinstance(on_s, str) and isinstance(off_s, str):
                                disabled_flag = bool(it.get("disabled", False))
                                slots.append(ScheduleSlot(on_s, off_s, disabled_flag))
                relays[key] = RelaySchedule(manual, slots)
            else:
                # Unknown type; skip or initialize empty
                relays[key] = RelaySchedule(False, [])

    result = Schedule(relays)

    if have_to_save:
        _save_schedule(result)
    return result


def _save_schedule(schedule: Schedule) -> None:

    payload = schedule.to_dict()
    cfg = get_config()
    schedule_path = cfg.get("schedule_json", ".schedule.json")
    with open(schedule_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)



def update_schedule_span(relay_id: int, span_index: int, is_on: bool) -> Dict[str, Any]:
    """
    Update schedule span's enabled/disabled state for given relay and span index.
    is_on=True means the span should be enabled (disabled=False), and vice versa.
    Returns a dict with updated relay schedule info.
    """
    schedule = _load_schedule()
    key = str(relay_id)
    rs = schedule.relays.get(key)
    if rs is None or not isinstance(rs, RelaySchedule):
        raise ValueError("Relay has no schedule")
    spans = rs.time_slots
    if not (0 <= span_index < len(spans)):
        raise IndexError("span_index out of range")
    slot = spans[span_index]
    if not isinstance(slot, ScheduleSlot):
        raise ValueError("Invalid span format")
    # Set disabled opposite to is_on
    slot.disabled = (not is_on)
    _save_schedule(schedule)
    _touch_last_update()
    # Return minimal info
    now_dt, now_min = _get_now_min(None)

    def span_view(s: ScheduleSlot) -> Dict[str, Any]:
        try:
            active = _is_now_in_interval(now_min, _parse_hhmm(s.on), _parse_hhmm(s.off))
        except Exception:
            active = False
        return {"on": s.on, "off": s.off, "disabled": bool(s.disabled), "active_now": active}

    return {
        "relay_id": relay_id,
        "spans": [span_view(s) for s in spans]
    }


def check_schedule(now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Check the schedule and set relays accordingly using the Schedule structure.
    - Loads schedule via _load_schedule (no direct file reads here).
    - For each relay ID key, determines if current time is within any enabled interval.
    - Respects manual_mode by skipping automatic changes for that relay.
    - Calls set_relay for that relay to achieve desired state when applicable.
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

    # Load schedule using the loader (handles current and legacy formats)
    schedule = _load_schedule()

    # Determine current local time in minutes (assuming schedule is in local time)
    now_dt, now_min = _get_now_min(now_utc)

    for relay_id, relay_schedule in schedule.relays.items():

        if relay_id not in RelayIndexed:
            continue

        desired_on = False
        skip_apply = False
        try:

            # Respect manual mode: skip automatic changes
            if relay_schedule.manual_mode:
                skip_apply = True
            else:
                active_enabled = False
                active_disabled = False
                for slot in relay_schedule.time_slots or []:
                    on_min = _parse_hhmm(slot.on)
                    off_min = _parse_hhmm(slot.off)
                    if _is_now_in_interval(now_min, on_min, off_min):
                        if slot.disabled:
                            active_disabled = True
                        else:
                            active_enabled = True
                            break
                if active_enabled:
                    desired_on = True
                elif active_disabled:
                    skip_apply = True
        except Exception as e:
            result["errors"].append(f"Relay {relay_id} parse error: {e}")

        before = RelayIndexed[relay_id].get_status()
        if skip_apply:
            after = before
            changed = False
        else:
            state_obj = set_relay(relay_id, desired_on)
            after = state_obj.get("status", desired_on)
            changed = before != after
        result["processed"].append({
            "id": relay_id,
            "desired": desired_on,
            "before": before,
            "after": after,
            "changed": changed,
            "skipped": skip_apply,
            "manual_mode": relay_schedule.manual_mode,
        })

    result["last"] = get_last_update()
    result["now"] = now_dt.isoformat()
    return result


def get_relays_status():
    # returns a dict with last timestamp and the list of relays incl. schedule spans (new structure)
    schedule = _load_schedule()
    now_dt, now_min = _get_now_min(None)
    rels = []
    for relay in Relay:
        obj = relay.get_status_obj()
        spans_view: List[Dict[str, Any]] = []
        rs = schedule.relays.get(str(relay.relay_id), RelaySchedule())
        for slot in rs.time_slots:
            try:
                active = _is_now_in_interval(now_min, _parse_hhmm(slot.on), _parse_hhmm(slot.off))
            except Exception:
                active = False
            spans_view.append({
                "on": slot.on,
                "off": slot.off,
                "disabled": bool(slot.disabled),
                "active_now": active
            })
        obj["schedule"] = spans_view
        obj["manual_mode"] = bool(rs.manual_mode)
        rels.append(obj)
    return {
        "last": get_last_update(),
        "relays": rels
    }
