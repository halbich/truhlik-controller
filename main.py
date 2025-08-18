#!/usr/bin/python
# -*- coding:UTF-8 -*-

import os
import socket
from gpiozero import DigitalOutputDevice
from bottle import route, run, request, static_file, get

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')


# GPIO setup
Relay = [
    DigitalOutputDevice(5),
    DigitalOutputDevice(6),
    DigitalOutputDevice(13),
    DigitalOutputDevice(16),
    DigitalOutputDevice(19),
    DigitalOutputDevice(20),
    DigitalOutputDevice(21),
    DigitalOutputDevice(26),
]

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
                relay.off()
            else:
                relay.on()
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
