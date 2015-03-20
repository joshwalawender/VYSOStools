#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import datetime
import re

import pymongo
from pymongo import MongoClient

from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url, StaticFileHandler
from tornado import websocket

from astropy import units as u
from astropy.coordinates import SkyCoord


##-----------------------------------------------------------------------------
## Handler for list of images
##-----------------------------------------------------------------------------
class ListOfImages(RequestHandler):
    def get(self, telescope, subject):
        assert telescope in ['V5', 'V20']
        names = {'V5': 'VYSOS-5', 'V20': 'VYSOS-20'}
        telescopename = names[telescope]

        client = MongoClient('192.168.1.101', 27017)
        collection = client.vysos['{}.images'.format(telescope)]

        ## If subject matches a date, then get images from a date
        if re.match('\d{8}UT', subject):
            image_list = [entry for entry in collection.find( { "date": subject } ) ]
        ## If subject matches a target name, then get images from a date
        else:
            target_name_list = sorted([entry for entry in collection.distinct("target name")])
            if subject in target_name_list:
                image_list = [entry for entry in collection.find( { "target name": subject } ) ]
            else:
                image_list = []
                self.write('Could not find {} in target list:<br>'.format(subject))
                for target in target_name_list:
                    self.write('{}<br>'.format(target))

        ## Set FWHM color
        for image in image_list:
            image['FWHM color'] = ""
            if 'FWHM_pix' in image.keys():
                image['FWHM color'] = "#70DB70" # green
                if 'flags' in image.keys():
                    if 'FWHM' in image['flags'].keys():
                        if image['flags']['FWHM']:
                            image['FWHM color'] = "#FF5C33" # red
        ## Set ellipticity color
        for image in image_list:
            image['ellipticity color'] = ""
            if 'ellipticity' in image.keys():
                image['ellipticity color'] = "#70DB70" # green
                if 'flags' in image.keys():
                    if 'ellipticity' in image['flags'].keys():
                        if image['flags']['ellipticity']:
                            image['ellipticity color'] = "#FF5C33" # red
        ## Set pointing error color
        for image in image_list:
            image['pointing error color'] = ""
            if 'pointing_error_arcmin' in image.keys():
                image['pointing error color'] = "#70DB70" # green
                if 'flags' in image.keys():
                    if 'pointing error' in image['flags'].keys():
                        if image['flags']['pointing error']:
                            image['pointing error color'] = "#FF5C33" # red
        ## Set zero point color
            image['zero point color'] = ""
            if 'zero_point' in image.keys():
                image['zero point color'] = "#70DB70" # green
                if 'flags' in image.keys():
                    if 'zero point' in image['flags'].keys():
                        if image['flags']['zero point']:
                            image['zero point color'] = "#FF5C33" # red

        if len(image_list) > 0:
            self.render("image_list.html", title="{} Results".format(telescopename),\
                        telescope = telescope,\
                        telescopename = telescopename,\
                        subject = subject,\
                        image_list = sorted(image_list, key=lambda entry: entry['time']),\
                       )

##-----------------------------------------------------------------------------
## Handler for list of nights
##-----------------------------------------------------------------------------
class ListOfNights(RequestHandler):

    def get(self, telescope):
        telescope = telescope
        assert telescope in ['V5', 'V20']
        names = {'V5': 'VYSOS-5', 'V20': 'VYSOS-20'}
        telescopename = names[telescope]

        client = MongoClient('192.168.1.101', 27017)
        collection = client.vysos['{}.images'.format(telescope)]
        date_list = sorted([entry for entry in collection.distinct("date")])

        paths_to_check = [os.path.join(os.path.expanduser('~'), 'IQMon', 'Logs', telescopename),\
                          os.path.join('/', 'Volumes', 'DroboPro1', 'IQMon', 'Logs', telescopename)]
        logs_path = None
        for path_to_check in paths_to_check:
            if os.path.exists(path_to_check):
                logs_path = path_to_check
        assert logs_path

        nights = []
        for date_string in date_list:
            night_info = {'date': date_string }

            night_graph_file = '{}_{}.png'.format(date_string, telescope)
            if os.path.exists(os.path.join(logs_path, night_graph_file)):
                night_info['night graph'] = night_graph_file

            environmental_graph_file = '{}_{}_Env.png'.format(date_string, telescope)
            if os.path.exists(os.path.join(logs_path, environmental_graph_file)):
                night_info['env graph'] = environmental_graph_file

            night_info['n images'] = collection.find( {"date":date_string} ).count()
            
            nights.append(night_info)

        self.render("night_list.html", title="{} Results".format(telescopename),\
                    telescope = telescope,\
                    telescopename = telescopename,\
                    nights = sorted(nights, key=lambda entry: entry['date'], reverse=True),\
                   )

