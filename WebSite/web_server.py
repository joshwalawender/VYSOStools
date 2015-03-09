#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import yaml

from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url

class HelloHandler(RequestHandler):
    def get(self):
        self.write("Hello, world")

class StatusHandler(RequestHandler):
    def get(self):
        items = ["Item 1", "Item 2", "Item 3"]
        self.render("status.html", title="VYSOS Status", items=items)

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
