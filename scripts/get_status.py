#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import time
import datetime
import re
import numpy as np

import datetime
import mongoengine as me

class weather(me.Document):
    querydate = me.DateTimeField(default=datetime.datetime.utcnow(), required=True)
    date = me.DateTimeField(required=True)
    current = me.BooleanField(default=True, required=True)
    clouds = me.DecimalField(precision=2)
    temp = me.DecimalField(precision=2)
    wind = me.DecimalField(precision=1)
    gust = me.DecimalField(precision=1)
    rain = me.IntField()
    light = me.IntField()
    switch = me.IntField()
    safe = me.BooleanField()

    meta = {'collection': 'weather',
            'indexes': ['current', 'querydate', 'date']}

    def __str__(self):
        output = 'MongoEngine Document at: {}\n'.format(self.querydate.strftime('%Y%m%d %H:%M:%S'))
        if self.date: output += '  Date: {}\n'.format(self.date.strftime('%Y%m%d %H:%M:%S'))
        if self.current: output += '  Current: {}\n'.format(self.current)
        if self.clouds: output += '  clouds: {:.2f}\n'.format(self.clouds)
        if self.temp: output += '  temp: {:.2f}\n'.format(self.temp)
        if self.wind: output += '  wind: {:.1f}\n'.format(self.wind)
        if self.gust: output += '  gust: {:.1f}\n'.format(self.gust)
        if self.rain: output += '  rain: {:.0f}\n'.format(self.rain)
        if self.light: output += '  light: {:.0f}\n'.format(self.light)
        if self.switch: output += '  switch: {}\n'.format(self.switch)
        if self.safe: output += '  safe: {}\n'.format(self.safe)
        return output

    def __repr__(self):
        return self.__str__()


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
        output = 'MongoEngine Document at: {}\n'.format(self.date.strftime('%Y%m%d %H:%M:%S'))
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
        if self.focuser_temperature: output += '  focuser_temperature: {:.1f}\n'.format(self.focuser_temperature)
        if self.focuser_position: output += '  focuser_position: {}\n'.format(self.focuser_position)
        return output

    def __repr__(self):
        return self.__str__()


##-------------------------------------------------------------------------
## Query AAG Solo for Weather Data
##-------------------------------------------------------------------------
def get_weather(logger):
    logger.info('Getting Weather status')
    import requests
    # http://aagsolo/cgi-bin/cgiLastData
    # http://aagsolo/cgi-bin/cgiHistData
    address = 'http://192.168.1.105/cgi-bin/cgiLastData'
    r = requests.get(address)
    lines = r.text.splitlines()
    result = {}
    for line in lines:
        key, val = line.split('=')
        result[str(key)] = str(val)

    weatherdoc = weather(date=datetime.datetime.strptime(result['dataGMTTime'], '%Y/%m/%d %H:%M:%S'))
    weatherdoc.clouds = float(result['clouds'])
    weatherdoc.temp = float(result['temp'])
    weatherdoc.wind = float(result['wind'])
    weatherdoc.gust = float(result['gust'])
    weatherdoc.rain = int(result['rain'])
    weatherdoc.light = int(result['light'])
    weatherdoc.switch = int(result['switch'])
    weatherdoc.safe = {'1': True, '0': False}[result['safe']]

    threshold = 30
    age = (weatherdoc.querydate - weatherdoc.date).total_seconds()
    if age > threshold:
        logger.warning('Age of weather data ({:.1f}) is greater than {:.0f} seconds'.format(
                       age, threshold))

    me.connect('vysos', host='192.168.1.101')

    ncurrent = len(weather.objects(__raw__={'current': True}))
    if ncurrent < 1:
        logger.error('No exiting "current" document found!')
    elif ncurrent == 1:
        logger.info('Modifying old "current" document')
        weather.objects(__raw__={'current': True, 'telescope': telescope}).update_one(set__current=False)
        logger.info('  Done')
    else:
        logger.error('Multiple ({}) exiting "current" document found!'.format(ncurrent))
        logger.info('Updating old "current" documents')
        weather.objects(__raw__={'current': True, 'telescope': telescope}).update(set__current=False, multi=True)
        logger.info('  Done')

    try:
        logger.info('Saving new "current" document')
        weatherdoc.save()
        logger.info("  Done")
        logger.info("\n{}".format(status))
    except:
        logger.error('Failed to add new document')




