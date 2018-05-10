import plotly as py
import plotly.graph_objs as go
import time
import sqlite3

connection = sqlite3.connect('data.db')

# cursor = connection.execute("SELECT Timestamp, Temperature, Humidity, DewPoint FROM Probes WHERE Timestamp >= date('now', '-1 days') AND Timestamp < date('now')") #Es werden nur Daten von den letzten 24h geladen
cursor = connection.execute("SELECT Timestamp, Temperature, Humidity, DewPoint FROM Probes")

temperature = [] #Arrays
humidity = []
dewpt = []
datetime = []

for row in cursor: #Daten einlesen
    temperature.append(row[1])
    humidity.append(row[2])
    dewpt.append(row[3])
    datetime.append(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(row[0])))

#print (temperature)
#print (humidity)
#print (dewpt)
#print (datetime)


connection.close()

# Diagrammerstellung
trace0 = go.Scatter(
    x=datetime,
    y = temperature,
    name = 'Lufttemperatur',
    line = dict(
        color = ('rgb(205, 12, 24)'),
        width = 4,
        shape = 'spline')
)
trace1 = go.Scatter(
    x=datetime,
    y = humidity,
    name = 'Luftfeuchte',
    line = dict(
        color = ('rgb(22, 96, 167)'),
        width = 4,
        shape = 'spline')
)
trace2 = go.Scatter(
    x=datetime,
    y = dewpt,
    name = 'Taupunkt',
    line = dict(
        color = ('rgb(0, 192, 94)'),
        width = 4,
        shape = 'spline')
)

data = [trace0, trace1, trace2]

# Edit the layout
layout = dict(title = 'Diagramm Temperatur/Feuchte/Taupunkt',
              xaxis = dict(title = 'Datum'),
              yaxis = dict(title = 'Temperatur(°C)/Feuchte(%)/Taupunkt(°C)'),
              )
fig = dict(data=data, layout=layout)
py.offline.plot(fig, filename='./output/name.html')
#py.offline.plot(fig, filename='./output/name.html',  auto_open=False)
