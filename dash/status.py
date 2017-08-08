import os
import re
import dash
from dash.dependencies import Input, Output, Event
import dash_core_components as dcc
import dash_html_components as html
import plotly
import pymongo
from datetime import datetime as dt
from datetime import timedelta as tdelta

from astropy import units as u
import ephem
from VYSOS import weather_limits, styles

##-------------------------------------------------------------------------
## Define App
##-------------------------------------------------------------------------
app = dash.Dash(__name__)
app.layout = html.Div(
    html.Div([
        html.Div(id='live-update-text'),
        dcc.Interval(
            id='interval-component',
            interval=5*1000 # in milliseconds
        )
    ])
)


##-------------------------------------------------------------------------
## Check Free Space on Drive
##-------------------------------------------------------------------------
def free_space(path):
    statvfs = os.statvfs(path)
    size = statvfs.f_frsize * statvfs.f_blocks * u.byte
    avail = statvfs.f_frsize * statvfs.f_bfree * u.byte

    if re.search('\/Volumes\/DataCopy', path):
        print('Correcting for 4.97 TB disk capacity')
        capacity = (4.97*u.TB).to(u.byte)
        correction = size - capacity
        size -= correction
        avail -= correction
    elif re.search('\/Volumes\/MLOData', path):
        print('Correcting for 16 TB disk capacity')
        capacity = (16.89*u.TB).to(u.byte)
        correction = size - capacity
        size -= correction
        avail -= correction
        if capacity > 16*u.TB:
            correction2 = (capacity - 16*u.TB).to(u.byte)
            size -= correction2
    used = (size - avail)/size

    return (size.to(u.GB).value, avail.to(u.GB).value, used.to(u.percent).value)


##-------------------------------------------------------------------------
## Get Weather Data
##-------------------------------------------------------------------------
def retrieve_weather(lookbackdays=0):
    delta_time = tdelta(lookbackdays, 120)
    client = pymongo.MongoClient('192.168.1.101', 27017)
    db = client.vysos
    weather = db.weather
    weatherdata = [x for x in weather.find( {"date": {"$gt": dt.utcnow()-delta_time} } )]
    client.close()
    return weatherdata

##-------------------------------------------------------------------------
## Determine Conditions from Weather Data
##-------------------------------------------------------------------------
def get_conditions(weatherdata):
    condition = {}
    color = {}

    # Determine Cloud Condition String
    if weatherdata['clouds'] < weather_limits['Cloudiness (C)'][0]:
        condition['cloud'] = 'Clear'
        color['cloud'] = 'green'
    elif weatherdata['clouds'] >= weather_limits['Cloudiness (C)'][0]\
     and weatherdata['clouds'] < weather_limits['Cloudiness (C)'][1]:
        condition['cloud'] = 'Cloudy'
        color['cloud'] = 'yellow'
    elif weatherdata['clouds'] >= weather_limits['Cloudiness (C)'][1]:
        condition['cloud'] = 'Overcast'
        color['cloud'] = 'red'
    else:
        condition['cloud'] = 'Unknown'
        color['cloud'] = 'red'

    # Determine Wind Condition String
    if weatherdata['wind'] < weather_limits['Wind (kph)'][0]:
        condition['wind'] = 'Calm'
        color['wind'] = 'green'
    elif weatherdata['wind'] >= weather_limits['Wind (kph)'][0]\
     and weatherdata['wind'] < weather_limits['Wind (kph)'][1]:
        condition['wind'] = 'Windy'
        color['wind'] = 'yellow'
    elif weatherdata['wind'] >= weather_limits['Wind (kph)'][1]:
        condition['wind'] = 'Very Windy'
        color['wind'] = 'red'
    else:
        condition['wind'] = 'Unknown'
        color['wind'] = 'red'

    # Determine Gust Condition String
    if weatherdata['gust'] < weather_limits['Wind (kph)'][0]:
        condition['gust'] = 'Calm'
        color['gust'] = 'green'
    elif weatherdata['gust'] >= weather_limits['Wind (kph)'][0]\
     and weatherdata['gust'] < weather_limits['Wind (kph)'][1]:
        condition['gust'] = 'Windy'
        color['gust'] = 'yellow'
    elif weatherdata['gust'] >= weather_limits['Wind (kph)'][1]:
        condition['gust'] = 'Very Windy'
        color['gust'] = 'red'
    else:
        condition['gust'] = 'Unknown'
        color['gust'] = 'red'

    # Determine Rain Condition String
    if weatherdata['rain'] > weather_limits['Rain'][0]:
        condition['rain'] = 'Dry'
        color['rain'] = 'green'
    elif weatherdata['rain'] <= weather_limits['Rain'][0]:
        condition['rain'] = 'Wet'
        color['rain'] = 'red'
    else:
        condition['rain'] = 'Unknown'
        color['rain'] = 'red'

    return condition, color


