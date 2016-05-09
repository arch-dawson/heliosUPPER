#*********************************************************#
#   COSGC Presents										  #
#      __  __     ___               ____________		  #
#     / / / /__  / (_)___  _____   /  _/  _/  _/		  #
#    / /_/ / _ \/ / / __ \/ ___/   / / / / / /  		  #
#   / __  /  __/ / / /_/ (__  )  _/ /_/ /_/ /   		  #
#  /_/ /_/\___/_/_/\____/____/  /___/___/___/   		  #
#   													  #
#  Copyright (c) 2014 University of Colorado Boulder	  #
#  COSGC HASP Helios III Team							  #
#*********************************************************#

import threading
import logging
import queue

import os.path as path
import subprocess
import time

import random

capture_code = "/home/pi/hasp_temp/heliosUPPER/flight_UPPER/capt/a.out"
## Command line argument to change exposure will have to be included here

class Cameras():
	
	def __init__(self):
		subprocess.call([capture_code, "-t"])
		#logging.info("Initialized capture code")
		#print("successfully ran test")
		#self.adcs_path = "/dev/v4l/by-id/..."		#Paths need to be completed
		self.sci_path = "/dev/v4l/by-id/usb-The_Imaging_Source_Europe_GmbH_DMK_51BU02_4410256-video-index0"		
		self.lock = threading.Lock()
	
	def science(self):
		# Captures a science and an adcs image, naming them with the "Camera_hr-min-sec.png" convention 
		t = time.gmtime()
		#adcs_name = "/home/pi/hasp_temp/flight/images/ADCS_" + str(t[3]) + "-" + str(t[4]) + "-" + str(t[5]) + ".png"
		sci_name = "/home/pi/hasp_temp/heliosUPPER/flight_UPPER/capt/images/SCI_" +  str(random.randint(0, 2**32)) + ".png"
		with self.lock:
			subprocess.call([capture_code, "-d", self.sci_path, "-o", sci_name])
			#subprocess.call([capture_code, "-d", self.adcs_path, "-o", adcs_name])
		#logging.info("Captured " + sci_name)
		return sci_name
