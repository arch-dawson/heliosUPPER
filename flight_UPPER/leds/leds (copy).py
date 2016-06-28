#*******************************************************#
#   COSGC Presents                                      #                                         #
#      __  __________    ________  _____   ___   __     #
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
    def __init__(self, timeOn, timeOff, signal, priority):
        # Time on and time off define blink pattern
        # Signal is queue of event
        # Priority is boolean, will show priority signal if true

    def querySignal(self):
        # Return true if signal is true.
        # Some signals are queues, others are events.
        # TIME EVENT.IS_SET(), AND QUEUE.GET(), WHICH IS FASTER?

class LED:
    def __init__(self, color, pinNum, timeOn, timeOff, signal):
        # Set up pin as output
        gpio.setup(pinNum, gpio.OUT)
        self.pinNum = pinNum

        self.color = color

        # Defines how the flashes should cycle
        self.timeOn = timeOn
        self.timeOff = timeOff

        # Control signal. Queue for eventLED, event for constant, ironically
        self.signal = signal

    def blink(self):
        """
        Only called at startup for now, makes a cool pattern
        Make sure the LEDs are defined in main in the same
        order that they're physically placed, or it'll look weird
        """
        gpio.output(self.pinNum, GPIO.HIGH)
        time.sleep(1)
        gpio.output(self.pinNum, GPIO.LOW)


class constLED(LED):
    # LEDs that are expected to be on or off for long periods of time
    # "On" light, night mode, etc.
    def update(self):
        if self.signal.is_set():
            self.loop()

    def loop(self):
        # Uses a cycle of two seconds
        for i in range(2/(self.timeOn+self.timeOff)):
            gpio.output(self.pinNum, GPIO.HIGH)
            time.sleep(timeOn)
            gpio.output(self.pinNum, GPIO.LOW)
            time.sleep(timeOff)
        return


class eventLED(LED):
    def update(self):
        # Checks the queue
        while not signal.empty():
            signal.get()
            gpio.output(self.numPin,GPIO.HIGH)
            time.sleep(self.timeOn)
            gpio.output(self.pinNum,GPIO.LOW)
            time.sleep(self.timeOff)

def startUp(*LEDs):
    for LED, i in zip(LEDs, range(len(LEDs))):
        threading.Timer((i/10),LED.blink).start()

def updateLED(*LEDs):
    # I have mixed thoughts about fractally branching.
    # I'm sure it's fine. Maybe.
    for LED in LEDs:
        threading.Timer(0,LED.update).start()
    threading.Timer(2.0, updateLED).start()

def main(nightMode, tempLED, cmdLED, picLED):

    on = threading.Event()
    on.set()
    # Sets "On" event LED to being true.
    # Unanimously decided test case for this would rarely be used

    LEDs = [
        constLED('red', 29, 1/8, 1/8, tempLED),
        constLED('blue', 37, 1, 1, nightMode),
        constLED('green', 33, 1, 1, on),
        eventLED('yellow', 31, 1/2, 1, cmdLED),
        eventLED('white', 35, 1/4, 0, picLED),
        ]

    # Pretty little light display
    startUp(*LEDs)

    # Update all the values for the first time, will keep itself running
    updateLED(*LEDs)
