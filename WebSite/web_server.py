#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import datetime
import re
import glob

import pymongo
from pymongo import MongoClient

from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url, StaticFileHandler
from tornado import websocket

from astropy import units as u
from astropy.coordinates import SkyCoord
import ephem

import IQMon

##-------------------------------------------------------------------------
## Check Free Space on Drive
##-------------------------------------------------------------------------
def free_space(path):
    statvfs = os.statvfs(path)
    size_GB = statvfs.f_frsize * statvfs.f_blocks / 1024 / 1024 / 1024
    avail_GB = statvfs.f_frsize * statvfs.f_bfree / 1024 / 1024 / 1024
    pcnt_used = float(size_GB - avail_GB)/float(size_GB) * 100
    return (size_GB, avail_GB, pcnt_used)


##-----------------------------------------------------------------------------
## Handler for list of images
##-----------------------------------------------------------------------------
class ListOfImages(RequestHandler):
    def get(self, telescope, subject):
        assert telescope in ['V5', 'V20']
        names = {'V5': 'VYSOS-5', 'V20': 'VYSOS-20'}
        telescopename = names[telescope]

        ## Create Telescope Object
        if telescope == 'V5':
            config_file = os.path.join(os.path.expanduser('~'), '.VYSOS5.yaml')
        if telescope == 'V20':
            config_file = os.path.join(os.path.expanduser('~'), '.VYSOS20.yaml')
        tel = IQMon.Telescope(config_file)


        client = MongoClient('192.168.1.101', 27017)
        collection = client.vysos['{}.images'.format(telescope)]

        ## If subject matches a date, then get images from a date
        if re.match('\d{8}UT', subject):
            image_list = [entry for entry in\
                          collection.find({"date": subject}).sort(\
                          [('time', pymongo.ASCENDING)])]
        ## If subject matches a target name, then get images from a date
        else:
            target_name_list = sorted(collection.distinct("target name"))
            if subject in target_name_list:
                image_list = [entry for entry in\
                              collection.find({"target name":subject}).sort(\
                              [('date', pymongo.DESCENDING),\
                              ('time', pymongo.DESCENDING)])]

            else:
                image_list = []
                self.write('<html><head><style>')
                self.write('table{border-collapse:collapse;margin-left:auto;margin-right:auto;}')
                self.write('table,th,td{border:1px solid black;vertical-align:top;text-align:left;')
                self.write('padding-top:5px;padding-right:5px;padding-bottom:5px;padding-left:5px;}')
                self.write('</style></head>')
                if (len(subject) > 0) and not re.match('[tT]argets', subject):
                    self.write('<p style="text-align:center;">Could not find {} in target list:</p>'.format(subject))
                self.write('<table style="border:1px solid black;">')
                self.write('<tr><th>Target</th><th>n Images</th>')
                for target in target_name_list:
                    target_images = [entry for entry in collection.find( { "target name": target } ) ]
                    self.write('<tr><td><a href="{0}">{0}</a></td><td>{1:d}</td></tr>'.format(target, len(target_images)))
                self.write('</table></html>')

        for image in image_list:
            ## Set FWHM color
            image['FWHM color'] = ""
            if 'FWHM pix' in image.keys():
                ## Convert FWHM to units
                if tel.units_for_FWHM == u.arcsec:
                    image['FWHM'] = image['FWHM pix'] * tel.pixel_scale.value
                elif tel.units_for_FWHM == u.pix:
                    image['FWHM'] = image['FWHM pix'] * tel.pixel_scale.value
                image['FWHM color'] = "#70DB70" # green
                if 'flags' in image.keys():
                    if 'FWHM' in image['flags'].keys():
                        if image['flags']['FWHM']:
                            image['FWHM color'] = "#FF5C33" # red
            ## Set ellipticity color
            image['ellipticity color'] = ""
            if 'ellipticity' in image.keys():
                image['ellipticity color'] = "#70DB70" # green
                if 'flags' in image.keys():
                    if 'ellipticity' in image['flags'].keys():
                        if image['flags']['ellipticity']:
                            image['ellipticity color'] = "#FF5C33" # red
            ## Set pointing error color
            image['pointing error color'] = ""
            if 'pointing error arcmin' in image.keys():
                image['pointing error color'] = "#70DB70" # green
                if 'flags' in image.keys():
                    if 'pointing error' in image['flags'].keys():
                        if image['flags']['pointing error']:
                            image['pointing error color'] = "#FF5C33" # red
            ## Set zero point color
            image['zero point color'] = ""
            if 'zero point' in image.keys():
                image['zero point color'] = "#70DB70" # green
                if 'flags' in image.keys():
                    if 'zero point' in image['flags'].keys():
                        if image['flags']['zero point']:
                            image['zero point color'] = "#FF5C33" # red

            ## Check for jpegs
            image_basename = os.path.splitext(image['filename'])[0]
            jpegs = glob.glob(os.path.join(tel.plot_file_path, '{}*.jpg'.format(image_basename)))
            image['jpegs'] = []
            for jpeg in jpegs:
                match_static_path = re.match('/var/www/([\w\/\.\-]+)', jpeg)
                if match_static_path:
                    image['jpegs'].append('/static/{}'.format(match_static_path.group(1)))
            ## Check for IQMon log file
            log_file = os.path.join(tel.logs_file_path, '{}_IQMon.log'.format(image_basename))
            if os.path.exists(log_file):
                match_static_path = re.match('/var/www/([\w\/\.\-]+)', log_file)
                if match_static_path:
                    image['logfile'] = '/static/{}'.format(match_static_path.group(1))
            ## Check for PSFinfo plot
            psf_plot_file = os.path.join(tel.plot_file_path, '{}_PSFinfo.png'.format(image_basename))
            if os.path.exists(psf_plot_file):
                match_static_path = re.match('/var/www/([\w\/\.\-]+)', psf_plot_file)
                if match_static_path:
                    image['PSF plot'] = '/static/{}'.format(match_static_path.group(1))
            ## Check for zero point plot
            zp_plot_file = os.path.join(tel.plot_file_path, '{}_ZeroPoint.png'.format(image_basename))
            if os.path.exists(zp_plot_file):
                match_static_path = re.match('/var/www/([\w\/\.\-]+)', zp_plot_file)
                if match_static_path:
                    image['ZP plot'] = '/static/{}'.format(match_static_path.group(1))


        if len(image_list) > 0:
            self.render("image_list.html", title="{} Results".format(telescopename),\
                        telescope = telescope,\
                        FWHM_units = tel.units_for_FWHM.to_string(),\
                        telescopename = telescopename,\
                        subject = subject,\
                        image_list = image_list,\
                       )

