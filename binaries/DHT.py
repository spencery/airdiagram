#!/usr/bin/python3.5
from apscheduler.schedulers.blocking import BlockingScheduler
from time import strftime
from Adafruit_DHT import read_retry, AM2302
from numpy import exp, log
from datetime import datetime

maxProbeTries = 3
dbConnection = None #TODO: Datenbank einrichten!

def probe():
	probeTryCount=0
	print("%s\t" % datetime.time(datetime.now()), end='')
	#Do-While-Schleife für die Validierung
	try:
		while True:
			humidity1, temperature1 = read_retry(AM2302, 2) # Try to grab a sensor reading. Use the read_retry method which will retry up
			humidity2, temperature2 = read_retry(AM2302, 2) # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
			probeTryCount += 1
			if abs(temperature1 - temperature2) < 1 and abs(humidity1 - humidity2) < 2:
				break
			if probeTryCount >= maxProbeTries:
				raise ResourceWarning('Maximum Probe Tries of ' + maxProbeTries + ' exceeded, please check sensor availability.')
	except ResourceWarning as w:
		print(w)
	else:
		humidity = (humidity1+humidity2)/2
		temperature = (temperature1+temperature2)/2

		#Taupunktberechnung, Formel anhand von TODO: Quelle angeben!  aufgebaut und per CAS gekürzt, sodass die Berechnung in einem Schritt erfolgt.
		dewpt = (-3928.5/(log(humidity*exp(-3928.5/(temperature+231.667)))-4.60517)
			)-231.667

		print('{0:0.2f} {1:0.2f} {2:0.2f}'.format(temperature, humidity, dewpt)) # TODO: In Datenbank schreiben!

def plot():
	print("Jetzt ist die Plot-Funktion auszuführen.")

if __name__ == '__main__':
	scheduler = BlockingScheduler()
	scheduler.add_executor('threadpool')
	scheduler.add_job(probe, 'cron', second=5)
	scheduler.add_job(plot, 'cron', minute='*/5')

	try:
		scheduler.start()
	except (KeyboardInterrupt, SystemExit):
		pass
