#!usr/bin/env python

import socket
import time

TCP_IP = '192.168.1.234'
TCP_PORT = 8080
BUFFER_SIZE = 1024


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
while True:
	MESSAGE = input('Enter the thing: ')
	s.send(MESSAGE.encode())
	data = s.recv(BUFFER_SIZE).decode()
	print("Acquired: ",data)
