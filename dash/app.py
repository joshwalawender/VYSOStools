from datetime import datetime as dt
from datetime import timedelta as tdelta

import dash
import dash_core_components as dcc
import dash_html_components as html

from pymongo import MongoClient

from astropy import units as u
from astropy.coordinates import SkyCoord
import ephem


#------------------------------------------------------------------------------
# Get Weather Data
#------------------------------------------------------------------------------
def get_temperature_data(weather):
    yesterday = dt.now() - timedelta(60*60*24)
    results = weather.find({"date": {"$gt": yesterday}})
    return results


#------------------------------------------------------------------------------
# Get Astronomical Info
#------------------------------------------------------------------------------
def update_astronomical_info():
    nowut = dt.utcnow()
    Observatory = ephem.Observer()
    Observatory.lon = "-155:34:33.9"
    Observatory.lat = "+19:32:09.66"
    Observatory.elevation = 3400.0
    Observatory.temp = 10.0
    Observatory.pressure = 680.0
    Observatory.horizon = '0.0'
    Observatory.date = nowut

    TheSun = ephem.Sun()
    TheSun.compute(Observatory)
    sun = {}
    sun['alt'] = float(TheSun.alt) * 180. / ephem.pi
    sun['set'] = Observatory.next_setting(TheSun).datetime()
    sun['rise'] = Observatory.next_rising(TheSun).datetime()
    if sun['alt'] <= -18:
        sun['now'] = 'night'
    elif sun['alt'] > -18 and sun['alt'] <= -12:
        sun['now'] = 'astronomical twilight'
    elif sun['alt'] > -12 and sun['alt'] <= -6:
        sun['now'] = 'nautical twilight'
    elif sun['alt'] > -6 and sun['alt'] <= 0:
        sun['now'] = 'civil twilight'
    elif sun['alt'] > 0:
        sun['now'] = 'day'

    TheMoon = ephem.Moon()
    Observatory.date = nowut
    TheMoon.compute(Observatory)
    moon = {}
    moon['phase'] = TheMoon.phase
    moon['alt'] = TheMoon.alt * 180. / ephem.pi
    moon['set'] = Observatory.next_setting(TheMoon).datetime()
    moon['rise'] = Observatory.next_rising(TheMoon).datetime()
    if moon['alt'] > 0:
        moon['now'] = 'up'
    else:
        moon['now'] = 'down'

    return sun, moon




#------------------------------------------------------------------------------
# Setup Mongo
#------------------------------------------------------------------------------
client = MongoClient()
weather = client['vysos']['weather']

#------------------------------------------------------------------------------
# Dash App
#------------------------------------------------------------------------------
app = dash.Dash()

sun, moon = update_astronomical_info()

current = f"It is currently {sun['now']} (Sun alt = {sun['alt']:.0f})"

markdown_text = f'''
# VYSOS Weather

Data from AAG Cloudwatcher.  Sun alt = {sun['alt']:.1f} deg.
'''

app.layout = html.Div([

    dcc.Markdown(children=markdown_text),


    dcc.Graph(
        id='temperature',
        figure={
            'data': [
                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
            ],
            'layout': {
                'title': 'Dash Data Visualization'
            }
        }
    )
])


if __name__ == '__main__':
    app.run_server(debug=True)
