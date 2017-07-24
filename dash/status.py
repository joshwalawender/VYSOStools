import dash
from dash.dependencies import Input, Output, Event
import dash_core_components as dcc
import dash_html_components as html
import plotly
import pymongo
from datetime import datetime as dt
from datetime import timedelta as tdelta

from VYSOS.schema import weather_limits

app = dash.Dash(__name__)
app.layout = html.Div(
    html.Div([
        html.Div(id='live-update-text'),
#         dcc.Graph(id='live-update-graph'),
        dcc.Interval(
            id='interval-component',
            interval=10*1000 # in milliseconds
        )
    ])
)

def retrieve_weather(lookbackdays=0):
    delta_time = tdelta(lookbackdays, 120)
    client = pymongo.MongoClient('192.168.1.101', 27017)
    db = client.vysos
    weather = db.weather
    data = [x for x in weather.find( {"date": {"$gt": dt.utcnow()-delta_time} } )]
    client.close()
    return data

def get_conditions(data):
    condition = {}
    color = {}

    # Determine Cloud Condition String
    if data['clouds'] < weather_limits['Cloudiness (C)'][0]:
        condition['cloud'] = 'Clear'
        color['cloud'] = 'green'
    elif data['clouds'] >= weather_limits['Cloudiness (C)'][0]\
     and data['clouds'] < weather_limits['Cloudiness (C)'][1]:
        condition['cloud'] = 'Cloudy'
        color['cloud'] = 'yellow'
    elif data['clouds'] >= weather_limits['Cloudiness (C)'][1]:
        condition['cloud'] = 'Overcast'
        color['cloud'] = 'red'
    else:
        condition['cloud'] = 'Unknown'
        color['cloud'] = 'red'

    # Determine Wind Condition String
    if data['wind'] < weather_limits['Wind (kph)'][0]:
        condition['wind'] = 'Calm'
        color['wind'] = 'green'
    elif data['wind'] >= weather_limits['Wind (kph)'][0]\
     and data['wind'] < weather_limits['Wind (kph)'][1]:
        condition['wind'] = 'Windy'
        color['wind'] = 'yellow'
    elif data['wind'] >= weather_limits['Wind (kph)'][1]:
        condition['wind'] = 'Very Windy'
        color['wind'] = 'red'
    else:
        condition['wind'] = 'Unknown'
        color['wind'] = 'red'

    # Determine Gust Condition String
    if data['gust'] < weather_limits['Wind (kph)'][0]:
        condition['gust'] = 'Calm'
        color['gust'] = 'green'
    elif data['gust'] >= weather_limits['Wind (kph)'][0]\
     and data['gust'] < weather_limits['Wind (kph)'][1]:
        condition['gust'] = 'Windy'
        color['gust'] = 'yellow'
    elif data['gust'] >= weather_limits['Wind (kph)'][1]:
        condition['gust'] = 'Very Windy'
        color['gust'] = 'red'
    else:
        condition['gust'] = 'Unknown'
        color['gust'] = 'red'

    # Determine Rain Condition String
    if data['rain'] > weather_limits['Rain'][0]:
        condition['rain'] = 'Dry'
        color['rain'] = 'green'
    elif data['rain'] <= weather_limits['Rain'][0]:
        condition['rain'] = 'Wet'
        color['rain'] = 'red'
    else:
        condition['rain'] = 'Unknown'
        color['rain'] = 'red'

    return condition, color


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
                                    'connected': False}
    client.close()

    return telstatus


# The `dcc.Interval` component emits an event called "interval"
# every `interval` number of milliseconds.
# Subscribe to this event with the `events` argument of `app.callback`
@app.callback(Output('live-update-text', 'children'),
              events=[Event('interval-component', 'interval')])
