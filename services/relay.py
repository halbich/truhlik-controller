import os
from pathlib import Path
from datetime import datetime, timezone

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
    relay.set_status(is_on)
    _touch_last_update()
    print(f"Relay {relay_id} is set to {is_on}")
    return relay.get_status_obj()


def get_relays_status():
    # returns a dict with last timestamp and the list of relays
    return {
        "last": get_last_update(),
        "relays": [
            relay.get_status_obj()
            for relay in Relay
        ]
    }
