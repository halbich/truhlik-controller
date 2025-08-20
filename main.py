#!/usr/bin/python
# -*- coding:UTF-8 -*-

import os
import socket
from gpiozero import DigitalOutputDevice
from bottle import route, run, request, static_file, get

from services.relay import Relay

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')


# GPIO setup
# Relay = [
#     DigitalOutputDevice(5, active_high=False),
#     DigitalOutputDevice(6, active_high=False),
#     DigitalOutputDevice(13, active_high=False),
#     DigitalOutputDevice(16, active_high=False),
#     DigitalOutputDevice(19, active_high=False),
#     DigitalOutputDevice(20, active_high=False),
#     DigitalOutputDevice(21, active_high=False),
#     DigitalOutputDevice(26, active_high=False),
# ]

# Static files
@route('/static/<filename:path>')
def serve_static(filename):
    return static_file(filename, root=STATIC_DIR)

@get("/")
def index():
    return static_file('index.html', root=STATIC_DIR)

@route('/<filename>')
def server_static(filename):
    return static_file(filename, root=STATIC_DIR)

# Relay control
@route('/Relay', method="POST")
def relay_control():
    for i in range(8):
        val = request.POST.get(f'Relay{i+1}')
        if val is not None:
            relay = Relay[i];
            print(f"{i}: {val}")
            if val == "0":
                relay.on()
            else:
                relay.off()
    return "OK"

# Determine local IP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8', 80))
    localhost = s.getsockname()[0]
finally:
    s.close()

# Run server
run(host=localhost, port=8080)
