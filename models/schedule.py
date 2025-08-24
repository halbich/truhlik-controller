from typing import Dict, Optional, List, Any, Union


class ScheduleSlot:
    def __init__(self, on: Union[str, int], off: Union[str, int], disabled: bool = False):
        # Internally store minutes since midnight for fast checks
        self.on_min = self._parse_hhmm(on)
        self.off_min = self._parse_hhmm(off)
        self.disabled = disabled

    @staticmethod
    def _parse_hhmm(value: Union[str, int]) -> int:
        if isinstance(value, int):
            if 0 <= value <= 1439:
                return value
            raise ValueError(f"Invalid minutes value: {value}")
        parts = str(value).strip().split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid time format: {value}")
        h = int(parts[0])
        m = int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"Invalid time value: {value}")
        return h * 60 + m

    @staticmethod
    def _format_hhmm(mins: int) -> str:
        if not (0 <= mins <= 1439):
            mins = 0
        h = mins // 60
        m = mins % 60
        return f"{h}:{m:02d}"

    def to_dict(self) -> Dict[str, Any]:
        # Emit strings for JSON compatibility
        return {"on": self._format_hhmm(self.on_min), "off": self._format_hhmm(self.off_min), "disabled": bool(self.disabled)}

    def is_now_in_interval(self, now_min: int) -> bool:
        # Return True if now_min is within [on_min, off_min), handling overnight spans
        on_min = self.on_min
        off_min = self.off_min
        if on_min == off_min:
            return False
        if on_min < off_min:
            return on_min <= now_min < off_min
        # overnight (e.g. 22:00-06:00)
        return now_min >= on_min or now_min < off_min


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
