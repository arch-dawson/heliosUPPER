# *********************************************************#
#   COSGC Presents										   #
#      __  __________    ________  _____   __    __        #
#     / / / / ____/ /   /  _/ __ \/ ___/   | |  / /        #
#    / /_/ / __/ / /    / // / / /\__ \    | | / /         #
#   / __  / /___/ /____/ // /_/ /___/ /    | |/ /          #
#  /_/ /_/_____/_____/___/\____//____/     |___/           #  
#                                                          #
#   													   #
#  Copyright (c) 2016 University of Colorado Boulder	   #
#  COSGC HASP Helios V Team							       #
# *********************************************************#

import socket
import re
import os
import subprocess
import queue
import time
import threading

TCP_IP='192.168.1.234'
TCP_PORT= 8080
BUFFER_SIZE=1024
inputQ = queue.Queue() # What clnt has received

tempRe = re.compile('temp')
cpuRe = re.compile('cpu')
rebootRe = re.compile('reboot')
pingRe = re.compile('ping')
diskRe = re.compile('disk')
fasterRe = re.compile('faster')
slowerRe = re.compile('slower')
imageRe = re.compile('image')
nightRe = re.compile('night')

class Client():
	def __init__(self, toLowerQ, capt_cmd, nightMode):
		self.toLowerQ = toLowerQ
		self.capt_cmd = capt_cmd
		self.nightMode = nightMode
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self.connect()
		
		self.flight()

	def connectCMD(self):
		try:
			self.s.connect((TCP_IP, TCP_PORT))
		except:
			return False
		return True

	def connect(self):
		print("Trying to connect to Lover Pi")
		res = self.connectCMD()
		while not res:
			time.sleep(5)
			res = self.connectCMD()
		print("Successfully united with Lover")
		return

	def restart(self):
		command = "/usr/bin/sudo /sbin/shutdown -r now"
		process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)

		self.s.close()

	def command(self, received):
		if tempRe.search(recieved):
			output = os.popen('vcgencmd measure_temp').readline()
			self.toLowerQ.put('     ' + output)
		elif cpuRe.search(recieved):
			out = str(os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2}'").readline().strip())
			self.toLowerQ.put('     ' + out + "%")
		elif rebootRe.search(recieved):
			self.s.send('     Rebooting upper now'.encode())
			threading.Timer(5.0, self.restart).start()
		elif diskRe.search(recieved):
			p=os.popen("df -h /")
			self.toLowerQ.put('\n' + p.readline() + p.readline())
		elif pingRe.search(recieved):
			self.toLowerQ.put('     RECIEVED COMMUNICATION')
		elif fasterRe.search(recieved):
			self.capt_cmd.put(2)
			self.toLowerQ.put("     Changed rate to 2")
		elif slowerRe.search(recieved):
			self.capt_cmd.put(5)
			self.toLowerQ.put("     Changed rate to 5")
		elif imageRe.search(recieved):
			self.capt_cmd.put('images')
		elif nightRe.search(received): # Toggles night mode
			if self.nightMode.is_set():
				self.nightMode.clear()
				self.toLowerQ.put("     Turned Upper Pi night mode OFF")
			else:
				self.nightMode.set()
				self.toLowerQ.put("     Turned Upper Pi night mode ON")
		else:
			self.toLowerQ.put("     error")
		print("Recieved data: ", recieved)

	def heartBeat(self):
		self.toLowerQ.put("Heartbeat <3")

	def flight(self):
		timer = 0 # Keep track of time since received last heartbeat
		while True:
			try: # Can crash thread if receive fails
				data = self.s.recv(BUFFER_SIZE).decode()
			except:
				timer = 0
				self.connect()
			data = data.lower() # All lower case
			if len(data) > 0:
				inputQ.put(data)
				self.heartBeat()
				timer = 0
			else:
				time.sleep(1)
				timer += 1
				if timer > 15: # Haven't gotten a heartbeat!
					self.connect()
			if not inputQ.empty():
				received = inputQ.get()
			while not self.toLowerQ.empty():
				message = self.toLowerQ.get()
				print("Sending message to Lover Pi")
				self.s.send(message.encode())
                        

def main(toLowerQ,capt_cmd, nightMode):
	connection = Client(toLowerQ,capt_cmd, nightMode)