##-------------------------------------------------------------------------
## Query ASCOM ACPHub for Telescope Position and State
##-------------------------------------------------------------------------
def get_telescope_info(status, logger):
    logger.info('Getting ACP status')
    try:
        ACP = win32com.client.Dispatch("ACP.Telescope")
    except:
        logger.error('Could not connect to ACP ASCOM object.')
        return status

    try:
        status.connected = ACP.Connected
        logger.debug('  ACP Connected = {}'.format(status.connected))
        if status.connected:
            status.park = ACP.AtPark
            logger.info('  ACP At Park = {}'.format(status.park))
            status.slewing = ACP.Slewing
            logger.info('  ACP Slewing = {}'.format(status.slewing))
            status.tracking = ACP.Tracking
            logger.info('  ACP Tracking = {}'.format(status.tracking))
            status.alt = float(ACP.Altitude)
            logger.info('  ACP Alt = {:.2f}'.format(status.alt))
            status.az = float(ACP.Azimuth)
            logger.info('  ACP Az = {:.2f}'.format(status.az))
            try:
                status.RA = ACP.TargetRightAscension * 15.0
                status.DEC = ACP.TargetDeclination
                logger.info('  ACP target RA = {:.4f}'.format(status.RA))
                logger.info('  ACP target Dec = {:.4f}'.format(status.DEC))
            except:
                logger.info('  Could not get target info')
    except pywintypes.com_error as err:
        logger.warning('COM error:')
        logger.warning('  {}'.format(err.message))
        status.ACPerr = '{}'.format(err.message)
    except:
        status.connected = False
        logger.warning('Queries to ACP object failed')

    return status


##-------------------------------------------------------------------------
## Query ASCOM Focuser for Position, Temperature, Fan State
##-------------------------------------------------------------------------
def get_focuser_info(status, logger):
    logger.info('Getting ASCOM focuser status')
    try:
        FocusMax = win32com.client.Dispatch("FocusMax.Focuser")
        if not FocusMax.Link:
            try:
                FocusMax.Link = True
            except:
                logger.error('Could not start FocusMax ASCOM link.')
        logger.debug('  Connected to FocusMax')
    except:
        logger.error('Could not connect to FocusMax ASCOM object.')
        return status

    ## Get Average of 3 Temperature Readings
    FocusMax_Temps = []
    for i in range(0,3,1):
        try:
            newtemp = float(FocusMax.Temperature)*9./5. + 32.
            logger.debug('  Queried FocusMax temperature = {:.1f}'.format(newtemp))
            FocusMax_Temps.append(newtemp)
        except:
            pass
    if len(FocusMax_Temps) > 0:
        ## Filter out bad values
        median_temp = np.median(FocusMax_Temps)
        if (median_temp > -10) and (median_temp < 150):
            status.focuser_temperature = median_temp
            logger.info('  FocusMax temperature = {:.1f} {}'.format(status.focuser_temperature, 'F'))
    ## Get Position
    try:
        status.focuser_position = int(FocusMax.Position)
        logger.info('  FocusMax position = {:d}'.format(status.focuser_position))
    except:
        pass

    return status


##-------------------------------------------------------------------------
## Query ControlByWeb Temperature Module for Temperature and Fan State
##-------------------------------------------------------------------------
def control_by_web(status, logger):
    logger.info('Getting CBW temperature module status')
    address = 'http://192.168.1.115/state.xml'
    import urllib2
    response = urllib2.urlopen(address)
    raw_result = response.read()
    tunits = re.search('<units>(\w+)</units>', raw_result).group(1)
    assert tunits in ['F', 'C']
    temp1 = float(re.search('<sensor1temp>(\d+\.\d*)</sensor1temp>', raw_result).group(1))
    r1state = bool(int(re.search('<relay1state>(\d)</relay1state>', raw_result).group(1)))
    r2state = bool(int(re.search('<relay2state>(\d)</relay2state>', raw_result).group(1)))

    if tunits == 'C':
        temp1 = temp1*9./5. + 32.
        tunits = 'F'

    status.dome_temperature = temp1
    status.fan_state = r1state
    status.fan_enable = r2state