##-------------------------------------------------------------------------
## Get Telescope Status Data
##-------------------------------------------------------------------------
def retrieve_telstatus(telescope):
    client = pymongo.MongoClient('192.168.1.101', 27017)
    db = client.vysos

    telstatus = {}
    for telescope in ['V20', 'V5']:
        results = db[f'{telescope}status'].find(limit=1, sort=[('date', pymongo.DESCENDING)])
        if results.count() > 0:
            telstatus[telescope] = results.next()
            try:
                if telstatus[telescope]['slewing'] is True:
                    telstatus[telescope]['status'] = 'Slewing'
                elif telstatus[telescope]['tracking'] is True:
                    telstatus[telescope]['status'] = 'Tracking'
                elif telstatus[telescope]['park'] is True:
                    telstatus[telescope]['status'] = 'Parked'
                else:
                    telstatus[telescope]['status'] = 'Stationary'
            except:
                telstatus[telescope]['status'] = 'Unknown'
            
            if 'RA' in telstatus[telescope] and 'DEC' in telstatus[telescope]:
                coord = SkyCoord(telstatus[telescope]['RA'],
                                 telstatus[telescope]['DEC'], unit=u.deg)
                telstatus[telescope]['RA'], telstatus[telescope]['DEC'] = coord.to_string('hmsdms', sep=':', precision=0).split()
        else:
            telstatus[telescope] = {'date': dt.utcnow()-tdelta(365),
                                    'status': 'Unknown',
                                    'connected': False}
        ## Format Values and fill in missing keys
        if 'alt' not in telstatus[telescope].keys():
            telstatus[telescope]['altstr'] = ''
        else:
            telstatus[telescope]['altstr'] = '{:.1f} deg'.format(telstatus['V20']['alt'])
        if 'az' not in telstatus[telescope].keys():
            telstatus[telescope]['azstr'] = ''
        else:
            telstatus[telescope]['azstr'] = '{:.1f} deg'.format(telstatus['V20']['az'])
        if 'RA' not in telstatus[telescope].keys():
            telstatus[telescope]['RAstr'] = ''
        else:
            telstatus[telescope]['RAstr'] = '{}'.format(telstatus['V20']['RA'])
        if 'Dec' not in telstatus[telescope].keys():
            telstatus[telescope]['Decstr'] = ''
        else:
            telstatus[telescope]['Decstr'] = '{}'.format(telstatus['V20']['Dec'])
        telstatus[telescope]['age'] = (dt.utcnow() - telstatus[telescope]['date']).total_seconds()/60.
    client.close()

    return telstatus


##------------------------------------------------------------------------
## Use pyephem determine sunrise and sunset times
##------------------------------------------------------------------------
def update_astronomy():
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


##-------------------------------------------------------------------------
## Run this to update the info on the page
##-------------------------------------------------------------------------
# The `dcc.Interval` component emits an event called "interval"
# every `interval` number of milliseconds.
# Subscribe to this event with the `events` argument of `app.callback`
@app.callback(Output('live-update-text', 'children'),
              events=[Event('interval-component', 'interval')])