##-----------------------------------------------------------------------------
## Handler for Status Page
##-----------------------------------------------------------------------------
class Status(RequestHandler):
    def get(self):
        now = datetime.datetime.now()
        nowut = datetime.datetime.utcnow()

        client = MongoClient('192.168.1.101', 27017)

        ##---------------------------------------------------------------------
        ## Get Latest V20 Data
        ##---------------------------------------------------------------------
        v20status = client.vysos['V20.status']
        v20entries = []
        while (len(v20entries) < 1) and (nowut > datetime.datetime(2015,1,1)):
            v20entries = [entry for entry\
                          in v20status.find( {"UT date" : nowut.strftime('%Y%m%dUT')} ).sort([('UT time', pymongo.ASCENDING)])]
            if len(v20entries) > 0: v20data = v20entries[-1]
            else: nowut = nowut - datetime.timedelta(1, 0)
        nowut = datetime.datetime.utcnow()

        try:
            try:
                v20clarity_time = v20data['boltwood timestamp']
            except:
                v20clarity_time = datetime.datetime.strptime('{} {}'.format(\
                                  v20data['boltwood date'],\
                                  v20data['boltwood time'][:-3]),\
                                  '%Y-%m-%d %H:%M:%S')        
            v20clarity_age = (now - v20clarity_time).total_seconds()
            if v20clarity_age > 60: v20clarity_color = 'red'
            else: v20clarity_color = 'black'
        except:
            v20clarity_age = float('nan')
            v20clarity_color = 'red'

        try:
            try:
                v20data_time = v20data['UT timestamp']
            except:
                v20data_time = datetime.datetime.strptime('{} {}'.format(\
                               v20data['UT date'],\
                               v20data['UT time']),\
                               '%Y%m%dUT %H:%M:%S')
            v20data_age = (nowut - v20data_time).total_seconds()
            if v20data_age > 60: v20data_color = 'red'
            else: v20data_color = 'black'
        except:
            v20data_age = float('nan')
            v20data_color = 'red'

        ##---------------------------------------------------------------------
        ## Get Latest V5 Data
        ##---------------------------------------------------------------------
        v5status = client.vysos['V5.status']
        v5entries = []
        while (len(v5entries) < 1) and (nowut > datetime.datetime(2015,1,1)):
            v5entries = [entry for entry\
                          in v5status.find( {"UT date" : nowut.strftime('%Y%m%dUT')} ).sort([('UT time', pymongo.ASCENDING)])]
            if len(v5entries) > 0: v5data = v5entries[-1]
            else: nowut = nowut - datetime.timedelta(1, 0)
        nowut = datetime.datetime.utcnow()

        try:
            try:
                v5clarity_time = v5data['boltwood timestamp']
            except:
                v5clarity_time = datetime.datetime.strptime('{} {}'.format(\
                                  v5data['boltwood date'],\
                                  v5data['boltwood time'][:-3]),\
                                  '%Y-%m-%d %H:%M:%S')        
            v5clarity_age = (now - v5clarity_time).total_seconds()
            if v5clarity_age > 60: v5clarity_color = 'red'
            else: v5clarity_color = 'black'
        except:
            v5clarity_age = float('nan')
            v5clarity_color = 'red'

        try:
            try:
                v5data_time = v5data['UT timestamp']
            except:
                v5data_time = datetime.datetime.strptime('{} {}'.format(\
                               v5data['UT date'],\
                               v5data['UT time']),\
                               '%Y%m%dUT %H:%M:%S')
            v5data_age = (nowut - v5data_time).total_seconds()
            if v5data_age > 60: v5data_color = 'red'
            else: v5data_color = 'black'
        except:
            v5data_age = float('nan')
            v5data_color = 'red'
        
        ##---------------------------------------------------------------------
        ## Format and Color Code Boltwood Data
        ##---------------------------------------------------------------------
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
            if v20data['boltwood rain status'] == 0: v20data['boltwood rain status color'] = 'green'
            elif v20data['boltwood rain status'] == 1: v20data['boltwood rain status color'] = 'red'
            elif v20data['boltwood rain status'] == 2: v20data['boltwood rain status color'] = 'red'
            else: v20data['boltwood rain color'] = ''
            v20data['boltwood rain status string'] = rain_status[v20data['boltwood rain status']]
        if 'boltwood wet status' in v20data.keys():
            if v20data['boltwood wet status'] == 0: v20data['boltwood wet status color'] = 'green'
            elif v20data['boltwood wet status'] == 1: v20data['boltwood wet status color'] = 'red'
            elif v20data['boltwood wet status'] == 2: v20data['boltwood wet status color'] = 'red'
            else: v20data['boltwood wet color'] = ''
            v20data['boltwood wet status string'] = wet_status[v20data['boltwood wet status']]
        if 'boltwood cloud condition' in v20data.keys():
            if v20data['boltwood cloud condition'] == 0: v20data['boltwood cloud color'] = 'orange'
            elif v20data['boltwood cloud condition'] == 1: v20data['boltwood cloud color'] = 'green'
            elif v20data['boltwood cloud condition'] == 2: v20data['boltwood cloud color'] = 'orange'
            elif v20data['boltwood cloud condition'] == 3: v20data['boltwood cloud color'] = 'red'
            else: v20data['boltwood cloud color'] = ''
            v20data['boltwood cloud condition string'] = cloud_condition[v20data['boltwood cloud condition']]
        if 'boltwood wind condition' in v20data.keys():
            if v20data['boltwood wind condition'] == 0: v20data['boltwood wind color'] = 'orange'
            elif v20data['boltwood wind condition'] == 1: v20data['boltwood wind color'] = 'green'
            elif v20data['boltwood wind condition'] == 2: v20data['boltwood wind color'] = 'orange'
            elif v20data['boltwood wind condition'] == 3: v20data['boltwood wind color'] = 'red'
            else: v20data['boltwood wind color'] = ''
            v20data['boltwood wind condition string'] = wind_condition[v20data['boltwood wind condition']]
        if 'boltwood rain condition' in v20data.keys():
            if v20data['boltwood rain condition'] == 0: v20data['boltwood rain color'] = 'orange'
            elif v20data['boltwood rain condition'] == 1: v20data['boltwood rain color'] = 'green'
            elif v20data['boltwood rain condition'] == 2: v20data['boltwood rain color'] = 'red'
            elif v20data['boltwood rain condition'] == 3: v20data['boltwood rain color'] = 'red'
            else: v20data['boltwood rain color'] = ''
            v20data['boltwood rain condition string'] = rain_condition[v20data['boltwood rain condition']]
        if 'boltwood day condition' in v20data.keys():
            if v20data['boltwood day condition'] == 0: v20data['boltwood day color'] = 'orange'
            elif v20data['boltwood day condition'] == 1: v20data['boltwood day color'] = 'green'
            elif v20data['boltwood day condition'] == 2: v20data['boltwood day color'] = 'orange'
            elif v20data['boltwood day condition'] == 3: v20data['boltwood day color'] = 'red'
            else: v20data['boltwood day color'] = ''
            v20data['boltwood day condition string'] = day_condition[v20data['boltwood day condition']]
        if 'boltwood roof close' in v20data.keys():
            if v20data['boltwood roof close'] == 0: v20data['boltwood roof close color'] = 'green'
            elif v20data['boltwood roof close'] == 1: v20data['boltwood roof close color'] = 'red'
            else: v20data['boltwood roof close color'] = ''
            v20data['boltwood roof close string'] = roof_close[v20data['boltwood roof close']]

        if 'boltwood wind units' in v5data.keys():
            v5data['boltwood wind units'] = wind_units[v5data['boltwood wind units']]
        if 'boltwood rain status' in v5data.keys():
            if v5data['boltwood rain status'] == 0: v5data['boltwood rain status color'] = 'green'
            elif v5data['boltwood rain status'] == 1: v5data['boltwood rain status color'] = 'red'
            elif v5data['boltwood rain status'] == 2: v5data['boltwood rain status color'] = 'red'
            else: v5data['boltwood rain color'] = ''
            v5data['boltwood rain status string'] = rain_status[v5data['boltwood rain status']]
        if 'boltwood wet status' in v5data.keys():
            if v5data['boltwood wet status'] == 0: v5data['boltwood wet status color'] = 'green'
            elif v5data['boltwood wet status'] == 1: v5data['boltwood wet status color'] = 'red'
            elif v5data['boltwood wet status'] == 2: v5data['boltwood wet status color'] = 'red'
            else: v5data['boltwood wet color'] = ''
            v5data['boltwood wet status string'] = wet_status[v5data['boltwood wet status']]
        if 'boltwood cloud condition' in v5data.keys():
            if v5data['boltwood cloud condition'] == 0: v5data['boltwood cloud color'] = 'orange'
            elif v5data['boltwood cloud condition'] == 1: v5data['boltwood cloud color'] = 'green'
            elif v5data['boltwood cloud condition'] == 2: v5data['boltwood cloud color'] = 'orange'
            elif v5data['boltwood cloud condition'] == 3: v5data['boltwood cloud color'] = 'red'
            else: v5data['boltwood cloud color'] = ''
            v5data['boltwood cloud condition string'] = cloud_condition[v5data['boltwood cloud condition']]
        if 'boltwood wind condition' in v5data.keys():
            if v5data['boltwood wind condition'] == 0: v5data['boltwood wind color'] = 'orange'
            elif v5data['boltwood wind condition'] == 1: v5data['boltwood wind color'] = 'green'
            elif v5data['boltwood wind condition'] == 2: v5data['boltwood wind color'] = 'orange'
            elif v5data['boltwood wind condition'] == 3: v5data['boltwood wind color'] = 'red'
            else: v5data['boltwood wind color'] = ''
            v5data['boltwood wind condition string'] = wind_condition[v5data['boltwood wind condition']]
        if 'boltwood rain condition' in v5data.keys():
            if v5data['boltwood rain condition'] == 0: v5data['boltwood rain color'] = 'orange'
            elif v5data['boltwood rain condition'] == 1: v5data['boltwood rain color'] = 'green'
            elif v5data['boltwood rain condition'] == 2: v5data['boltwood rain color'] = 'red'
            elif v5data['boltwood rain condition'] == 3: v5data['boltwood rain color'] = 'red'
            else: v5data['boltwood rain color'] = ''
            v5data['boltwood rain condition string'] = rain_condition[v5data['boltwood rain condition']]
        if 'boltwood day condition' in v5data.keys():
            if v5data['boltwood day condition'] == 0: v5data['boltwood day color'] = 'orange'
            elif v5data['boltwood day condition'] == 1: v5data['boltwood day color'] = 'green'
            elif v5data['boltwood day condition'] == 2: v5data['boltwood day color'] = 'orange'
            elif v5data['boltwood day condition'] == 3: v5data['boltwood day color'] = 'red'
            else: v5data['boltwood day color'] = ''
            v5data['boltwood day condition string'] = day_condition[v5data['boltwood day condition']]
        if 'boltwood roof close' in v5data.keys():
            if v5data['boltwood roof close'] == 0: v5data['boltwood roof close color'] = 'green'
            elif v5data['boltwood roof close'] == 1: v5data['boltwood roof close color'] = 'red'
            else: v5data['boltwood roof close color'] = ''
            v5data['boltwood roof close string'] = roof_close[v5data['boltwood roof close']]

        ##---------------------------------------------------------------------
        ## Format and Color Code ACP Data
        ##---------------------------------------------------------------------
        ACP_connected = {True: 'Connected', False: 'Disconnected'}

        if 'ACP connected' in v20data.keys():
            v20data['ACP connected string'] = ACP_connected[v20data['ACP connected']]
            if (v20data['ACP connected']):
                v20data['ACP connected color'] = 'green'
                if ('ACP park status' in v20data.keys()) and\
                   ('ACP slewing status' in v20data.keys()) and\
                   ('ACP tracking status' in v20data.keys()):
                    P = v20data['ACP park status']
                    S = v20data['ACP slewing status']
                    T = v20data['ACP tracking status']
                    if P:
                        v20data['ACP status string'] = 'Parked'
                        v20data['ACP status color'] = ''
                    elif not P and not S and not T:
                        v20data['ACP status string'] = 'Stationary'
                        v20data['ACP status color'] = ''
                    elif not P and S and not T:
                        v20data['ACP status string'] = 'Slewing'
                        v20data['ACP status color'] = 'orange'
                    elif not P and not S and T:
                        v20data['ACP status string'] = 'Tracking'
                        v20data['ACP status color'] = 'green'
                    else:
                        v20data['ACP status string'] = '{}{}{}'.format(P,S,T)
                        v20data['ACP status color'] = 'red'
                if ('ACP target RA' in v20data.keys()) and ('ACP target Dec' in v20data.keys()):
                    v20c = SkyCoord(ra=v20data['ACP target RA']*u.degree,\
                                    dec=v20data['ACP target Dec']*u.degree,\
                                    frame='icrs')
                    v20coord = '{} {}'.format(\
                                              v20c.ra.to_string(sep=':', precision=1),\
                                              v20c.dec.to_string(sep=':', precision=1),\
                                             )
                else:
                    v20c = None
                    v20coord = ''
            else:
                v20data['ACP connected color'] = ''
                v20coord = ''

        if 'ACP connected' in v5data.keys():
            v5data['ACP connected string'] = ACP_connected[v5data['ACP connected']]
            if (v5data['ACP connected']):
                v5data['ACP connected color'] = 'green'
                if ('ACP park status' in v5data.keys()) and\
                   ('ACP slewing status' in v5data.keys()) and\
                   ('ACP tracking status' in v5data.keys()):
                    P = v5data['ACP park status']
                    S = v5data['ACP slewing status']
                    T = v5data['ACP tracking status']
                    if P:
                        v5data['ACP status string'] = 'Parked'
                        v5data['ACP status color'] = ''
                    elif not P and not S and not T:
                        v5data['ACP status string'] = 'Stationary'
                        v5data['ACP status color'] = ''
                    elif not P and S and not T:
                        v5data['ACP status string'] = 'Slewing'
                        v5data['ACP status color'] = 'orange'
                    elif not P and not S and T:
                        v5data['ACP status string'] = 'Tracking'
                        v5data['ACP status color'] = 'green'
                    else:
                        v5data['ACP status string'] = '{}{}{}'.format(P,S,T)
                        v5data['ACP status color'] = 'red'
                if ('ACP target RA' in v5data.keys()) and ('ACP target Dec' in v5data.keys()):
                    v5c = SkyCoord(ra=v5data['ACP target RA']*u.degree,\
                                   dec=v5data['ACP target Dec']*u.degree,\
                                   frame='icrs')
                    v5coord = '{} {}'.format(\
                                             v5c.ra.to_string(sep=':', precision=1),\
                                             v5c.dec.to_string(sep=':', precision=1),\
                                            )
                else:
                    v5c = None
                    v5coord = ''
            else:
                v5data['ACP connected color'] = ''
                v5coord = ''

        ##---------------------------------------------------------------------
        ## Render
        ##---------------------------------------------------------------------
        self.render("status.html", title="VYSOS Status",\
                    now = now,\
                    nowut = nowut,\
                    v20clarity_age = v20clarity_age,\
                    v20clarity_color = v20clarity_color,\
                    v20data_time = v20data_time,\
                    v20data_age = v20data_age,\
                    v20data_color = v20data_color,\
                    v20data = v20data,\
                    v20coord = v20coord,\
                    v5clarity_age = v5clarity_age,\
                    v5clarity_color = v5clarity_color,\
                    v5data_time = v5data_time,\
                    v5data_age = v5data_age,\
                    v5data_color = v5data_color,\
                    v5data = v5data,\
                    v5coord = v5coord,\
                    )

##-----------------------------------------------------------------------------
## Main
##-----------------------------------------------------------------------------
def main():
    app = Application([
                       url(r"/", Status),
                       url(r"/(V20$|V5$)", ListOfNights),
#                        url(r"/(V20|V5)/(\d{8}UT)", ListOfImages),
                       url(r"/(V20|V5)/(\w+)", ListOfImages),
                       (r"/static/(.*)", StaticFileHandler, {"path": "/var/www"}),
                     ])
    app.listen(80)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
