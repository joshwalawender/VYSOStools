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
    fan_speed = me.DecimalField(min_value=0, max_value=100, precision=1)
    truss_temperature  = me.DecimalField(min_value=-50, max_value=120, precision=1)
    primary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    secondary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
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
        if self.truss_temperature: output += '  truss_temperature: {:.1f}\n'.format(self.truss_temperature)
        if self.primary_temperature: output += '  primary_temperature: {:.1f}\n'.format(self.primary_temperature)
        if self.secondary_temperature: output += '  secondary_temperature: {:.1f}\n'.format(self.secondary_temperature)
        if self.fan_speed: output += '  fan_speed: {}\n'.format(self.fan_speed)
        if self.dome_temperature: output += '  dome_temperature: {:.1f}\n'.format(self.dome_temperature)
        if self.fan_state: output += '  fan_state: {}\n'.format(self.fan_state)
        if self.fan_enable: output += '  fan_enable: {}\n'.format(self.fan_enable)
        return output

    def __repr__(self):
        return self.__str__()



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
            newtemp = float(FocusMax.Temperature)
            logger.debug('  Queried FocusMax temperature = {:.1f}'.format(newtemp))
            FocusMax_Temps.append(newtemp)
        except:
            pass
    if len(FocusMax_Temps) > 0:
        ## Filter out bad values
        median_temp = np.median(FocusMax_Temps)
        if (median_temp > -10) and (median_temp < 150):
            status.focuser_temperature = median_temp
            logger.info('  FocusMax temperature = {:.1f} {}'.format(status.focuser_temperature, 'C'))
    ## Get Position
    try:
        status.focuser_position = int(FocusMax.Position)
        logger.info('  FocusMax position = {:d}'.format(status.focuser_position))
    except:
        pass

    return status


##-------------------------------------------------------------------------
## Query RCOS TCC
##-------------------------------------------------------------------------
def get_RCOS_info(status, logger):
    logger.info('Getting RCOS TCC status')
    try:
        RCOST = win32com.client.Dispatch("RCOS_AE.Temperature")
        RCOSF = win32com.client.Dispatch("RCOS_AE.Focuser")
        logger.debug('  Connected to RCOS focuser')
    except:
        logger.error('Could not connect to RCOS ASCOM object.')
        return status

    ## Get Average of 5 Temperature Readings
    RCOS_Truss_Temps = []
    RCOS_Primary_Temps = []
    RCOS_Secondary_Temps = []
    RCOS_Fan_Speeds = []
    RCOS_Focus_Positions = []
    logger.debug('  {:>7s}, {:>7s}, {:>7s}, {:>7s}, {:>5s}'.format('Truss', 'Pri', 'Sec', 'Fan', 'Foc'))
    for i in range(0,5,1):
        try:
            new_Truss_Temp = RCOST.AmbientTemp
            if new_Truss_Temp > 20 and new_Truss_Temp < 120:
                RCOS_Truss_Temps.append(new_Truss_Temp)
            else:
                new_Truss_Temp = float('nan')

            new_Pri_Temp = RCOST.PrimaryTemp
            if new_Pri_Temp > 20 and new_Pri_Temp < 120:
                RCOS_Primary_Temps.append(new_Pri_Temp)
            else:
                new_Pri_Temp = float('nan')

            new_Sec_Temp = RCOST.SecondaryTemp
            if new_Sec_Temp > 20 and new_Sec_Temp < 120:
                RCOS_Secondary_Temps.append(new_Sec_Temp)
            else:
                new_Sec_Temp = float('nan')

            new_Fan_Speed = RCOST.FanSpeed
            RCOS_Fan_Speeds.append(new_Fan_Speed)

            new_Focus_Pos = RCOSF.Position
            RCOS_Focus_Positions.append(new_Focus_Pos)

            logger.debug('  {:5.1f} F, {:5.1f} F, {:5.1f} F, {:5.0f} %, {:5d}'.format(new_Truss_Temp, new_Pri_Temp, new_Sec_Temp, new_Fan_Speed, new_Focus_Pos))
        except:
            pass
        time.sleep(1)
    if len(RCOS_Truss_Temps) >= 3:
        status.truss_temperature = (float(np.median(RCOS_Truss_Temps)) - 32.)/1.8
        logger.info('  RCOS temperature (truss) = {:.1f} {}'.format(
                    status.truss_temperature, 'C'))
    if len(RCOS_Primary_Temps) >= 3:
        status.primary_temperature = (float(np.median(RCOS_Primary_Temps)) - 32.)/1.8
        logger.info('  RCOS temperature (primary) = {:.1f} {}'.format(
                    status.primary_temperature, 'C'))
    if len(RCOS_Secondary_Temps) >= 3:
        status.secondary_temperature = (float(np.median(RCOS_Secondary_Temps)) - 32.)/1.8
        logger.info('  RCOS temperature (secondary) = {:.1f} {}'.format(
                    status.secondary_temperature, 'C'))
    if len(RCOS_Fan_Speeds) >= 3:
        status.fan_speed = float(np.median(RCOS_Fan_Speeds))
        logger.info('  RCOS fan speed = {:.0f} %'.format(status.fan_speed))

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
#     LogFilePath = os.path.join('Z:\\', 'Logs', DateString)
#     if not os.path.exists(LogFilePath):
#         os.mkdir(LogFilePath)
#     LogFile = os.path.join(LogFilePath, 'get_status_{}.log'.format(DateString))
#     LogFileHandler = logging.FileHandler(LogFile)
#     LogFileHandler.setLevel(logging.DEBUG)
#     LogFileHandler.setFormatter(LogFormat)
#     logger.addHandler(LogFileHandler)

    ##-------------------------------------------------------------------------
    ## Get Status Info
    ##-------------------------------------------------------------------------
    logger.info('#### Starting Status Queries ####')
    status = telstatus(telescope=telescope, current=True,
                       date=datetime.datetime.utcnow())
    status = get_telescope_info(status, logger)
    status = get_focuser_info(status, logger)
    if telescope == 'V20':
        status = get_RCOS_info(status, logger)

    ##-------------------------------------------------------------------------
    ## Write to Mongo
    ##-------------------------------------------------------------------------
    logger.info('Connecting to mongo db at 192.168.1.101')
    try:
        me.connect('vysos', host='192.168.1.101')

        ## Edit old "current" entry to be not current
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

        ## Save new "current" document
        try:
            logger.info('Saving new "current" document')
            status.save()
            logger.info("  Done")
            logger.info("\n{}".format(status))
        except:
            logger.error('Failed to add new document')

    except:
        logger.error('Could not connect to mongo db')
        raise Error('Failed to connect to mongo')


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