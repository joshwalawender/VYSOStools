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
from time import sleep

import pymongo

from tornado.web import RequestHandler, Application, url, StaticFileHandler
import tornado.log as tlog

from astropy import units as u
from astropy.coordinates import SkyCoord
import ephem

import IQMon
from VYSOS import weather_limits


##-------------------------------------------------------------------------
## Get Telescope Status
##-------------------------------------------------------------------------
def get_status(telescope, db):
    collection = db[f'{telescope}status']
    two_min_ago = dt.utcnow() - tdelta(0, 2*60)
    values = [x for x in
              collection.find( {'date': {'$gt': two_min_ago}} ).sort('date')]
    try:
        current = status_values[-1]
    except:
        current = None
    return current


##-------------------------------------------------------------------------
## Check for Images
##-------------------------------------------------------------------------
def get_image_list(telescope, date, flats=False, cals=False):
    path = os.path.join('/', 'Users', 'vysosuser', f'{telescope}Data',\
                        'Images', f'{date}')
    disk_array_path = os.path.join('/', 'Volumes', 'VYSOSData', f'{telescope}',\
                                   'Images', f'{date[0:4]}', f'{date}')
    if flats is True:
        descriptor = 'flats '
        path = os.path.join(path, 'AutoFlat')
        disk_array_path = os.path.join(disk_array_path, 'AutoFlat')
        filename_pattern = f'AutoFlat*fts*'
    elif cals is True:
        descriptor = 'cals '
        path = os.path.join(path, 'Calibration')
        disk_array_path = os.path.join(disk_array_path, 'Calibration')
        filename_pattern = '*fts*'
    else:
        descriptor = ''
        filename_pattern = f'{telescope}*fts*'

    image_list = glob.glob(os.path.join(path, filename_pattern))
    image_list.extend(glob.glob(os.path.join(disk_array_path, filename_pattern)))
    tlog.app_log.info(f"Got {descriptor}image list for {telescope} {date}")
#     tlog.app_log.info(f"{image_list}")
    return image_list


##-------------------------------------------------------------------------
## Check Free Space on Drive
##-------------------------------------------------------------------------
def free_space(path):
    statvfs = os.statvfs(path)
    size = statvfs.f_frsize * statvfs.f_blocks * u.byte
    avail = statvfs.f_frsize * statvfs.f_bfree * u.byte

    if re.search('\/Volumes\/VYSOSData', path):
        print('Correcting for 16 TB disk capacity')
        capacity = (11.79*u.TB).to(u.byte)
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

        client = pymongo.MongoClient('localhost', 27017)
        db = client['vysos']

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
        paths = {'Drobo': os.path.join('/', 'Volumes', 'VYSOSData'),\
                 'macOS': os.path.expanduser('~'),\
                }

        disks = {}
        for disk in paths.keys():
            if os.path.exists(paths[disk]):
                size_GB, avail_GB, pcnt_used = free_space(paths[disk])
                disks[disk] = [size_GB, avail_GB, pcnt_used]

        tlog.app_log.info('  Disk use data determined')

        ##---------------------------------------------------------------------
        ## Get Telescope Status
        ##---------------------------------------------------------------------
        telstatus = {}
        tlog.app_log.info(f"Getting telescope status records from mongo")
        for telescope in ['V20', 'V5']:
            try:
                telstatus[telescope] = (db[f'{telescope}status'].find(limit=1, sort=[('date', pymongo.DESCENDING)])).next()
                if 'RA' in telstatus[telescope] and 'DEC' in telstatus[telescope]:
                    coord = SkyCoord(telstatus[telescope]['RA'],
                                     telstatus[telescope]['DEC'], unit=u.deg)
                    telstatus[telescope]['RA'], telstatus[telescope]['DEC'] = coord.to_string('hmsdms', sep=':', precision=0).split()
                tlog.app_log.info(f"  Got telescope status record for {telescope}")

                if 'dome_shutterstatus' in telstatus[telescope].keys():
                    shutter_status_code = telstatus[telescope]['dome_shutterstatus']
                    last_non_error_status_code = (db[f'{telescope}status'].find({'dome_shutterstatus': {'$ne': 4}}, sort=[('date', pymongo.DESCENDING)])).next()['dome_shutterstatus']
                    shutter_status_values = {0: 'Open', 1: 'Closed', 2: 'Opening',
                                             3: 'Closing', 4: 'Unknown'}
                    shutter_status_str = shutter_status_values[shutter_status_code]
                    last_non_error_status_str = shutter_status_values[last_non_error_status_code]
                    tlog.app_log.info(f"  Shutter Status: {shutter_status_str} ({shutter_status_code})")
                    tlog.app_log.info(f"  Was Status: {last_non_error_status_str} ({last_non_error_status_code})")
                    shutter_last = {0: '', 1: '', 2: '', 3: '',
                                    4: f' (was {last_non_error_status_str})'}
                    telstatus[telescope]['shutter_str'] = f'{shutter_status_str}{shutter_last[shutter_status_code]}'
                    tlog.app_log.info(f"  Shutter string: {telstatus[telescope]['shutter_str']}")
                else:
                    telstatus[telescope]['shutter_str'] = f'unknown'
            except StopIteration:
                telstatus[telescope] = {'date': dt.utcnow()-tdelta(365),
                                        'connected': False}
                tlog.app_log.info(f"  No telescope status records for {telescope}.")
                tlog.app_log.info(f"  Filling in blank data for {telescope}.")
        
        
        ##---------------------------------------------------------------------
        ## Get Current Weather
        ##---------------------------------------------------------------------
        tlog.app_log.info(f"Getting weather records from mongo")
        weather = client.vysos['weather']
        if weather.count() > 0:
            cw = weather.find(limit=1, sort=[('date', pymongo.DESCENDING)]).next()
        else:
            cw = None
        tlog.app_log.info(f"  Done")
        
        ##---------------------------------------------------------------------
        ## Render
        ##---------------------------------------------------------------------
        link_date_string = nowut.strftime('%Y%m%dUT')
        files_string = "Tonight's Files"
        if nowut.hour < 3:
            link_date_string = (nowut - tdelta(1,0)).strftime('%Y%m%dUT')
            files_string = "Last Night's Files"

        tlog.app_log.info('  Rendering Status')
        cctv = False
        if input.lower() in ["cctv", "cctv.html"]:
            cctv = True
        self.render("status.html", title="VYSOS Status",
                    now = (now, nowut),
                    disks = disks,
                    link_date_string = link_date_string,
                    moon = moon,
                    sun = sun,
                    telstatus=telstatus,
                    files_string = files_string,\
                    v5_images = get_image_list('V5', link_date_string),\
                    v20_images = get_image_list('V20', link_date_string),\
                    v5_flats = get_image_list('V5', link_date_string, flats=True),\
                    v20_flats = get_image_list('V20', link_date_string, flats=True),\
                    v5_cals = get_image_list('V5', link_date_string, cals=True),\
                    v20_cals = get_image_list('V20', link_date_string, cals=True),\
                    cctv=cctv,
                    currentweather=cw,
                    weather_limits=weather_limits,
                    )
        tlog.app_log.info('  Done')




