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
        v20entries = [entry for entry\
                      in v20status.find( {"UT date" : now.strftime('%Y%m%dUT')} ).sort([('UT time', pymongo.ASCENDING)])]
        v20data = v20entries[-1]

        v5status = client.vysos['v5status']
        v5entries = [entry for entry\
                      in v5status.find( {"UT date" : now.strftime('%Y%m%dUT')} ).sort([('UT time', pymongo.ASCENDING)])]
        v5data = v5entries[-1]

        
        wind_units = {'M': 'mph', 'K': 'kph', 'm': 'm/s'}
        rain_status = {0: 'Dry', 1: 'Recent Rain', 2: 'Raining'}
        wet_status = {0: 'Dry', 1: 'Recent Wet', 2: 'Wet'}
        cloud_condition = {0: 'Unknown', 1: 'Clear', 2: 'Cloudy', 3: 'Very Cloudy'}
        wind_condition = {0: 'Unknown', 1: 'Calm', 2: 'Windy', 3: 'Very Windy'}
        rain_condition = {0: 'Unknown', 1: 'Dry', 2: 'Wet', 3: 'Rain'}
        day_condition = {0: 'Unknown', 1: 'Dark', 2: 'Light', 3: 'Very Light'}
        roof_close = {0: 'Safe', 1: 'Unsafe'}

        if 'boltwood wind units' in v20data.keys():
            v20data['boltwood wind units'] = wind_units[v20data['boltwood wind units']]
        if 'boltwood rain status' in v20data.keys():
            v20data['boltwood rain status string'] = rain_status[v20data['boltwood rain status']]
        if 'boltwood wet status' in v20data.keys():
            v20data['boltwood wet status string'] = wet_status[v20data['boltwood wet status']]
        if 'boltwood cloud condition' in v20data.keys():
            v20data['boltwood cloud condition string'] = cloud_condition[v20data['boltwood cloud condition']]
        if 'boltwood wind condition' in v20data.keys():
            v20data['boltwood wind condition string'] = wind_condition[v20data['boltwood wind condition']]
        if 'boltwood rain condition' in v20data.keys():
            v20data['boltwood rain condition string'] = rain_condition[v20data['boltwood rain condition']]
        if 'boltwood day condition' in v20data.keys():
            v20data['boltwood day condition string'] = day_condition[v20data['boltwood day condition']]
        if 'boltwood roof close' in v20data.keys():
            v20data['boltwood roof close string'] = roof_close[v20data['boltwood roof close']]

        v20clarity_time = datetime.datetime.strptime('{} {}'.format(v20data['boltwood date'], v20data['boltwood time'][:-3]), '%Y-%m-%d %H:%M:%S')
        v20clarity_age = (now - v20clarity_time).total_seconds()

        v20data_time = datetime.datetime.strptime('{} {}'.format(v20data['UT date'], v20data['UT time']), '%Y%m%dUT %H:%M:%S')
        v20data_age = (nowut - v20data_time).total_seconds()

        if 'boltwood wind units' in v5data.keys():
            v5data['boltwood wind units'] = wind_units[v5data['boltwood wind units']]
        if 'boltwood rain status' in v5data.keys():
            v5data['boltwood rain status string'] = rain_status[v5data['boltwood rain status']]
        if 'boltwood wet status' in v5data.keys():
            v5data['boltwood wet status string'] = wet_status[v5data['boltwood wet status']]
        if 'boltwood cloud condition' in v5data.keys():
            v5data['boltwood cloud condition string'] = cloud_condition[v5data['boltwood cloud condition']]
        if 'boltwood wind condition' in v5data.keys():
            v5data['boltwood wind condition string'] = wind_condition[v5data['boltwood wind condition']]
        if 'boltwood rain condition' in v5data.keys():
            v5data['boltwood rain condition string'] = rain_condition[v5data['boltwood rain condition']]
        if 'boltwood day condition' in v5data.keys():
            v5data['boltwood day condition string'] = day_condition[v5data['boltwood day condition']]
        if 'boltwood roof close' in v5data.keys():
            v5data['boltwood roof close string'] = roof_close[v5data['boltwood roof close']]

        v5clarity_time = datetime.datetime.strptime('{} {}'.format(v5data['boltwood date'], v5data['boltwood time'][:-3]), '%Y-%m-%d %H:%M:%S')
        v5clarity_age = (now - v5clarity_time).total_seconds()

        v5data_time = datetime.datetime.strptime('{} {}'.format(v5data['UT date'], v5data['UT time']), '%Y%m%dUT %H:%M:%S')
        v5data_age = (nowut - v5data_time).total_seconds()

        self.render("status.html", title="VYSOS Status",\
                    date = nowut.strftime('%Y%m%dUT'),\
                    time = nowut.strftime('%H:%M:%S'),\
                    v20clarity_age = v20clarity_age,\
                    v20data_age = v20data_age,\
                    v20data = v20data,\
                    v5clarity_age = v5clarity_age,\
                    v5data_age = v5data_age,\
                    v5data = v5data,\
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
