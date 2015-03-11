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
        now = datetime.datetime.utcnow()
        UTdate_string = now.strftime('%Y%m%dUT')

        client = MongoClient('192.168.1.101', 27017)
        v20status = client.vysos['v20status']

        entries = [entry for entry\
                   in v20status.find( {"UT date" : UTdate_string} ).sort([('UT time', pymongo.ASCENDING)])]
        print()

        self.render("status.html", title="VYSOS Status", data = entries[-1])

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