#     import urllib
#     from xml.dom import minidom
#     logger.info('Getting CBW temperature module status')
#     if ('RCOS temperature units' in focuser_info.keys()) and ('RCOS temperature (truss)' in focuser_info.keys()):
#         if focuser_info['RCOS temperature units'] == 'F':
#             InsideTemp = focuser_info['RCOS temperature (truss)']
#         else:
#             logger.error('  Focuser temperature unit mismatch')
#             return {}
#     else:
#         logger.error('  Focuser temperature unit not found')
#         return {}
# 
#     if ('boltwood temp units' in boltwood.keys()) and ('boltwood ambient temp' in boltwood.keys()):
#         if boltwood['boltwood temp units'] == 'F':
#             OutsideTemp = boltwood['boltwood ambient temp']
#         else:
#             logger.error('  Boltwood temperature unit mismatch')
#             return{}
#     else:
#         logger.error('  Boltwood temperature unit not found')
#         return{}
# 
#     CBW_info = {}
#     IPaddress = "192.168.1.115"
#     try:
#         page = urllib.urlopen("http://"+IPaddress+"/state.xml")
#         contents = page.read()
#         ContentLines = contents.splitlines()
#         xmldoc = minidom.parseString(contents)
#         CBW_info['CBW temperature units'] = str(xmldoc.getElementsByTagName('units')[0].firstChild.nodeValue)
#         CBW_info['CBW temp1'] = float(xmldoc.getElementsByTagName('sensor1temp')[0].firstChild.nodeValue)
#         logger.debug('  Temp1 = {:.1f} {}'.format(CBW_info['CBW temp1'], CBW_info['CBW temperature units']))
#         CBW_info['CBW temp2'] = float(xmldoc.getElementsByTagName('sensor2temp')[0].firstChild.nodeValue)
#         logger.debug('  Temp2 = {:.1f} {}'.format(CBW_info['CBW temp2'], CBW_info['CBW temperature units']))
#         if CBW_info['CBW temperature units'] == "C":
#             CBW_info['CBW temp1'] = CBW_info['CBW temp1']*9./5. + 32.
#             CBW_info['CBW temp2'] = CBW_info['CBW temp2']*9./5. + 32.
#             CBW_info['CBW temperature units'] = 'F'
#             logger.info('  Temp1 = {:.1f} {}'.format(CBW_info['CBW temp1'], CBW_info['CBW temperature units']))
#             logger.debug('  Temp2 = {:.1f} {}'.format(CBW_info['CBW temp2'], CBW_info['CBW temperature units']))
#         CBW_info['CBW fan state'] = bool(xmldoc.getElementsByTagName('relay1state')[0].firstChild.nodeValue)
#         logger.info('  Fans On? = {}'.format(CBW_info['CBW fan state']))
#         CBW_info['CBW fan enable'] = bool(xmldoc.getElementsByTagName('relay2state')[0].firstChild.nodeValue)
#         logger.debug('  Fan Control Enabled? = {}'.format(CBW_info['CBW fan enable']))
#     except:
#         logger.error('Could not connect to CBW temperature module.')
#         return {}
# 
#     ## Control Fans
#     DeadbandHigh = 0.5
#     DeadbandLow = 3.0
# 
#     ## If fan enable not on, return values and stop
#     if not CBW_info['CBW fan enable']:
#         if CBW_info['CBW fan state']:
#             logger.info("  Turning Dome Fan Off.  Remote Control Set to Off.")
#             page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
#         return CBW_info
#     
#     ## If fans should be on or off based on the time of day
#     operate_fans_now = True
#     
#     ## Set state of fans based on temperature
#     if OutsideTemp and InsideTemp:
#         logger.debug('  Inside Temp = {:.1f}'.format(InsideTemp))
#         logger.debug('  Outside Temp = {:.1f}'.format(OutsideTemp))
#         DeltaT = InsideTemp - OutsideTemp
# 
#         ## Turn on Fans if Inside Temperature is High
#         if operate_fans_now and (InsideTemp > OutsideTemp + DeadbandHigh):
#             if not CBW_info['CBW fan state']:
#                 logger.info("  Turning Dome Fan On.  DeltaT = %.1f" % DeltaT)
#                 page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=1")
#                 CBW_info['CBW fan state'] = True
#             else:
#                 logger.debug("  Leaving Dome Fan On.  DeltaT = %.1f" % DeltaT)
#         ## Turn off Fans if Inside Temperature is Low
#         elif operate_fans_now and (InsideTemp < OutsideTemp - DeadbandLow):
#             if CBW_info['CBW fan state']:
#                 logger.info("  Turning Dome Fan Off.  DeltaT = %.1f" % DeltaT)
#                 page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
#                 CBW_info['CBW fan state'] = False
#             else:
#                 logger.debug("  Leaving Dome Fan Off.  DeltaT = %.1f" % DeltaT)
#         ## Turn off Fans if it is night
#         elif not operate_fans_now:
#             if CBW_info['CBW fan state']:
#                 logger.info("  Turning Dome Fan Off for Night.  DeltaT = %.1f" % DeltaT)
#                 page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
#                 CBW_info['CBW fan state'] = False
#             else:
#                 logger.debug("  Leaving Dome Fan Off.  DeltaT = %.1f" % DeltaT)

    return status


