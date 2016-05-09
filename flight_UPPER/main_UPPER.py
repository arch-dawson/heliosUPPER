#*********************************************************#
#   COSGC Presents										  #
#      __  __________    ________  _____    _____    __   #
#     / / / / ____/ /   /  _/ __ \/ ___/   /  _/ |  / /   #
#    / /_/ / __/ / /    / // / / /\__ \    / / | | / /    #
#   / __  / /___/ /____/ // /_/ /___/ /  _/ /  | |/ /     #
#  /_/ /_/_____/_____/___/\____//____/  /___/  |___/      #
#                                                         #
#   													  #
#  Copyright (c) 2015 University of Colorado Boulder	  #
#  COSGC HASP Helios IV Team							  #
#*********************************************************#


import threading
import queue

#from capt import cameras


def shutdown():
    """ Completes all necessary events for a shutdown """
    exit()

# Import code for threading. All flight code must be initialized from the main function in the thread file
#from capt import capt
#from star import star
from inpt import inpt
from oupt import oupt
from serv import serv

# Directory for all code shared between threads
from shared import easyserial

# Create required Queues
capt_cmd = queue.Queue()
star_cmd = queue.Queue()
input = queue.Queue()
output = queue.Queue()


# Package arg tuples for thread
#capt_args = (capt_cmd, cameras)
star_args = (star_cmd)
inpt_args = (input,None)
oupt_args = (output, None)
serv_args = (input, output)
# Create thread objects
threads = [
    	#threading.Thread(name='capt', target= capt.main),
	#threading.Thread(name='star', target= star.main),
	threading.Thread(name='inpt', target = inpt.main, args=inpt_args),
   	threading.Thread(name='oupt', target = oupt.main, args=oupt_args),
	threading.Thread(name='serv', target = serv.main, args=serv_args),
]
# Start running threads within a try-except block to allow for it to catch exceptions
try:
    for t in threads:
        t.daemon = True  # Prevents it from running without main
        t.start()
    while True:
        for t in threads:
            t.join(5)  # Prevent main from quitting by joining threads
except(KeyboardInterrupt, SystemExit):
    # Capture an exit condition and shut down the flight code
    shutdown()
