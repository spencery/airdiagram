#!/usr/bin/python3.4
from time import localtime, strftime, clock
 #from Adafruit_DHT import read_retry, AM2302
from numpy import exp, log
from os import popen, path, remove

import sys
import signal

# Try to grab a sensor reading.  Use the read_retry method which will retry up
# to 15 times to get a sensor reading (waiting 2 seconds between each retry).
lt = localtime()

 #humidity1, temperature1 = read_retry(AM2302, 4)

 #humidity2, temperature2 = read_retry(AM2302, 4)

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
humidity = 1#(humidity1+humidity2)/2
temperature = 1#(temperature1+temperature2)/2
dewpt = (-3928.5/(log(humidity*exp(-3928.5/(temperature+231.667)))-4.60517))-231.667

with open(strftime("./csvs/%y-%m-%d.csv", lt), "a") as file:
	file.write(strftime("%H:%M ", lt) + '{0:0.2f} {1:0.2f} {2:0.2f}\n'.format(temperature, humidity, dewpt))