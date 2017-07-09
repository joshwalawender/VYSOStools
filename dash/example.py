import dash
from dash.dependencies import Input, Output, Event
import dash_core_components as dcc
import dash_html_components as html
import datetime
import plotly
import pymongo
from datetime import datetime as dt
from datetime import timedelta as tdelta


# pip install pyorbital
from pyorbital.orbital import Orbital
satellite = Orbital('TERRA')

app = dash.Dash(__name__)
app.layout = html.Div(
    html.Div([
        html.H2('VYSOS Weather'),
        html.Div(id='live-update-text'),
        dcc.Graph(id='live-update-graph'),
        dcc.Interval(
            id='interval-component',
            interval=5*1000 # in milliseconds
        )
    ])
)

# The `dcc.Interval` component emits an event called "interval"
# every `interval` number of milliseconds.
# Subscribe to this event with the `events` argument of `app.callback`
@app.callback(Output('live-update-text', 'children'),
              events=[Event('interval-component', 'interval')])
def update_metrics():
    lon, lat, alt = satellite.get_lonlatalt(datetime.datetime.now())
    style = {'padding': '5px', 'fontSize': '16px'}
    return [
        html.Span('Longitude: {0:.2f}'.format(lon), style=style),
        html.Span('Latitude: {0:.2f}'.format(lat), style=style),
        html.Span('Altitude: {0:0.2f}'.format(alt), style=style)
    ]


# Multiple components can update everytime interval gets fired.
@app.callback(Output('live-update-graph', 'figure'),
              events=[Event('interval-component', 'interval')])
def update_graph_live():
    client = pymongo.MongoClient('192.168.1.101', 27017)
    db = client.vysos
    weather = db.weather
    data = [x for x in weather.find( {"date": {"$gt": dt.utcnow()-tdelta(1)} } )]
    client.close()

    time = [x['date'] for x in data]
    print(min(time))
    print(max(time))
    temp = [x['temp']*1.8+32. for x in data]
    print(min(temp), max(temp))
    clouds = [x['clouds']*1.8+32. for x in data]
    print(min(clouds), max(clouds))


    # Create the graph with subplots
    fig = plotly.tools.make_subplots(rows=2, cols=1, vertical_spacing=0.4)
    fig['layout']['margin'] = {
        'l': 30, 'r': 10, 'b': 30, 't': 10
    }
    fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
    fig['layout']['yaxis'] = {'range': [25, 95]}

    fig.append_trace({
        'x': time,
        'y': temp,
        'name': 'Temperature',
        'mode': 'lines+markers',
        'type': 'scatter'
    }, 1, 1)


    fig['layout']['yaxis'] = {'range': [25, 95]}
    fig.append_trace({
        'x': time,
        'y': clouds,
        'name': 'Cloudiness',
        'mode': 'lines+markers',
        'type': 'scatter'
    }, 2, 1)

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
