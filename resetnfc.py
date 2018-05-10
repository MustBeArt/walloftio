#!/usr/bin/python2

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.OUT, initial=GPIO.HIGH)
GPIO.output(25, 0)
GPIO.output(25, 1)
GPIO.setup(25, GPIO.IN)

