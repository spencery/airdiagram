#!/usr/bin/python3.5
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from time import strftime, localtime
from Adafruit_DHT import read_retry, AM2302
from numpy import exp, log, convolve, ones
from datetime import datetime
from sqlite3 import OperationalError, connect as sql_connect
from sys import argv, exit
from getopt import getopt, GetoptError
from os import path
from paramiko import SSHClient, WarningPolicy
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError
from scp import SCPClient, SCPException
from socket import gaierror
from _thread import interrupt_main
from plotly.offline import plot as plotlyPlot
from plotly.graph_objs import Scatter

def probe(dbConnection, tolerant, maxProbeTries):
	probeTryCount = 0
	now = datetime.time(datetime.now())
	#Do-While-Schleife für die Validierung
	try:
		while True:
			humidity1, temperature1 = read_retry(sensor=AM2302, pin=2, retries=5) # Try to grab a sensor reading. Use the read_retry method which will retry up
			humidity2, temperature2 = read_retry(sensor=AM2302, pin=2, retries=5) # to 15 times to get a sensor reading (waiting 2 seconds between each retry).
			probeTryCount += 1
			if None in [humidity1, temperature1, humidity2, temperature2] or probeTryCount >= maxProbeTries:
				raise ResourceWarning("%s Messung(en) erfolglos. Bitte stellen Sie sicher, dass der Sensor erreichbar ist." % probeTryCount)
			if abs(temperature1 - temperature2) < 1 and abs(humidity1 - humidity2) < 2:
				break
	except ResourceWarning as w: # Falls Messung als gescheitert betrachtet wird, ist eine weitere Berechnung etc. nicht möglich
		print(w)
		return 11 # Rückgabewert 11 bedeutet eine Forderung nach Programmabbruch
	else:
		humidity = (humidity1+humidity2)/2
		temperature = (temperature1+temperature2)/2

		#Taupunktberechnung, Formel anhand von TODO: Quelle angeben!  aufgebaut und per CAS gekürzt, sodass die Berechnung in einem Schritt erfolgt.
		dewpt = (-3928.5/(log(humidity*exp(-3928.5/(temperature+231.667)))-4.60517)
			)-231.667

		print("%s %0.2f %0.2f %0.2f" % (now, temperature, humidity, dewpt))
		with dbConnection:
			cur = dbConnection.cursor()
			cur.execute("insert into Probes values ( strftime('%s','now'), ?, ?, ?)", (temperature, humidity, dewpt))

