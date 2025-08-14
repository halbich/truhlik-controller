#!/usr/bin/python
# -*- coding:UTF-8 -*-

import os
import socket
import RPi.GPIO as GPIO
from bottle import route, run, request, static_file, get

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')


# GPIO setup
Relay = [5, 6, 13, 16, 19, 20, 21, 26]
RelayState = [1]*8

GPIO.setmode(GPIO.BCM)
for i in range(8):
    GPIO.setup(Relay[i], GPIO.OUT)
    GPIO.output(Relay[i], GPIO.HIGH)

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
            RelayState[i] = int(val)
            GPIO.output(Relay[i], RelayState[i])
    return "OK"

# Determine local IP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    s.connect(('8.8.8.8', 80))
    localhost = s.getsockname()[0]
finally:
    s.close()

# Run server
run(host=localhost, port=8080, debug=True)