##-----------------------------------------------------------------------------
## Handler for list of nights
##-----------------------------------------------------------------------------
class ListOfNights(RequestHandler):

    def get(self, telescope):
        telescope = telescope.strip('/')
        assert telescope in ['V5', 'V20']
        names = {'V5': 'VYSOS-5', 'V20': 'VYSOS-20'}
        telescopename = names[telescope]

        client = MongoClient('192.168.1.101', 27017)
        collection = client.vysos['{}.images'.format(telescope)]
        date_list = sorted(collection.distinct("date"), reverse=True)

        ## Create Telescope Object
        if telescope == 'V5':
            config_file = os.path.join(os.path.expanduser('~'), '.VYSOS5.yaml')
        if telescope == 'V20':
            config_file = os.path.join(os.path.expanduser('~'), '.VYSOS20.yaml')
        tel = IQMon.Telescope(config_file)

        night_plot_path = os.path.abspath('/var/www/nights/')

        nights = []
        for date_string in date_list:
            night_info = {'date': date_string }

            night_graph_file = '{}_{}.png'.format(date_string, telescope)
            if os.path.exists(os.path.join(night_plot_path, night_graph_file)):
                night_info['night graph'] = night_graph_file

#             environmental_graph_file = '{}_{}_Env.png'.format(date_string, telescope)
#             if os.path.exists(os.path.join(logs_path, environmental_graph_file)):
#                 night_info['env graph'] = environmental_graph_file

            night_info['n images'] = collection.find( {"date":date_string} ).count()
            
            nights.append(night_info)

        self.render("night_list.html", title="{} Results".format(telescopename),\
                    telescope = telescope,\
                    telescopename = telescopename,\
                    nights = nights,\
                   )

##-----------------------------------------------------------------------------
## Handler for Status Page
##-----------------------------------------------------------------------------
class Status(RequestHandler):
    def get(self):
        nowut = datetime.datetime.utcnow()
        now = nowut - datetime.timedelta(0,10*60*60)

        client = MongoClient('192.168.1.101', 27017)

        ##------------------------------------------------------------------------
        ## Use pyephem determine sunrise and sunset times
        ##------------------------------------------------------------------------
        Observatory = ephem.Observer()
        Observatory.lon = "-155:34:33.9"
        Observatory.lat = "+19:32:09.66"
        Observatory.elevation = 3400.0
        Observatory.temp = 10.0
        Observatory.pressure = 680.0
        Observatory.date = nowut.strftime('%Y/%m/%d 01:00:00')
        Observatory.horizon = '0.0'

