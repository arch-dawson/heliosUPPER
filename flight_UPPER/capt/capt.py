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

import time
import math
import queue
import threading
import os.path as path
import shlex
from subprocess import Popen, PIPE
import subprocess
import re


imagesRe = re.compile('images')

class Cameras:	
	def __init__(self,toLowerQ):
		self.flight_count = 0
		self.current_count = 0
		self.queryTime = time.time()
		self.toLowerQ = toLowerQ	
		init_cmd = "v4l2-ctl --set-fmt-video=width=1600,height=1200,pixelformat='Y16 '"	
		Popen(shlex.split(init_cmd), stdout=PIPE).communicate()
		self.lock = threading.Lock()
		print("Finished initializing")
	
	def science(self):
		t = str(time.time())
		pic_cmd = "v4l2-ctl --stream-mmap=3 --stream-count=1 --stream-to=/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_" + t + ".jpg"
		with self.lock:
			subprocess.call(shlex.split(pic_cmd))
		result, err = Popen("ls /home/pi/heliosUPPER/flight_UPPER/capt/images/*.jpg | grep %s" % t, stdout=PIPE, shell=True).communicate()
		if result:
			self.flight_count += 1
			self.current_count += 1
			print("Took science picture with timestamp: " + t)
		return 

	def downlinkData(self):
		timeDiff = time.time() - self.queryTime
		timeDiffStr = "Time since last query, (hh:mm:ss) = %d:%d:%d" % math.floor(timeDiff/3600), math.floor((timeDiff%3600)/60), math.floor(timeDiff%60)
		outStr = "Flight pictures: %d\n %s \n Pictures since last Query: %d" % self.flight_count, timeDiffStr, self.current_count
		self.current_count = 0
		self.toLowerQ.put(outStr) 
		
		

def main(toLowerQ,capt_cmd, nightMode):
	print("Initializing Science Camera")
	camera = Cameras(toLowerQ)

	# Initialize initial photo capture rate
	capt_cmd.put(2)

	while(True):
		if not capt_cmd.empty():
			cmd = capt_cmd.get()
			if isinstance(cmd, int):
				rate = cmd
			elif imagesRe.search(cmd):
				camera.downlinkData()
		if not nightMode.is_set():
                        camera.science()
		time.sleep(rate)
