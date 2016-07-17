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

import socket
import re
import os
import subprocess
import queue
import time
import threading

TCP_IP='192.168.1.234' # IP set in /etc/network/interfaces
TCP_PORT= 8080 #
BUFFER_SIZE=128
inputQ = queue.Queue() # What clnt has received

# Making all the regexs for parsing commands
rebootRe = re.compile('reboot')
pingRe = re.compile('ping')
fasterRe = re.compile('faster')
slowerRe = re.compile('slower')
imageRe = re.compile('image')
nightRe = re.compile('night')
fireRe = re.compile('fire')
cmdRe = re.compile('command')
expRe = re.compile('exposure')
expDRe = re.compile('expDown')
expURe = re.compile('expUp')
heartRe = re.compile('heartbeat')
"""
This was written so that the Pis are constantly communicating with each other.
Might be overkill, but it worked well for having the LEDs function.
Also, for those of you familiar with the 'heartbleed' bug, I totally stole that
and the security vulnerability has NOT been guarded against.
It's probably fine, but don't put your credit card number on HELIOS anywhere.
Or if you do put your credit card number on here, shoot me an email and I'll have an early vacation. ;)
"""

class Client():
    def __init__(self, toLowerQ, capt_cmd, nightMode, tempLED, cmdLED):
        self.toLowerQ = toLowerQ # Things to send to lower
        self.capt_cmd = capt_cmd # Commands to the capt thread
        self.nightMode = nightMode # If night mode is on
        self.tempLED = tempLED # If any parts of HELIOS are on fire
        self.cmdLED = cmdLED # Whenever a command has been received by lower
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def runConnect(self):
        print("Trying to connect to Lover Pi") # Not a typo, the Pis are in love
        try:
            connectRes = self.connect()
        except:
            connectRes = False
        while not connectRes:
            try:
                connectRes = self.connect()
            except:
                connectRes = False
        print("Successfully connected")
        self.toLowerQ.put("BL BU CLNT")
        return

    def connect(self):
        self.s.connect((TCP_IP, TCP_PORT)) # Actually try connecting
        return True

    def restart(self):
        # Sends reboot command
        print("Got reboot command")
        command = "/usr/bin/sudo /sbin/shutdown -r now"
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)

        # Closes connection.  Pi is dying anyway, but we might as well kill it gently.
        self.s.close()

    def diskParse(self, line):
        # Make the line for disk usage less long
        resList = re.findall(r'\d{1,3}', line)
        return resList[3] + '%D'

    def tempParse(self, line):
        resList = re.findall(r'\-?\d{1,3}\.\d\'C', line)
        return resList[0]  

    def writeCMD(self):
        self.cmdLED.put('First')
        self.cmdLED.put('Second')
        self.cmdLED.put('Third')
        # Contents of queue don't matter
        return

    def command(self, received):
        if not heartRe.search(received):
            self.toLowerQ.put("HUH?")
        self.heartBeat()
        if rebootRe.search(received): # Lower wants to kill us.  Watch out for that guy.
            self.s.send('RB'.encode())
            self.restart()
        elif pingRe.search(received): # Lower making sure we're alive
            self.toLowerQ.put('ACK')
        elif fasterRe.search(received): # Lower wants faster pictures
            self.capt_cmd.put(2)
            self.toLowerQ.put("CamHz2")
        elif slowerRe.search(received): # Lower wants slower pictures
            self.capt_cmd.put(5)
            self.toLowerQ.put("CamHz5")
        elif imageRe.search(received): # Lower is checking up on pictures
            self.capt_cmd.put('images')
        elif nightRe.search(received): # Toggles night mode
            if self.nightMode.is_set():
                self.nightMode.clear()
                self.toLowerQ.put("NMOFF")
            else:
                self.nightMode.set()
                self.toLowerQ.put("NMON")
        elif fireRe.search(received): # If the lower Pi reports that >= 1 thing is on fire
            if not self.tempLED.is_set():
                self.tempLED.set()
        elif cmdRe.search(received): # If the lower pi received a command
            self.writeCMD()
        elif expRe.search(received):
            self.capt_cmd.put('exposure')
        elif expDRe.search(received):
            self.capt_cmd.put('expDown')
        elif expURe.search(received):
            self.capt_cmd.put('expUp')
        self.toLowerQ.put(';') # To demarcate where the end of HB message is
        return
            

    def heartBeat(self): # After clnt receives communication, send heartbeat back to confirm received
        # Contents of the message doesn't really matter.
        temp = self.tempParse(os.popen('vcgencmd measure_temp').readline())
        cpu = str(os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2}'").readline().strip()) + '%'
        p = os.popen("df -h /")
        disk = self.diskParse(p.readline() + p.readline())
        self.toLowerQ.put("HB " + temp + " " + cpu + " " + disk)
        return

    def flight(self):
        timer = 0 # Keep track of time since received last heartbeat
        while True:
            data = self.s.recv(BUFFER_SIZE).decode() # Decoding received data from lower.  Doesn't hang here.
            data = data.lower() # All lower case
            if len(data) > 0: # If there's something in the message...
                inputQ.put(data) # Add to the queue to be parsed
                #self.heartBeat() # Confirm we got it
                timer = 0 # Reset timer
            else:
                time.sleep(1) # Be sad for a second
                timer += 1 # Record sadness
                if timer > 15: # Haven't gotten a heartbeat, should come every 5 seconds
                    break # Try reconnecting
            while not inputQ.empty(): # If we have things to be parsed
                received = inputQ.get() # Pop off the queue
                self.command(received) # Send them to the command parser
            while not self.toLowerQ.empty(): # If things need to be sent to lower
                message = self.toLowerQ.get() # Get the thing off the queue
                self.s.send(message.encode()) # And send it to the lower, encoded as bytes
                print(message)
        return # Want to break and return to main if there's a problem


def main(toLowerQ,capt_cmd, nightMode, tempLED, cmdLED):
    connection = Client(toLowerQ,capt_cmd, nightMode, tempLED, cmdLED)
    connection.runConnect()
    connection.flight()
    while True:
        try:
            connection.flight()
            connection.runConnect()
        except:
            connection.runConnect()
