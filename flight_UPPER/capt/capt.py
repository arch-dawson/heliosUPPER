# *********************************************************#
#   COSGC Presents                                                                                 #
#      __  __________    ________  _____   __    __        #
#     / / / / ____/ /   /  _/ __ \/ ___/   | |  / /        #
#    / /_/ / __/ / /    / // / / /\__ \    | | / /         #
#   / __  / /___/ /____/ // /_/ /___/ /    | |/ /          #
#  /_/ /_/_____/_____/___/\____//____/     |___/           #
#                                                          #
#                                                                                                          #
#  Copyright (c) 2016 University of Colorado Boulder       #
#  COSGC HASP Helios V Team                                                            #
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
import array
import numpy as np


imagesRe = re.compile('images')
expRe = re.compile('exposure')
expDRe = re.compile('expDown')
expURe = re.compile('expUp')

pixelVals = {x:0 for x in range(0,65536,12)}

class Cameras:
    def __init__(self,toLowerQ, biasVals):
        # Counts for picture query command
        self.flight_count = 0
        self.initTime = time.time()
        self.toLowerQ = toLowerQ
        self.biasVals = biasVals
        self.exposure = 1000

        # Setting up the science camera initial set-up.  If more settings are needed, change here.
        init_cmd = "v4l2-ctl --set-ctrl=exposure_absolute={0} --set-fmt-video=width=1600,height=1200,pixelformat='Y16 '".format(self.exposure)
        Popen(shlex.split(init_cmd), stdout=PIPE).communicate()

        self.lock = threading.Lock()
        print("Finished initializing science camera")

    def science(self): # Takes a science picture
        self.t = str(time.time())
        # Long command to actually take the picture
        pic_cmd = "v4l2-ctl --stream-mmap=3 --stream-count=1 --stream-to=/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_" + self.t + "_" + str(self.exposure) + ".raw"

        with self.lock: # Forget why this was important...
            subprocess.call(shlex.split(pic_cmd))
        # Comfirm that the picture was actually taken by checking the folder
        result, err = Popen("ls /home/pi/heliosUPPER/flight_UPPER/capt/images/*.raw | grep %s" % self.t, stdout=PIPE, shell=True).communicate()
        if result:
            self.flight_count += 1
            print("Took science picture with timestamp: " + self.t)
            return True
        return False
        
    def mode(arr):
        for item in arr:
            pixelVals[item] += 1

        max = 0
        
        for val in pixelVals.keys():
            if pixelVals[val] > max:
                max = pixelVals[val]
                maxIndex = val
        return maxIndex

    def exposureAnalysis(self):
        img = open('/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_' + self.t + "_" + str(self.exposure) + '.raw','rb')

        valArray = array.array('H') # H is code for unsigned short. Obviously

        valArray.fromfile(img, 1200*1600)

        img.close()

        npArray = np.frombuffer(valArray, dtype='u2') # u2 says 2 byte unsigned
        
        npArray = np.sort(npArray)
        
        npArray = npArray[(len(npArray)//10):]
        
        self.toLowerQ.put(self.mode(npArray))  

        return
        
    def changeExposure(self, expChange):
        cmd = "v4l2-ctl --set-ctrl=exposure_absolute={0} --set-fmt-video=width=1600,height=1200,pixelformat='Y16 '".format(self.exposure + expChange)
        Popen(shlex.split(init_cmd), stdout=PIPE).communicate()
        
        return

    def downlinkData(self): # If lower Pi wants picture status.  Strings are pretty self-explanatory
        timeDiff = time.time() - self.initTime
        outStr = "{0} {1}".format(timeDiff, self.flight_count)
        self.toLowerQ.put(outStr)
        return
        
    def updateBias(self):
        img = open('/home/pi/heliosUPPER/flight_UPPER/capt/images/SCI_' + self.t + "_" + str(self.exposure) + '.raw','rb')

        valArray = array.array('H') # H is code for unsigned short. Obviously

        valArray.fromfile(img, 1200*1600)

        img.close()
        
        npArray = np.frombuffer(valArray, dtype='u2') # u2 says 2 byte unsigned
        
        npArray.reshape(1200,1600)
        
        xSum = 0
        ySum = 0
        
        # Summing up the edges of the array.
        # Double counts corners but doesn't really matter
        
        for a in (0,1199):
            for b in range(0,799):
                xSum -= npArray[a,b]
            for c in range(800,1599):
                xSum += npArray[a,c]
                
        for a in (0,1599): # a is the column now
            for b in range(0,599):
                ySum += npArray[b,a]
            for c in range(600,1199):
                ySum -= npArray[c,a]
        
        xSum /= 5600
        ySum /= 5600
                
        self.biasVals.put((xSum,ySum))
        
        return


def main(toLowerQ,capt_cmd, nightMode, picLED, biasVals):
    print("Initializing Science Camera")
    camera = Cameras(toLowerQ, biasVals)

    # Initialize initial photo capture rate
    capt_cmd.put(2)

    while(True):
        if not capt_cmd.empty():
            cmd = capt_cmd.get()
            if isinstance(cmd, int): # If the command is an integer, change the rate
                rate = cmd
            elif imagesRe.search(cmd):
                camera.downlinkData()
            elif expRe.search(cmd):
                camera.exposureAnalysis()
            elif expDRe.search(cmd):
                camera.changeExposure(-50)
            elif expURe.search(cmd):
                camera.changeExposure(50)
        if not nightMode.is_set(): # If night mode isn't on
            if camera.science(): # Take a picture
                picLED.put(True) # And send that fact to the LED thread
        time.sleep(rate)
