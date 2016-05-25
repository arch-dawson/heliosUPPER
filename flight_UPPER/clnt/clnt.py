
#!usr/bin/env python

import socket
import re
import os
import subprocess
import queue
import time

TCP_IP='192.168.1.234'
TCP_PORT= 8080
BUFFER_SIZE=1024
inputQ = queue.Queue()

def restart():
	command = "/usr/bin/sudo /sbin/shutdown -r now"
	process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)

def main(toLowerQ,capt_cmd):
	time.sleep(75)
	
	print("Trying to connect to Lover Pi")
	
	s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	s.connect((TCP_IP, TCP_PORT))

	message = "     Successful Connection to Upper Pi"

	s.send(message.encode())

	tempRe = re.compile('temp')
	
	cpuRe = re.compile('cpu')

	rebootRe = re.compile('reboot')

	pingRe = re.compile('ping')
	
	diskRe = re.compile('disk')

	fasterRe = re.compile('faster')

	slowerRe = re.compile('slower')

	while True:
		#Attempts to get data from connection, if successful adds to input queue	
		data=s.recv(BUFFER_SIZE).decode()
		data=data.lower()
		if len(data) > 0:
			inputQ.put(data)
		if not inputQ.empty():
			recieved = inputQ.get()
			if tempRe.search(recieved):
				output = os.popen('vcgencmd measure_temp').readline()
				toLowerQ.put('     ' + output)
			elif cpuRe.search(recieved):
				out = str(os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2}'").readline().strip())
				toLowerQ.put('     ' + out + "%")
			elif rebootRe.search(recieved):
				s.send('     Rebooting upper now'.encode())
				restart()
			elif diskRe.search(recieved):
				p=os.popen("df -h /")
				toLowerQ.put('\n' + p.readline() + p.readline())
			elif pingRe.search(recieved):
				toLowerQ.put('     RECIEVED COMMUNICATION')
			elif fasterRe.search(recieved):
				capt_cmd.put(2)
				toLowerQ.put("     Changed rate to 2")
			elif slowerRe.search(recieved):
				capt_cmd.put(5)
				toLowerQ.put("     Changed rate to 5")
			else:
				toLowerQ.put("     error")
			print("Recieved data: ", recieved)
		# If output is not empty
		if (toLowerQ.empty() == False):
		# Gets first item from output queue and sends to lower Pi	
			message = toLowerQ.get()
			s.send(message.encode())
	s.close()
	return 0
