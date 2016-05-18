#!usr/bin/env python

import socket
import re
import os
import subprocess

TCP_IP='192.168.1.234'
TCP_PORT= 8080
BUFFER_SIZE=1024

def restart():
	command = "/usr/bin/sudo /sbin/shutdown -r now"
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)

def main(inputQ,outputQ):
	s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	s.connect((TCP_IP, TCP_PORT))

	tempRe = re.compile('temp')
	
	cpuRe = re.compile('cpu')

	rebootRe = re.compile('reboot')

	pingRe = re.compile('ping')
	
	diskRe = re.compile('disk')

	while True:
		#Attempts to get data from connection, if successful adds to input queue	
		data=s.recv(BUFFER_SIZE).decode()
		data=data.lower()
		if len(data) > 0:
			inputQ.put(data)
		if not inputQ.empty():
			recieved = inputQ.get()
			print(recieved)
			if tempRe.search(recieved):
				output = os.popen('vcgencmd measure_temp').readline()
				outputQ.put(output)
			elif cpuRe.search(recieved):
				out = str(os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2}'").readline().strip())
				outputQ.put(out+"%")
			elif rebootRe.search(recieved):
				s.send('Rebooting upper now'.encode())
				restart()
			elif diskRe.search(recieved):
				p=os.popen("df -h /")
				outputQ.put('\n' + p.readline() + p.readline())
			elif pingRe.search(recieved):
				outputQ.put('RECIEVED COMMUNICATION')
			else:
				outputQ.put("error")
			print("Recieved data: ", recieved)
		#if not data: break
		
		# If output is not empty
		if (outputQ.empty() == False):
		# Gets first item from output queue and sends to lower Pi	
			message = outputQ.get()
			s.send(message.encode())
#	if not data: break
#	print('recieved data:', data)
			#conn.send(data.encode())
	s.close()
	return 0
