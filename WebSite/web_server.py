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

        clarity_time = datetime.datetime.strptime('{} {}'.format(entries[-1]['boltwood date'], entries[-1]['boltwood time'][:-3]), '%Y-%m-%d %H:%M:%S')
        clarity_age = (now - clarity_time).total_seconds()

        data_time = datetime.datetime.strptime('{} {}'.format(entries[-1]['UT date'], entries[-1]['UT time']), '%Y%m%dUT %H:%M:%S')
        data_age = (nowut - data_time).total_seconds()

        self.render("status.html", title="VYSOS Status",\
                    date = nowut.strftime('%Y%m%dUT'),\
                    time = nowut.strftime('%H:%M:%S'),\
                    clarity_age = clarity_age,\
                    data_age = data_age,\
                    data = entries[-1],\
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