def plot(dbConnection, diagramPeriod, remotepath, scp, tolerant):
	now = datetime.time(datetime.now())
	fltAvgModr = 37
	htmlFileName = 'diagram.html'
	humanReadableDateTime = []
	temperature = [] #Arrays
	humidity = []
	dewpt = []

	#cursor = dbConnection.execute("SELECT Timestamp, Temperature, Humidity, DewPoint FROM Probes")
	cursor = dbConnection.execute("SELECT Timestamp, Temperature, Humidity, DewPoint FROM Probes WHERE Timestamp >= strftime('%s', 'now', '-1 days')") #Es werden nur Daten von den letzten 24h geladen

	#Daten einlesen
	for row in cursor:
		humanReadableDateTime.append(strftime('%Y-%m-%d %H:%M:%S', localtime(row[0])))
		temperature.append(row[1])
		humidity.append(row[2])
		dewpt.append(row[3])

	# Berechnung der gleitenden Mittelwerte der drei Messgrößen
	moderatedTemperature = convolve(temperature, ones((fltAvgModr,))/fltAvgModr, mode='valid')
	moderatedHumidity = convolve(humidity, ones((fltAvgModr,))/fltAvgModr, mode='valid')
	moderatedDewpt = convolve(dewpt, ones((fltAvgModr,))/fltAvgModr, mode='valid')

	# Diagrammerstellung
	trace0 = Scatter(
		x = humanReadableDateTime[int(fltAvgModr/2):-int(fltAvgModr/2)],
		y = moderatedTemperature,
		name = 'Lufttemperatur',
		line = dict(
			color = ('rgb(205, 12, 24)'),
			width = 4,
			shape = 'spline')
	)
	trace1 = Scatter(
		x = humanReadableDateTime[int(fltAvgModr/2):-int(fltAvgModr/2)],
		y = moderatedHumidity,
		name = 'Luftfeuchte',
		line = dict(
			color = ('rgb(22, 96, 167)'),
			width = 4,
			shape = 'spline')
	)
	trace2 = Scatter(
		x = humanReadableDateTime[int(fltAvgModr/2):-int(fltAvgModr/2)],
		y = moderatedDewpt,
		name = 'Taupunkt',
		line = dict(
			color = ('rgb(0, 192, 94)'),
			width = 4,
			shape = 'spline')
	)

	trace3 = Scatter(
		x = humanReadableDateTime,
		y = temperature,
		showlegend = False,
		line = dict(
			color = ('rgba(205, 12, 24, 0.5)'),
			width = 1,
			shape = 'spline')
	)
	trace4 = Scatter(
		x = humanReadableDateTime,
		y = humidity,
		showlegend = False,
		line = dict(
			color = ('rgba(22, 96, 167, 0.5)'),
			width = 1,
			shape = 'spline')
	)
	trace5 = Scatter(
		x = humanReadableDateTime,
		y = dewpt,
		showlegend = False,
		line = dict(
			color = ('rgba(0, 192, 94, 0.5)'),
			width = 1,
			shape = 'spline')
	)

	data = [trace0, trace1, trace2, trace3, trace4, trace5]

	# Edit the layout
	layout = dict(title = 'Diagramm Temperatur/Feuchte/Taupunkt',
			xaxis = dict(title = 'Zeit'),
			yaxis = dict(title = 'Temperatur(°C) / Feuchte(%) / Taupunkt(°C)'),
		)
	fig = dict(data = data, layout = layout)
	plotlyPlot(fig, filename='diagram.html')
	# Push auf gewählten Server per SCP durch paramiko, falls scp None ist, verwende SCP des Systems
	try:
		scp.put(htmlFileName, remote_path = remotepath)
	except SCPException as e:
		print("Fehler beim Übertragen der Datei, möglicherweise ist der angegebene Pfad fehlerhaft. Fehlermeldung: %s" % e)
		return(13)
	else:
		print("%s Diagramm erfolgreich erstellt" % now)

def errorListener(event):
	if event.retval in (11, 13):
		print("Fehler während eines Messversuchs, Beende Programm.")
		interrupt_main() # Beende Hauptprogramm auf saubere Weise statt das Programm zu töten

