#!/usr/bin/python2
from time import localtime, strftime, clock
#print clock()
#print "import time"
#from Adafruit_DHT import read_retry, AM2302
#print clock()
#print "import Adafruit"
from numpy import exp, log
#print clock()
#print "import numpy"
from os import popen, path, remove
#print clock()
#print "import os"
import sys
import signal

if path.isfile("./lock"):
	sys.exit(0)

#print clock()
#print ("exec check")

#signal.signal(signal.SIGALRM,sys.exit(201))
#print ("error?")
signal.alarm(30)

open("/var/tmp/runningl", "w")
#print (clock())
#print ("open running")
# Try to grab a sensor reading.  Use the read_retry method which will retry up
# to 15 times to get a sensor reading (waiting 2 seconds between each retry).
lt = localtime()
#print clock()
#print "get localtime"

humidity1, temperature1 = read_retry(AM2302, 4)
#print clock()
#print "first reading"
humidity2, temperature2 = read_retry(AM2302, 4)
#print clock()
#print "second reading"
#if  abs(temperature1 - temperature2) >= 1 or abs(humidity1 - humidity2) >= 2:
#	line = popen(strftime("tail -n 1 /home/pi/cloud/csvs/%y-%m-%d.csv", lt)).read()
#	if abs( float(line[6:11]) - temperature1 ) >= 2:
#		temperature = temperature2
#		humidity = humidity2
#	elif abs( float(line[6:11]) - temperature2 ) >= 2:
#		temperature = temperature1
#		humidity = humidity1
#	elif abs( float(line[12:17]) - humidity1 ) >= 5:
#		temperature = temperature2
#		humidity = humidity2
#	elif abs( float(line[12:17]) - humidity2 ) >= 5:
#		temperature = temperature1
#		humidity = humidity1
#	else:
#		print('Error! {0:0.1f} {1:0.1f} {2:0.1f} {3:0.1f}'.format(temperature1, temperature2, humidity1, humidity2))
#		#sys.exit(67)
#else:
#	print clock()
#	print "no error"
humidity = (humidity1+humidity2)/2
temperature = (temperature1+temperature2)/2
#print clock()
#print "humidity and temperature set"
dewpt = (-3928.5/(log(humidity*exp(-3928.5/(temperature+231.667)))-4.60517))-231.667
#print (clock())
#print ("dewpt set")

with open(strftime("/home/pi/cloud/csvs/%y-%m-%d.csv", lt), "a") as file:
	file.write(strftime("%H:%M ", lt) + '{0:0.2f} {1:0.2f} {2:0.2f}\n'.format(temperature, humidity, dewpt))
#print (clock())
#print ("output")
#print clock()
#print "clock time"
if path.isfile("/var/tmp/runningl"):
	remove("/var/tmp/runningl")