def update_metrics():
    data = retrieve_weather(lookbackdays=0)[-1]
    condition, color = get_conditions(data)

    telstatus = retrieve_telstatus('V20')

    style = {'padding': '5px', 'fontSize': '16px'}
    cloud_style = style.copy()
    cloud_style.update({'color': color['cloud']})
    wind_style = style.copy()
    wind_style.update({'color': color['wind']})
    gust_style = style.copy()
    gust_style.update({'color': color['gust']})
    rain_style = style.copy()
    rain_style.update({'color': color['rain']})
        
    components = [
        html.H2('VYSOS Weather'),
        html.Span('Temperature:', style=style),
        html.Span('{0:.1f} C,'.format(data['temp']), style=style),
        html.Span('{0:.1f} F'.format(data['temp']*1.8+32.), style=style),
        html.Br(),
        html.Span('Cloudiness:', style=style),
        html.Span(condition['cloud'], style=cloud_style),
        html.Span('({0:.1f} F)'.format(data['clouds']*1.8+32.), style=style),
        html.Br(),
        html.Span('Wind Speed:', style=style),
        html.Span(condition['wind'], style=wind_style),
        html.Span('({0:.1f} kph)'.format(data['wind']), style=style),
        html.Br(),
        html.Span('Wind Gusts:', style=style),
        html.Span(condition['gust'], style=gust_style),
        html.Span('({0:.1f} kph)'.format(data['gust']), style=style),
        html.Br(),
        html.Span('Rain:', style=style),
        html.Span(condition['rain'], style=rain_style),
        html.Span('({0:.0f})'.format(data['rain']), style=style),
        html.Hr(),
    ]

    components.append(html.H2('VYSOS-20 Status'))

    components.append(html.Span('ACP Connected:', style=style))
    if 'connected' in telstatus['V20'].keys():
        components.append(html.Span('{}'.format(telstatus['V20']['connected']), style=style))
    components.append(html.Br())

    components.append(html.Span('Status:', style=style))
    if 'status' in telstatus['V20'].keys():
        components.append(html.Span('{}'.format(telstatus['V20']['status']), style=style))
    components.append(html.Br())

    components.append(html.Span('Alt:', style=style))
    if 'alt' in telstatus['V20'].keys():
        components.append(html.Span('{:.1f} deg'.format(telstatus['V20']['alt']), style=style))
    components.append(html.Br())

    components.append(html.Span('Az:', style=style))
    if 'az' in telstatus['V20'].keys():
        components.append(html.Span('{:.1f} deg'.format(telstatus['V20']['az']), style=style))
    components.append(html.Br())

    components.append(html.Span('Target RA (Jnow):', style=style))
    if 'RA' in telstatus['V20'].keys():
        components.append(html.Span('{}'.format(telstatus['V20']['RA']), style=style))
    components.append(html.Br())

    components.append(html.Span('Target Dec (Jnow):', style=style))
    if 'Dec' in telstatus['V20'].keys():
        components.append(html.Span('{}'.format(telstatus['V20']['Dec']), style=style))
    components.append(html.Br())

    components.append(html.Span('ACP Data Age:', style=style))
    if 'date' in telstatus['V20'].keys():
        age = (dt.utcnow() - telstatus['V20']['date']).total_seconds()/60.
        components.append(html.Span('{:.1f} min'.format(age, style=style)))
    components.append(html.Br())


    components.append(html.Hr())


#         html.Span('Status:', style=style),
#         html.Br(),
#         html.Span('Target RA (Jnow):', style=style),
#         html.Br(),
#         html.Span('Target Dec (Jnow):', style=style),
#         html.Br(),
#         html.Span('ACP Data Age:', style=style),
#         html.Br(),

    return components

# Multiple components can update everytime interval gets fired.
# @app.callback(Output('live-update-graph', 'figure'),
#               events=[Event('interval-component', 'interval')])
# def update_graph_live():
#     data = retrieve_weather(lookbackdays=1)
# 
#     time = [x['date'] for x in data]
#     temp = [x['temp']*1.8+32. for x in data]
#     clouds = [x['clouds']*1.8+32. for x in data]
# 
# 
#     # Create the graph with subplots
#     fig = plotly.tools.make_subplots(rows=2, cols=1, vertical_spacing=0.4)
#     fig['layout']['margin'] = {
#         'l': 30, 'r': 10, 'b': 30, 't': 10
#     }
#     fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
#     fig['layout']['yaxis'] = {'range': [25, 95]}
# 
#     fig.append_trace({
#         'x': time,
#         'y': temp,
#         'name': 'Temperature',
#         'mode': 'lines+markers',
#         'type': 'scatter'
#     }, 1, 1)
# 
# 
#     fig['layout']['yaxis'] = {'range': [25, 95]}
#     fig.append_trace({
#         'x': time,
#         'y': clouds,
#         'name': 'Cloudiness',
#         'mode': 'lines+markers',
#         'type': 'scatter'
#     }, 2, 1)
# 
#     return fig


if __name__ == '__main__':
    app.run_server(debug=True)
