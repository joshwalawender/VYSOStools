from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
from datetime import datetime as dt
from datetime import timedelta as tdelta
import re
import glob

import pymongo
from pymongo import MongoClient

from tornado.web import RequestHandler, Application, url, StaticFileHandler
import tornado.log as tlog

from astropy import units as u
from astropy.coordinates import SkyCoord
import ephem

import IQMon

import datetime
import mongoengine as me

class telstatus(me.Document):
    telescope = me.StringField(max_length=3, required=True, choices=['V5', 'V20'])
    date = me.DateTimeField(default=datetime.datetime.utcnow(), required=True)
    current = me.BooleanField(default=True, required=True)
    ## ACP Status
    connected = me.BooleanField()
    park = me.BooleanField()
    slewing = me.BooleanField()
    tracking = me.BooleanField()
    alt = me.DecimalField(min_value=-90, max_value=90, precision=4)
    az = me.DecimalField(min_value=0, max_value=360, precision=4)
    RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    ACPerr = me.StringField(max_length=256)
    ## FocusMax Status
    focuser_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    focuser_position = me.DecimalField(min_value=0, max_value=105000, precision=1)

    ## RCOS TCC Status
    fan_speed = me.DecimalField(min_value=0, max_value=100, precision=0)
    truss_temperature  = me.DecimalField(min_value=-50, max_value=120, precision=1)
    primary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    secondary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=0)
    ## CBW Status
    dome_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    fan_state = me.BooleanField()
    fan_enable = me.BooleanField()

    meta = {'collection': 'telstatus',
            'indexes': ['telescope', 'current', 'date']}

    def __str__(self):
        output = 'MongoEngine Document for: {}\n'.format(self.date)
        if self.telescope: output += '  Telescope: {}\n'.format(self.telescope)
        if self.current: output += '  Current: {}\n'.format(self.current)
        if self.connected: output += '  connected: {}\n'.format(self.connected)
        if self.park: output += '  park: {}\n'.format(self.park)
        if self.slewing: output += '  slewing: {}\n'.format(self.slewing)
        if self.tracking: output += '  tracking: {}\n'.format(self.tracking)
        if self.alt: output += '  Altitude: {:.4f}\n'.format(self.alt)
        if self.az: output += '  Azimuth: {:.4f}\n'.format(self.az)
        if self.RA: output += '  RA: {:.4f}\n'.format(self.RA)
        if self.DEC: output += '  DEC: {:.4f}\n'.format(self.DEC)
        if self.ACPerr: output += '  ACPerr: {}\n'.format(self.ACPerr)
        if self.focuser_temperature: output += '  focuser_temperature: {}\n'.format(self.focuser_temperature)
        if self.focuser_position: output += '  focuser_position: {}\n'.format(self.focuser_position)
        return output

    def __repr__(self):
        return self.__str__()


##-------------------------------------------------------------------------
## Check for Images
##-------------------------------------------------------------------------
def get_nimages(telescope, date):
    path = os.path.join('/Volumes/Data_{}/Images/{}'.format(telescope, date))
    image_list = glob.glob(os.path.join(path, '{}*fts'.format(telescope)))
    return len(image_list)

##-------------------------------------------------------------------------
## Check for Flats
##-------------------------------------------------------------------------
def get_nflats(telescope, date):
    path = os.path.join('/Volumes/Data_{}/Images/{}/AutoFlat'.format(telescope, date))
    image_list = glob.glob(os.path.join(path, 'AutoFlat*fts'))
    return len(image_list)


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


##-----------------------------------------------------------------------------
## Handler for Status Page
##-----------------------------------------------------------------------------
class Status(RequestHandler):
    def get(self, input):
        tlog.app_log.info('Get request for Status "{}" recieved'.format(input))
        nowut = dt.utcnow()
        now = nowut - tdelta(0,10*60*60)

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

        tlog.app_log.info('  Ephem data calculated')

        ##---------------------------------------------------------------------
        ## Get disk use info
        ##---------------------------------------------------------------------
        paths = {'Drobo': os.path.join('/', 'Volumes', 'DataCopy'),\
                 'macOS': os.path.expanduser('~'),\
                 'DroboPro': os.path.join('/', 'Volumes', 'MLOData'),\
#                  'USB Drive B': os.path.join('/', 'Volumes', 'WD500B'),\
#                  'USB Drive C': os.path.join('/', 'Volumes', 'WD500_C'),\
#                  'Vega': os.path.join('/', 'Volumes', 'Data_V5'),\
#                  'Black': os.path.join('/', 'Volumes', 'Data_V20'),\
                }

        disks = {}
        for disk in paths.keys():
            if os.path.exists(paths[disk]):
                size_GB, avail_GB, pcnt_used = free_space(paths[disk])
                disks[disk] = [size_GB, avail_GB, pcnt_used]

        tlog.app_log.info('  Disk use data determined')

        ##---------------------------------------------------------------------
        ## Render
        ##---------------------------------------------------------------------
        if nowut.hour < 6 and sun['now'] == 'day' and (sun['set']-nowut).total_seconds() >= 60.*60.:
            link_date_string = (nowut - tdelta(1,0)).strftime('%Y%m%dUT')
            files_string = "Last Night's Files"
        elif sun['now'] != 'day':
            link_date_string = nowut.strftime('%Y%m%dUT')
            files_string = "Tonight's Files"
        else:
            link_date_string = nowut.strftime('%Y%m%dUT')
            files_string = "Last Night's Files"

        tlog.app_log.info('  Rendering Status')
        me.connect('vysos', host='192.168.1.101')
        v5status = telstatus.objects(__raw__={'current': True, 'telescope': 'V5'})[0]
        v20status = telstatus.objects(__raw__={'current': True, 'telescope': 'V20'})[0]
        cctv = False
        if input not in ["status", "status.html"]:
            cctv = True
        self.render("status.html", title="VYSOS Status",
                    now = (now, nowut),
                    disks = disks,
                    link_date_string = link_date_string,
                    moon = moon,
                    sun = sun,
                    v5status=v5status,
                    v20status=v20status,
                    files_string = files_string,\
                    v5_nimages = get_nimages('V5', link_date_string),\
                    v20_nimages = get_nimages('V20', link_date_string),\
                    v5_nflats = get_nflats('V5', link_date_string),\
                    v20_nflats = get_nflats('V20', link_date_string),\
                    cctv=cctv
                    )
        tlog.app_log.info('  Done')
