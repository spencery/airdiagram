#!/usr/bin/python3.5
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from time import strftime
from Adafruit_DHT import read_retry, AM2302
from numpy import exp, log
from datetime import datetime
from sqlite3 import connect as sql_connect
from sys import argv, exit
from getopt import getopt, GetoptError
from os import path
from paramiko import SSHClient
from paramiko.ssh_exception import SSHException
from scp import SCPClient

maxProbeTries = 3
dbConnection = None

def probe():
	probeTryCount=0
	print("%s " % datetime.time(datetime.now()), end='')
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

		print('{0:0.2f} {1:0.2f} {2:0.2f}'.format(temperature, humidity, dewpt))
		with dbConnection:
			cur = dbConnection.cursor()
			cur.execute("insert into Probes values ( strftime('%s','now'), ?, ?, ?)", (temperature, humidity, dewpt))

def plot(scp, remotepath):
	htmlFileName = 'scatter.html'
	print("Jetzt ist die Plot-Funktion auszuführen.")

	# Push auf gewählten Server per SCP
	scp.put(htmlFileName, remote_path = remotepath)

if __name__ == '__main__':
	dbFilePath = './airdata.db' # Standardwert
	probeCronTabExpression = ''
	plotCronTabExpression = ''
	hostname = 'localhost'
	username = 'pi'
	remotepath = 'public-html/scatter.html'

	# Parsen der übergebenen Parameter
	try:
		opts, args = getopt(argv[1:],"hd:H:p:P:u:",["help", "dbfile=", "hostname=", "probeinterval=","plotinterval=", "username="])
	except GetoptError:
		print("Usage:\n%s [-h] [-d <dbfile>] [-H <hostname>] [-p <probeinterval>] [-P <plotinterval>] [-u <username>]" % argv[0])
		exit(42)

	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print("Usage:\n%s [-h] [-d <dbfile>] [-H <hostname>] [-p <probeinterval>] [-P <plotinterval>] [-u <username>]" % argv[0])
			exit(0)
		elif opt in ("-d", "--dbfile"):
			dbFilePath = arg
		elif opt in ("-H", "--hostname"):
			hostname = arg
		elif opt in ("-p", "--probeinterval"):
			probeCronTabExpression = arg
		elif opt in ("-P", "--plotinterval"):
			plotCronTabExpression = arg
		elif opt in ("-u", "--username"):
			username = arg

	dbConnection = sql_connect(dbFilePath, check_same_thread=False)
	# Falls die benötigte Tabelle in der Datenbank noch nicht vorhanden ist → Anlegen
	with dbConnection:
		cur = dbConnection.cursor()
		cur.execute("create table if not exists Probes (Timestamp int, Temperature float, Humidity float, DewPoint float);")

	ssh = SSHClient()
	ssh.load_system_host_keys()
	try:
		ssh.load_host_keys(path.expanduser('~/.ssh/known_hosts'))
	except FileNotFoundError:
		print("Die Datei ~/.ssh/known_hosts konnte nicht gefunden werden, überspringe")
	except PermissionError:
		print("Die Datei ~/.ssh/known_hosts konnte nicht geöffnet werden, stellen Sie die nötigen Zugriffs-Rechte sicher.")

	try:
		ssh.connect(hostname = hostname, username = username)
	except SSHException:
		print("Der Server „%s“ konnte nicht in der Datei known_hosts gefunden werden, Abbruch." % hostname)
		exit(13)
	scp = SCPClient(ssh.get_transport())

	scheduler = BlockingScheduler()
	scheduler.add_executor('threadpool')

	if (probeCronTabExpression == ''):
		scheduler.add_job(probe, 'cron', second=0) # verwende Standard-Intervall, falls keine Cron-Tab-Expr. gesetzt
	else:
		scheduler.add_job(probe, CronTrigger.from_crontab(probeCronTabExpression))

	if (plotCronTabExpression == ''):
		scheduler.add_job(plot, 'cron', args=[scp, remotepath], minute='*/5', second=30) # verwende Standard-Intervall, falls keine Cron-Tab-Expr. gesetzt
	else:
		scheduler.add_job(probe, CronTrigger.from_crontab(plotCronTabExpression))


	#probe() #Zum Testen! Später entfernen
	plot(scp, remotepath)
	try:
		scheduler.start()
	except (KeyboardInterrupt, SystemExit):
		pass
