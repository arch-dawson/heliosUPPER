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
# from capt import capture
import threading
import os.path as path
import subprocess

capture_code = "/home/pi/heliosUPPER/flight_UPPER/capt/a.out"

class Cameras:	
	def __init__(self,toLowerQ):
		self.toLowerQ = toLowerQ
		#subprocess.call([capture_code, "-t"])
		#logging.info("Initialized capture code")
		#print("successfully ran test")
		#self.adcs_path = "/dev/v4l/by-id/..."		#Paths need to be completed
		#self.sci_path = "/dev/v4l/by-id/usb-The_Imaging_Source_Europe_GmbH_DMK_23U274_17510268-video-index0"		
		subprocess.call(["v4l2-ctl", "--set-fmt-video=width=1600,height=1200,pixelformat='Y16 '"])
		self.lock = threading.Lock()
		print("Finished initializing")
	
	def science(self):
		# Captures a science and an adcs image, naming them with the "Camera_hr-min-sec.png" convention 
		#t = time.gmtime()
		t = str(time.time())
		#adcs_name = "/home/pi/hasp_temp/flight/images/ADCS_" + str(t[3]) + "-" + str(t[4]) + "-" + str(t[5]) + ".png"
		#sci_name = "/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_" +  str(random.randint(0, 2**32)) + ".png"
		#sci_name = "/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_" + t + ".png" 
		sci_name = "--stream-to=/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_" + t + ".jpg"
		#v4l2-ctl --stream-mmap=3 --stream-count=1 --stream-to=SUCCESS.jpg
		with self.lock:
			subprocess.call(['v4l2-ctl', '--stream-mmap=3', '--stream-count=1', sci_name])
		#with self.lock:
			#subprocess.call([capture_code, "-d", self.sci_path, "-o", sci_name])
			#subprocess.call([capture_code, "-d", self.adcs_path, "-o", adcs_name])
		#logging.info("Captured " + sci_name)
		#threading.Timer(10,science(self)).start()
		self.toLowerQ.put("Took Science picture with timestamp: " + t)
		print("Took science picture with timestamp: " + t)
		return #sci_name

def main(toLowerQ,rate):
	print("Initializing Science Camera")
	camera = Cameras(toLowerQ)
	# Initialize initial photo capture rate
	#rate = 10; 

	while(True):
		camera.science()
		time.sleep(rate)