def generate_weather_table():
    now = dt.now()
    nowut = now + tdelta(0, 10*60*60)
    weatherdata = retrieve_weather(lookbackdays=0)[-1]
    condition, color = get_conditions(weatherdata)
    weather_data_age = (nowut - weatherdata['date']).total_seconds()
    if weather_data_age < 60:
        weather_str = {True: 'Safe', False: 'Unsafe'}[weatherdata['safe']]
        if weatherdata['safe'] is True:
            weather_status = html.Span(weather_str, style={'color': 'green'})
        else:
            weather_status = html.Span(weather_str, style={'color': 'red'})
    else:
        weather_status = html.Span('Unsafe', style={'color': 'red'})

    telstatus = retrieve_telstatus('V20')
    sun, moon = update_astronomy()
    sunstrings = [f"Next sunrise is at {sun['rise'].strftime('%Y/%m/%d %H:%M:%S UT')}",
                  f"Next sunset is at {sun['set'].strftime('%Y/%m/%d %H:%M:%S UT')}"]
    if sun['rise'] > sun['set']:
        sunstrings.reverse()


    paths = {'Drobo': os.path.join('/', 'Volumes', 'DataCopy'),\
             'macOS': os.path.expanduser('~'),\
             'DroboPro': os.path.join('/', 'Volumes', 'MLOData')}
    disks = {}
    for disk in paths.keys():
        if os.path.exists(paths[disk]):
            size_GB, avail_GB, pcnt_used = free_space(paths[disk])
            disks[disk] = [size_GB, avail_GB, pcnt_used]

    tdcw300 = styles['tdc'].copy()
    tdcw300['width'] = '300px'
    tdrw200 = styles['tdc'].copy()
    tdrw200['width'] = '200px'
    tdlw150 = styles['tdl'].copy()
    tdlw150['width'] = '150px'
    tdcw250 = styles['tdc'].copy()
    tdcw250['width'] = '250px'

    tdcw200 = styles['tdc'].copy()
    tdcw200['width'] = '200px'
    tdcw150 = styles['tdc'].copy()
    tdcw150['width'] = '150px'
    tdcw400 = styles['tdc'].copy()
    tdcw400['width'] = '400px'

    weather_table = html.Table([
                    html.Tr([
                             html.Td(html.Span('Time', style={'font-weight': 'bold'}), style=tdcw300),
                             html.Td(html.Span('Weather', style={'font-weight': 'bold'}), style=tdrw200),
                             html.Td(html.Span(weather_status, style={'font-weight': 'bold'}), style=tdlw150),
                             html.Td(html.Span('Disks', style={'font-weight': 'bold'}), style=tdcw250),
                            ]),
                    html.Tr([
                             html.Td(now.strftime('%Y/%m/%d %H:%M:%S HST'), style=styles['tdl']),
                             html.Td('Ambient Temperature', style=styles['tdr']),
                             html.Td(f"{weatherdata['temp']:.1f} C, {weatherdata['temp']*1.8+32.:.1f} F", style=styles['tdl']),
                             html.Td([html.Span('MLOData', style={'font-family': 'Courier, monospace'}),
                                      f": {disks['DroboPro'][1]:.0f}GB free ({disks['DroboPro'][2]:.0f}% full)"],  style=styles['tdr']),
                            ]),
                    html.Tr([
                             html.Td(nowut.strftime('%Y/%m/%d %H:%M:%S UT'), style=styles['tdl']),
                             html.Td('Cloudiness', style=styles['tdr']),
                             html.Td([html.Span(condition['cloud'], style={'color': color['cloud']}),
                                      html.Span(' ({0:.1f} F)'.format(weatherdata['clouds']*1.8+32.), style=styles['p']),
                                     ], style=styles['tdl']),
                             html.Td([html.Span('DataCopy', style={'font-family': 'Courier, monospace'}),
                                      f": {disks['Drobo'][1]:.0f}GB free ({disks['Drobo'][2]:.0f}% full)"],  style=styles['tdr']),
                            ]),
                    html.Tr([
                             html.Td(f"It is currently {sun['now']} (Sun alt = {sun['alt']:.0f})", style=styles['tdl']),
                             html.Td('Wind Speed', style=styles['tdr']),
                             html.Td([html.Span(condition['wind'], style={'color': color['wind']}),
                                      html.Span(' ({0:.1f} kph)'.format(weatherdata['wind']), style=styles['p']),
                                     ], style=styles['tdl']),
                             html.Td([html.Span('macOS', style={'font-family': 'Courier, monospace'}),
                                      f": {disks['macOS'][1]:.0f}GB free ({disks['macOS'][2]:.0f}% full)"],  style=styles['tdr']),
                            ]),
                    html.Tr([
                             html.Td(f"A {moon['phase']:.0f}% illuminated moon is {moon['now']}", style=styles['tdl']),
                             html.Td('Gusts', style=styles['tdr']),
                             html.Td([html.Span(condition['gust'], style={'color': color['gust']}),
                                      html.Span(' ({0:.1f} kph)'.format(weatherdata['gust']), style=styles['p']),
                                     ], style=styles['tdl']),
                             html.Td('',  style=styles['tdr']),
                            ]),
                    html.Tr([
                             html.Td(sunstrings[0], style=styles['tdl']),
                             html.Td('Rain', style=styles['tdr']),
                             html.Td([html.Span(condition['rain'], style={'color': color['rain']}),
                                      html.Span(' ({0:.0f})'.format(weatherdata['rain']), style=styles['p']),
                                     ], style=styles['tdl']),
                             html.Td('',  style=styles['tdr']),
                            ]),
                    html.Tr([
                             html.Td(sunstrings[1], style=styles['tdl']),
                             html.Td('Weather Data Age', style=styles['tdr']),
                             html.Td('{:.1f}s'.format(weather_data_age), style=styles['tdl']),
                             html.Td('',  style=styles['tdr']),
                            ]),
                    html.Tr([
                             html.Td(html.Img(src='http://127.0.0.1:80/static/weather.png', width=800), colSpan=4, style=styles['tdc']),
                            ]),
                   ], style=styles['table'])

    telstatus_table = html.Table([
                      html.Tr([
                               html.Td(html.Span('Status', style={'font-weight': 'bold'}), style=tdcw200),
                               html.Td(html.Span('VYSOS-5', style={'font-weight': 'bold'}), style=tdcw150),
                               html.Td(html.Span('VYSOS-20', style={'font-weight': 'bold'}), style=tdcw150),
                               html.Td(html.Span('ATLAS All Sky Image', style={'font-weight': 'bold'}), style=tdcw400),
                              ]),
                      html.Tr([
                               html.Td('ACP Connected', style=styles['tdr']),
                               html.Td('{}'.format(telstatus['V5']['connected']), style=styles['tdl']),
                               html.Td('{}'.format(telstatus['V20']['connected']), style=styles['tdl']),
                               html.Td(html.Img(src='http://www.fallingstar.com/weather/mlo/latest_bw400.jpg', width=400), rowSpan=8, style=styles['tdc']),
                              ]),
                      html.Tr([
                               html.Td('Status', style=styles['tdr']),
                               html.Td('{}'.format(telstatus['V5']['status']), style=styles['tdl']),
                               html.Td('{}'.format(telstatus['V20']['status']), style=styles['tdl']),
                              ]),
                      html.Tr([
                               html.Td('Alt', style=styles['tdr']),
                               html.Td(telstatus['V5']['altstr'], style=styles['tdl']),
                               html.Td(telstatus['V20']['altstr'], style=styles['tdl']),
                              ]),
                      html.Tr([
                               html.Td('Az', style=styles['tdr']),
                               html.Td(telstatus['V5']['azstr'], style=styles['tdl']),
                               html.Td(telstatus['V20']['azstr'], style=styles['tdl']),
                              ]),
                      html.Tr([
                               html.Td('Target RA', style=styles['tdr']),
                               html.Td(telstatus['V5']['RAstr'], style=styles['tdl']),
                               html.Td(telstatus['V20']['RAstr'], style=styles['tdl']),
                              ]),
                      html.Tr([
                               html.Td('Target Dec', style=styles['tdr']),
                               html.Td(telstatus['V5']['Decstr'], style=styles['tdl']),
                               html.Td(telstatus['V20']['Decstr'], style=styles['tdl']),
                              ]),
                      html.Tr([
                               html.Td('ACP Data Age', style=styles['tdr']),
                               html.Td('{:.1f} min'.format(telstatus['V5']['age']), style=styles['tdl']),
                               html.Td('{:.1f} min'.format(telstatus['V20']['age']), style=styles['tdl']),
                              ]),
                      html.Tr([
                               html.Td('', style=styles['tdr']),
                               html.Td('', style=styles['tdl']),
                               html.Td('', style=styles['tdl']),
                              ]),
                     ], style=styles['table'])


    components = [weather_table,
                  html.Hr(),
                  telstatus_table,
                  ]
    return components



if __name__ == '__main__':
    app.run_server(debug=True)
