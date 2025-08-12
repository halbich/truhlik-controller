import RPi.GPIO as GPIO

#GPIO Pin
Relay = [6, 13, 16, 19, 20, 21, 26] # 5 is first, but it is reserved


def init_relay():
    # GPIO init
    GPIO.setmode(GPIO.BCM)

    for i in range(len(Relay)):
        GPIO.setup(Relay[i], GPIO.OUT)
        GPIO.output(Relay[i], GPIO.HIGH)

def set_relay(relay_id: int, is_on: bool):
    GPIO.output(Relay[relay_id], GPIO.LOW if is_on else GPIO.HIGH)