if __name__ == '__main__':
	dbFilePath = './data.db' # Standardwert
	diagramPeriod = '24' # Standardwert 1 Tag
	hostname = 'localhost' # Dummy-Standardwert
	knownHostsFile = '~/.ssh/known_hosts'
	maxProbeTries = 3 # Standardwert
	passphrase = ''
	password = ''
	plotCronTabExpression = ''
	probeCronTabExpression = ''
	remotepath = './diagram.html' # Standardname der Ausgabedatei
	scp = None # Falls nicht initialisiert wird, wird SCP des Systems verwendet
	tolerant = False # reagiere auf nicht-kritische Fehler mit exit.
	username = 'pi' # Dummy-Standardwert
	useSystemSsh = False # verwende standardmäßig paramiko statt ssh des Systems

	# Parsen der übergebenen Parameter
	try:
		opts, args = getopt(argv[1:],"hd:H:k:m:p:P:r:stu:",["help",
								"dbfile=",
								"diagramperiod=",
								"hostname=",
								"knownhostsfile=",
								"maxproberetries=",
								"passphrase=",
								"password=",
								"plotcronexpr=",
								"probecronexpr=",
								"remotepath=",
								"systemssh",
								"tolerant",
								"username="])
	except GetoptError:
		print("Usage:\n%s [-h] [-d <dbfile>] [--diagramperiod=<no. of hours<] [-H <hostname>] [-k <knownhostsfile>] [-m <maxproberetries>] [-p <password>] [-P <passphrase>] [-r <remotepath>] [-s] [-t] [-u <username>]" % argv[0])
		exit(2)

	for opt, arg in opts:
		if opt in ("-h", "--help"):
			print("Usage:\n%s [-h] [-d <dbfile>] [--diagramperiod=<no. of hours<] [-H <hostname>] [-k <knownhostsfile>] [-m <maxproberetries>] [-p <password>] [-P <passphrase>] [-r <remotepath>] [-s] [-t] [-u <username>]" % argv[0])
			exit(0)
		elif opt in ("-d", "--dbfile"):
			dbFilePath = arg
		elif opt == "--diagramperiod":
			diagramPeriod = arg
		elif opt in ("-H", "--hostname"):
			hostname = arg
		elif opt in ("-k", "--knownhostsfile"):
			knownHostsFile = arg
		elif opt in ("-m", "--maxproberetries"):
			maxProbeTries = arg
		elif opt in ("-P", "--passphrase"):
			passphrase = arg
		elif opt in ("-p", "--password"):
			password = arg
		elif opt == "--probecronexpr":
			probeCronTabExpression = arg
		elif opt == "--plotcronexpr":
			plotCronTabExpression = arg
		elif opt in ("-r", "--remotepath"):
			remotepath = arg
		#elif opt in ("-n", "--systemssh"):
		#	useSystemSsh = True
		elif opt in ("-t", "--tolerant"):
			tolerant = True
		elif opt in ("-u", "--username"):
			username = arg

	try:
		dbConnection = sql_connect(dbFilePath, check_same_thread=False)

		# Falls die benötigte Tabelle in der Datenbank noch nicht vorhanden ist → Anlegen
		with dbConnection:
			cur = dbConnection.cursor()
			cur.execute("create table if not exists Probes (Timestamp int, Temperature float, Humidity float, DewPoint float);")
	except OperationalError as e:
		exit("Schwerwiegender Datenbank-Fehler: %s", e.args[0])

	# Einrichtung der SSH-Verbindung über paramiko nur, wenn nicht das systemeigene SSH verwendet wird
	if not useSystemSsh:
		ssh = SSHClient()
		ssh.load_system_host_keys()

		if tolerant: # Falls nicht tolerant, ist die Policy standardmäßig „RejectPolicy“
			ssh.set_missing_host_key_policy(WarningPolicy)
		try:
			ssh.load_host_keys(path.expanduser(knownHostsFile))
		except FileNotFoundError:
			print("Die Datei ~/.ssh/known_hosts konnte nicht gefunden werden, überspringe")
		except PermissionError:
			print("Die Datei ~/.ssh/known_hosts konnte nicht geöffnet werden, überspringe, stellen Sie die nötigen Zugriffs-Rechte sicher.")

		try:
			ssh.connect(hostname = hostname, username = username, password = password, passphrase = passphrase)
		except AuthenticationException as e:
			exit("Authentifizierungsproblem: %s" % e)
		except NoValidConnectionsError as e:
			print("Die Verbindung zu „%s@%s“ ist fehlgeschlagen: %s" % (username, hostname, e.args[1]))
			if not tolerant:
				exit(1)
		except SSHException as e:
			print("Allgemeiner SSH-Fehler bei Verbindung zu Host „%s“: %s" % (hostname, e))
			if not tolerant:
				exit(1)
		except gaierror:
			print("Der Hostname „%s“ konnte nicht gefunden werden." % hostname)
			if not tolerant:
				exit(1)
		else:
			scp = SCPClient(ssh.get_transport())

	scheduler = BlockingScheduler()
	scheduler.add_executor('threadpool')
	if not tolerant: # Programm-Abrruch in verschiedenen Fehlerfällen
		scheduler.add_listener(errorListener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

	if (probeCronTabExpression == ''):
		scheduler.add_job(probe, 'cron', args=[dbConnection, tolerant, maxProbeTries], coalesce=False, second='*/10') # verwende Standard-Intervall, falls keine Cron-Tab-Expr. gesetzt
	else:
		scheduler.add_job(probe, CronTrigger.from_crontab(probeCronTabExpression), args=[dbConnection, tolerant, maxProbeTries])

	if (plotCronTabExpression == ''):
		scheduler.add_job(plot, 'cron', args=[dbConnection, diagramPeriod, remotepath, scp, tolerant], coalesce=False, minute='*/1', second=50) # verwende Standard-Intervall, falls keine Cron-Tab-Expr. gesetzt
	else:
		scheduler.add_job(plot, CronTrigger.from_crontab(plotCronTabExpression), args=[dbConnection, diagramPeriod, remotepath, scp, tolerant])


	#probe(tolerant) #Zum Testen! Später entfernen
	#plot(scp, remotepath, tolerant)
	try:
		scheduler.start()
	except (KeyboardInterrupt, SystemExit):
		scheduler.shutdown(wait=False)
		dbConnection.close()
		pass
