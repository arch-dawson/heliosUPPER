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
import queue
import threading
import os.path as path
import subprocess
import shlex


class Cameras:	
	def __init__(self,toLowerQ):
		self.toLowerQ = toLowerQ
		#self.sci_path = "/dev/v4l/by-id/usb-The_Imaging_Source_Europe_GmbH_DMK_23U274_17510268-video-index0"	
		init_cmd = "v4l2-ctl --set-fmt-video=width=1600,height=1200,pixelformat='Y16 '"	
		subprocess.call(shlex.split(init_cmd))
		self.lock = threading.Lock()
		print("Finished initializing")
	
	def science(self):
		t = str(time.time())
		pic_cmd = "v4l2-ctl --stream-mmap=3 --stream-count=1 --stream-to=/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_" + t + ".jpg"
		#sci_name = "--stream-to=/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_" + t + ".jpg"
		with self.lock:
			subprocess.call(shlex.split(pic_cmd))
		#self.toLowerQ.put("Took Science picture with timestamp: " + t)
		print("Took science picture with timestamp: " + t)
		return 

def main(toLowerQ,capt_cmd):
	print("Initializing Science Camera")
	camera = Cameras(toLowerQ)

	# Initialize initial photo capture rate
	capt_cmd.put(2)

	while(True):
		if not capt_cmd.empty():
			rate = capt_cmd.get()
		camera.science()
		time.sleep(rate)

