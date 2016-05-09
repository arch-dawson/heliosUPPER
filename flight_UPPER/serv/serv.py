#!usr/bin/env python

import socket

TCP_IP='192.168.1.230'
TCP_PORT= 8080
BUFFER_SIZE=1024
def main(input, output):
	s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	# Uncomment this line when actually running
	#s.bind((TCP_IP, TCP_PORT))

	s.listen(1)

	conn, addr = s.accept()
	print('Connection address:', addr)
	while True:
		#Attempts to get data from connection, if successful adds to input queue	
		data=conn.recv(BUFFER_SIZE).decode()
		input.put(data)
		#if not data: break
		
		# If output is not empty
		if (output.empty() == false):
			# Gets first item from output queue and sends to lower Pi	
			message = output.get()
			conn.send(message.encode())
	conn.close()
	return 0