def get_status_and_log(telescope, logger):
    ## Set up log file output
    LogFilePath = os.path.join('Z:\\', 'Logs', DateString)
    if not os.path.exists(LogFilePath):
        os.mkdir(LogFilePath)
    LogFile = os.path.join(LogFilePath, 'get_status_{}.log'.format(DateString))
    LogFileHandler = logging.FileHandler(LogFile)
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)

    logger.info('#### Starting Status Queries ####')

    ##-------------------------------------------------------------------------
    ## Get Status Info
    ##-------------------------------------------------------------------------
    logger.info('Connecting to mongo db at 192.168.1.101')
    try:
        me.connect('vysos', host='192.168.1.101')
    except:
        logger.error('Could not connect to mongo db')
        raise Error('Failed to connect to mongo')
    else:
        status = telstatus(telescope=telescope, current=True,
                           date=datetime.datetime.utcnow())
        status = get_telescope_info(status, logger)
        status = get_focuser_info(status, logger)

    ncurrent = len(telstatus.objects(__raw__={'current': True, 'telescope': telescope}))
    if ncurrent < 1:
        logger.error('No exiting "current" document found!')
    elif ncurrent == 1:
        logger.info('Modifying old "current" document')
        telstatus.objects(__raw__={'current': True, 'telescope': telescope}).update_one(set__current=False)
        logger.info('  Done')
    else:
        logger.error('Multiple ({}) exiting "current" document found!'.format(ncurrent))
        logger.info('Updating old "current" documents')
        telstatus.objects(__raw__={'current': True, 'telescope': telescope}).update(set__current=False, multi=True)
        logger.info('  Done')

    try:
        logger.info('Saving new "current" document')
        status.save()
        logger.info("  Done")
        logger.info("\n{}".format(status))
    except:
        logger.error('Failed to add new document')


if __name__ == '__main__':

    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = argparse.ArgumentParser(
             description="Program description.")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    ## add arguments
    parser.add_argument("-t",
        type=str, dest="telescope", default='',
        choices=['V5', 'V20', ''], required=False,
        help="The telescope system we are querying.  Will query weather if not specified.")
    args = parser.parse_args()

    telescope = args.telescope

    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    now = datetime.datetime.utcnow()
    DateString = now.strftime("%Y%m%dUT")
    TimeString = now.strftime("%H:%M:%S")
    logger = logging.getLogger('get_status_{}'.format(DateString))
    if len(logger.handlers) < 1:
        logger.setLevel(logging.DEBUG)
        ## Set up console output
        LogConsoleHandler = logging.StreamHandler()
        if args.verbose:
            LogConsoleHandler.setLevel(logging.DEBUG)
        else:
            LogConsoleHandler.setLevel(logging.INFO)
        LogFormat = logging.Formatter('%(asctime)s %(levelname)8s: %(message)s',
                                      datefmt='%Y%m%d %H:%M:%S')
        LogConsoleHandler.setFormatter(LogFormat)
        logger.addHandler(LogConsoleHandler)


    while True:
        if telescope in ['V5', 'V20']:
            import win32com.client
            import pywintypes
            get_status_and_log(telescope, logger)
        else:
            get_weather(logger)
        logging.shutdown()
        time.sleep(20)