#         twilight = {}
#         Observatory.horizon = '0.0'
#         twilight['sunset'] = Observatory.next_setting(ephem.Sun()).datetime()
#         twilight['sunrise'] = Observatory.next_rising(ephem.Sun()).datetime()
#         Observatory.horizon = '-6.0'
#         twilight['evening civil'] = Observatory.next_setting(ephem.Sun(), use_center=True).datetime()
#         twilight['morning civil'] = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
#         Observatory.horizon = '-12.0'
#         twilight['evening nautical'] = Observatory.next_setting(ephem.Sun(), use_center=True).datetime()
#         twilight['morning nautical'] = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
#         Observatory.horizon = '-18.0'
#         twilight['evening astronomical'] = Observatory.next_setting(ephem.Sun(), use_center=True).datetime()
#         twilight['morning astronomical'] = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
#         if (nowut <= twilight['sunset']):
#             twilight['now'] = 'day'
#         elif (nowut > twilight['sunset']) and (nowut <= twilight['evening civil']):
#             twilight['now'] = 'civil twilight'
#         elif (nowut > twilight['evening civil']) and (nowut <= twilight['evening nautical']):
#             twilight['now'] = 'nautical twilight'
#         elif (nowut > twilight['evening nautical']) and (nowut <= twilight['evening astronomical']):
#             twilight['now'] = 'astronomical twilight'
#         elif (nowut > twilight['evening astronomical']) and (nowut <= twilight['morning astronomical']):
#             twilight['now'] = 'night'
#         elif (nowut > twilight['morning astronomical']) and (nowut <= twilight['morning nautical']):
#             twilight['now'] = 'astronomical twilight'
#         elif (nowut > twilight['morning nautical']) and (nowut <= twilight['morning civil']):
#             twilight['now'] = 'nautical twilight'
#         elif (nowut > twilight['morning civil']) and (nowut <= twilight['sunrise']):
#             twilight['now'] = 'civil twilight'
#         elif (nowut > twilight['sunrise']):
#             twilight['now'] = 'day'

        Observatory.date = nowut.strftime('%Y/%m/%d %H:%M:%S')
        TheSun = ephem.Sun()
        TheSun.compute(Observatory)
        sun = {}
        sun['set'] = Observatory.next_setting(ephem.Sun()).datetime()
        sun['rise'] = Observatory.next_rising(ephem.Sun()).datetime()
        sun['alt'] = TheSun.alt * 180. / ephem.pi
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
        TheMoon.compute(Observatory)
        moon = {}
        moon['phase'] = TheMoon.phase
        moon['alt'] = TheMoon.alt * 180. / ephem.pi
        if moon['alt'] > 0:
            moon['now'] = 'up'
        else:
            moon['now'] = 'down'

        ##---------------------------------------------------------------------
        ## Get Latest V20 Data
        ##---------------------------------------------------------------------
        v20status = client.vysos['V20.status']
        v20entries = []
        while (len(v20entries) < 1) and (nowut > datetime.datetime(2015,1,1)):
            v20entries = [entry for entry\
                          in v20status.find(\
                          {"UT date" : nowut.strftime('%Y%m%dUT')}\
                          ).sort([('UT time', pymongo.ASCENDING)])]
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
                    elif not P and S and T:
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
        ## Get disk use info
        ##---------------------------------------------------------------------
        paths = {'Drobo': os.path.join('/', 'Volumes', 'Drobo'),\
                 'Data': os.path.expanduser('~'),\
                 'Ext Drive B': os.path.join('/', 'Volumes', 'WD500B'),\
                 'Ext Drive C': os.path.join('/', 'Volumes', 'WD500_C'),\
                 'Vega': os.path.join('/', 'Volumes', 'Data_V5'),\
                 'Black': os.path.join('/', 'Volumes', 'Data_V20'),\
                }

        disks = {}
        for disk in paths.keys():
            if os.path.exists(paths[disk]):
                size_GB, avail_GB, pcnt_used = free_space(paths[disk])
                if disk == 'Drobo':
                    size_GB -= 12750
                    avail_GB -= 12750
                    pcnt_used = float(size_GB - avail_GB)/float(size_GB) * 100
                disks[disk] = [size_GB, avail_GB, pcnt_used]


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
#                     twilight = twilight,\
                    moon = moon,\
                    sun = sun,\
                    disks = disks,\
                    )

##-----------------------------------------------------------------------------
## Main
##-----------------------------------------------------------------------------
def main():
    app = Application([
                       url(r"/", Status),
                       url(r"/(V20$|V5$)", ListOfNights),
                       url(r"/(V20/?$|V5/?$)", ListOfNights),
                       url(r"/(V20|V5)/(\w*)", ListOfImages),
                       (r"/static/(.*)", StaticFileHandler, {"path": "/var/www"}),
                     ])
    app.listen(80)
    IOLoop.current().start()

if __name__ == '__main__':
    main()
