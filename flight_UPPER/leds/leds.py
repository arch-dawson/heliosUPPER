#*******************************************************#
#   COSGC Presents                                      #                                         #
#      __  __________    ________  _____    __   __     #
#     / / / / ____/ /   /  _/ __ \/ ___/   | |  / /     #
#    / /_/ / __/ / /    / // / / /\__ \    | | / /      #
#   / __  / /___/ /____/ // /_/ /___/ /    | |/ /       #
#  /_/ /_/_____/_____/___/\____//____/     |___/        #
#                                                       #
#                                                       #                                                 #
#  Copyright (c) 2016 University of Colorado Boulder    #
#  COSGC HASP Helios V Team                             #
#*******************************************************#


import threading
import queue
import time

import RPi.GPIO as gpio
gpio.setwarnings(False)
gpio.setmode(gpio.BOARD)

# Pin 37: Blue
#   On can be anything
#   Nightmode is an event
# Pin 35: Red,
#   Temp is an event
#   Command is from queue
# Pin 33: White,
#   Picture taken is a queue


class Pattern:
    def __init__(self, timeOn, timeOff, signal, priority, ledQ):
        # Time on and time off define blink pattern
        # Signal is queue of event
        # Priority is boolean, will show priority signal if true

        # Defines how the flashes should cycle
        self.timeOn = timeOn
        self.timeOff = timeOff

        self.ledQ = ledQ

        # Control signal. Queue for eventLED, event for constant, ironically
        self.signal = signal

        self.priority = priority

    def flight(self):
        while True:
            if self.querySignal():
                self.ledQ.put((self.priority, (self.timeOn, self.timeOff)))

class eventPattern(Pattern):
    def querySignal(self):
        if self.signal.is_set():
            self.ledQ.put((self.priority, (self.timeOn, self.timeOff)))
        return

class queuePattern(Pattern):
    def querySignal(self):
        if not self.signal.empty():
            self.signal.get()
            self.ledQ.put((self.priority, (self.timeOn, self.timeOff)))
        return

        

class LED:
    def __init__(self, color, pinNum):
        # Set up pin as output
        gpio.setup(pinNum, gpio.OUT)
        self.pinNum = pinNum
        self.color = color

        self.controlQ = queue.PriorityQueue()
        
        return

    def setPatterns(self, patterns): # Both rely on each other, need this circular definition
        self.patterns = patterns

    def blink(self):
        """
        Only called at startup for now, makes a cool pattern
        Make sure the LEDs are defined in main in the same
        order that they're physically placed, or it'll look weird
        """
        gpio.output(self.pinNum, gpio.HIGH)
        time.sleep(1)
        gpio.output(self.pinNum, gpio.LOW)
        return

    def light(self, timeOn, timeOff):
        gpio.output(self.pinNum, gpio.HIGH)
        time.sleep(timeOn)
        gpio.output(self.pinNum, gpio.LOW)
        time.sleep(timeOff)
        return
        

    def flight(self):
        while True:
            for pattern in self.patterns:
                pattern.querySignal()

            while not self.controlQ.empty():
                val = self.controlQ.get()
                self.light(*val[1])
        
def startUp(LEDs):
    for LED, i in zip(LEDs, range(len(LEDs))):
        threading.Timer((i/10),LED.blink).start()

def main(nightMode, tempLED, cmdLED, picLED):

    on = threading.Event()
    on.set()
    # Sets "On" event LED to being true.
    # Unanimously decided test case for this would rarely be used

    blueLED = LED('blue', 37)
    redLED = LED('red', 35)
    whiteLED = LED('white', 33)

    tempPattern = eventPattern(1/8, 1/8, tempLED, 1, redLED.controlQ)
    nightPattern = eventPattern(3, 3, nightMode, 1, blueLED.controlQ)
    onPattern = eventPattern(1, 2, on, 2, blueLED.controlQ)
    cmdPattern = queuePattern(1/2, 1, cmdLED, 2, redLED.controlQ)
    picPattern = queuePattern(1/4, 0, picLED, 2, whiteLED.controlQ)

    blueLED.setPatterns((onPattern, nightPattern))
    redLED.setPatterns((tempPattern, cmdPattern))
    whiteLED.setPatterns((picPattern,))  # Leave weird comma

    # Pretty little light display
    startUp((blueLED, redLED, whiteLED))
    
    # Setting up threads 
    threading.Thread(target=blueLED.flight).start()
    threading.Thread(target=whiteLED.flight).start()
    threading.Thread(target=redLED.flight).start()
