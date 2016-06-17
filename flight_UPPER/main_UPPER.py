#*******************************************************#
#   COSGC Presents				        #					  #
#      __  __________    ________  _____   ___   __     #
#     / / / / ____/ /   /  _/ __ \/ ___/   | |  / /     #
#    / /_/ / __/ / /    / // / / /\__ \    | | / /      #
#   / __  / /___/ /____/ // /_/ /___/ /    | |/ /       #
#  /_/ /_/_____/_____/___/\____//____/     |___/        #
#                                                       #
#   						        #						  #
#  Copyright (c) 2015 University of Colorado Boulder    #
#  COSGC HASP Helios V Team			        #
#*******************************************************#


import threading
import queue

#from capt import cameras


def shutdown():
    """ Completes all necessary events for a shutdown """
    exit()

# Import code for threading. All flight code must be initialized from the main function in the thread file
from capt import capt
#from star import star
from clnt import clnt

# Directory for all code shared between threads
from shared import easyserial

# Create required Queues
capt_cmd = queue.Queue()
toLowerQ = queue.Queue()

# Night mode affects the upper and lower, so we have an equivalent
# flag here that should update at the same time.
nightMode = threading.Event()

# Package arg tuples for thread

capt_args = (toLowerQ,capt_cmd,nightMode) # Leave the comma! Comma makes it a tuple
clnt_args = (toLowerQ,capt_cmd,nightMode)

# Create thread objects
threads = [
    	threading.Thread(name='capt', target= capt.main, args=capt_args),
	threading.Thread(name='clnt', target = clnt.main, args=clnt_args),
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
