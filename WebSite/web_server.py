#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import datetime

import pymongo
from pymongo import MongoClient

from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url

class HelloHandler(RequestHandler):
    def get(self):
        self.write("Hello, world")

class StatusHandler(RequestHandler):
    def get(self):
        now = datetime.datetime.now()
        nowut = datetime.datetime.utcnow()

        client = MongoClient('192.168.1.101', 27017)
        v20status = client.vysos['v20status']

        entries = [entry for entry\
                   in v20status.find( {"UT date" : now.strftime('%Y%m%dUT')} ).sort([('UT time', pymongo.ASCENDING)])]
        data = entries[-1]
        
        wind_units = {'M': 'mph', 'K': 'kph', 'm': 'm/s'}
        rain_status = {0: 'Dry', 1: 'Recent Rain', 2: 'Raining'}
        wet_status = {0: 'Dry', 1: 'Recent Wet', 2: 'Wet'}
        cloud_condition = {0: 'Unknown', 1: 'Clear', 2: 'Cloudy', 3: 'Very Cloudy'}
        wind_condition = {0: 'Unknown', 1: 'Calm', 2: 'Windy', 3: 'Very Windy'}
        rain_condition = {0: 'Unknown', 1: 'Dry', 2: 'Wet', 3: 'Rain'}
        day_condition = {0: 'Unknown', 1: 'Dark', 2: 'Light', 3: 'Very Light'}
        roof_close = {0: 'Safe', 1: 'Unsafe'}

        if 'boltwood wind units' in data.keys():
            data['boltwood wind units'] = wind_units[data['boltwood wind units']]
        if 'boltwood rain status' in data.keys():
            data['boltwood rain status string'] = rain_status[data['boltwood rain status']]
        if 'boltwood wet status' in data.keys():
            data['boltwood wet status string'] = wet_status[data['boltwood wet status']]
        if 'boltwood cloud condition' in data.keys():
            data['boltwood cloud condition string'] = cloud_condition[data['boltwood cloud condition']]
        if 'boltwood wind condition' in data.keys():
            data['boltwood wind condition string'] = wind_condition[data['boltwood wind condition']]
        if 'boltwood rain condition' in data.keys():
            data['boltwood rain condition string'] = rain_condition[data['boltwood rain condition']]
        if 'boltwood day condition' in data.keys():
            data['boltwood day condition string'] = day_condition[data['boltwood day condition']]
        if 'boltwood roof close' in data.keys():
            data['boltwood roof close string'] = roof_close[data['boltwood roof close']]

        clarity_time = datetime.datetime.strptime('{} {}'.format(entries[-1]['boltwood date'], entries[-1]['boltwood time'][:-3]), '%Y-%m-%d %H:%M:%S')
        clarity_age = (now - clarity_time).total_seconds()

        data_time = datetime.datetime.strptime('{} {}'.format(data['UT date'], data['UT time']), '%Y%m%dUT %H:%M:%S')
        data_age = (nowut - data_time).total_seconds()

        self.render("status.html", title="VYSOS Status",\
                    date = nowut.strftime('%Y%m%dUT'),\
                    time = nowut.strftime('%H:%M:%S'),\
                    clarity_age = clarity_age,\
                    data_age = data_age,\
                    data = data,\
                    )

def make_app():
    return Application([
        url(r"/", StatusHandler),
        ])

def main():
    app = make_app()
    app.listen(80)
    IOLoop.current().start()




if __name__ == '__main__':
    main()
