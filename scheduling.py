#!/usr/bin/python3.4
import schedule, time

def log():
  print("An dieser Stelle ist die Logging-Funktion auszuführen.")

def plot():
  print("An dieser Stelle ist die Plot-Funktion auszuführen.")


schedule.every().minute.do(log)
schedule.every(5).minutes.do(plot)

while 1:
  schedule.run_pending()
  time.sleep(1)