import os
from pathlib import Path

import RPi.GPIO as GPIO
from gpiozero import DigitalOutputDevice

from services.config import get_config


# GPIO Pin


status_path = get_config().get("status_path", ".")

class RelayInstance:
    def __init__(self, relay_id: int, description: str = ""):
        self.relay_id = relay_id
        self.dod = DigitalOutputDevice(relay_id, active_high=False)
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


Relay = [
    RelayInstance(5),  # TODO delete me later
    RelayInstance(6),
    RelayInstance(13),
    RelayInstance(16),
    RelayInstance(19),
    RelayInstance(20),
    RelayInstance(21),
    RelayInstance(26),
]


def init_relay():
    print(f"Status path: {status_path}")
    Path(status_path).mkdir(parents=True, exist_ok=True)
    for relay in Relay:
        relay.init_relay()


def set_relay(relay_id: int, is_on: bool):
    Relay[relay_id].set_status(is_on)
    print(f"Relay {relay_id} is set to {is_on}")


def get_relays_status():
    return [
        {
            "id": relay.relay_id,
            "description": relay.description,
            "status": relay.get_status(),
        }
        for relay in Relay
    ]
