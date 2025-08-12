#!/usr/bin/python
# -*- coding:UTF-8 -*-

from bottle import *

import socket

from services.relay import init_relay, set_relay

#All the relay
Relay1 = 1
Relay2 = 1
Relay3 = 1
Relay4 = 1
Relay5 = 1
Relay6 = 1
Relay7 = 1

init_relay()


@get("/")
def index():
  global Relay1,Relay2,Relay3,Relay4,Relay5,Relay6,Relay7
  
  Relay1 = 1
  Relay2 = 1
  Relay3 = 1
  Relay4 = 1
  Relay5 = 1
  Relay6 = 1
  Relay7 = 1

  return static_file('index.html', './')

@route('/<filename>')
def server_Static(filename):
    return static_file(filename, root='./')

@route('/Relay', method="POST")
def Relay_Control():
  global Relay1,Relay2,Relay3,Relay4,Relay5,Relay6,Relay7
  
  Relay1 = request.POST.get('Relay1')
  Relay2 = request.POST.get('Relay2')
  Relay3 = request.POST.get('Relay3')
  Relay4 = request.POST.get('Relay4')
  Relay5 = request.POST.get('Relay5')
  Relay6 = request.POST.get('Relay6')
  Relay7 = request.POST.get('Relay7')

  set_relay(0, int(Relay1) == 0)
  set_relay(1, int(Relay2) == 0)
  set_relay(2, int(Relay3) == 0)
  set_relay(3, int(Relay4) == 0)
  set_relay(4, int(Relay5) == 0)
  set_relay(5, int(Relay6) == 0)
  set_relay(6, int(Relay7) == 0)

  
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(('8.8.8.8', 80))
localhost = s.getsockname()[0]

run(host=localhost, port="8080")

