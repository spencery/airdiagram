#!/usr/bin/python3.5
import schedule
from time import localtime, strftime, clock, sleep
from Adafruit_DHT import read_retry, AM2302
from numpy import exp, log
from os import popen, path, remove

import sys
import signal

def probe():
	csvFilename = path.join(dir, strftime('%y-%m-%d.csv'))

	# Try to grab a sensor reading.  Use the read_retry method which will retry up
	# to 15 times to get a sensor reading (waiting 2 seconds between each retry).
	humidity1, temperature1 = read_retry(AM2302, 2)

	humidity2, temperature2 = read_retry(AM2302, 2)

	#TODO Do-While-Schleife für Validierung einführen
	print(popen('tail -n 1 ' + csvFilename).read())
	if  abs(temperature1 - temperature2) >= 1 or abs(humidity1 - humidity2) >= 2:
        	line = popen('tail -n 1 ' + csvFilename).read()
	        values=line.split()
	        if abs( float(values[1]) - temperature1 ) >= 2:
        	        temperature = temperature2
                	humidity = humidity2
	        elif abs( float(values[1]) - temperature2 ) >= 2:
        	        temperature = temperature1
                	humidity = humidity1
	        elif abs( float(values[2]) - humidity1 ) >= 5:
        	        temperature = temperature2
                	humidity = humidity2
	        elif abs( float(values[2]) - humidity2 ) >= 5:
        	        temperature = temperature1
                	humidity = humidity1
	        else:
        	        print('Error! {0:0.1f} {1:0.1f} {2:0.1f} {3:0.1f}'.format(temperature1, temperature2, humidity1, humidity2))
                	#sys.exit(67)
	else:
	        humidity = (humidity1+humidity2)/2
        	temperature = (temperature1+temperature2)/2
	        dewpt = (-3928.5/(log(humidity*exp(-3928.5/(temperature+231.667)))-4.60517))-231.667

	with open(csvFilename , "a") as file:
        	file.write(strftime("%H:%M ") + '{0:0.2f} {1:0.2f} {2:0.2f}\n'.format(temperature, humidity, dewpt))

def plot():
	print("Jetzt ist die Plot-Funktion auszuführen.")

dir = path.join(path.dirname(path.abspath(__file__)), path.pardir, 'csvs')

schedule.every().minute.do(probe)
schedule.every(5).minutes.do(plot)

schedule.run_all()
while 1:
	schedule.run_pending()
	sleep(5)
