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
# import yaml
import numpy as np

import win32com.client
import urllib
from xml.dom import minidom
import pymongo
from pymongo import MongoClient

def get_boltwood(ClarityDataFile, logger):
    logger.info('Reading Clarity file')
    logger.debug('  Clarity File: {}'.format(ClarityDataFile))
    if not os.path.exists(ClarityDataFile):
        logger.error('Could not find Clarity file.')
        return {}

    with open(ClarityDataFile, 'r') as clarityFO:
        data = clarityFO.read().split()

    if len(data) != 20:
        return {}
    logger.debug('  Read Clarity file.')

    boltwood = {}
    boltwood['boltwood date'] = data[0]                # local date (yyyy-mm-dd)
    boltwood['boltwood time'] = data[1]                # local time (hh:mm:ss.ss)
    logger.debug('  Date and Time: {} {}'.format(boltwood['boltwood date'], boltwood['boltwood time']))
    ## If boltwood time ends in :60 seconds, change to make valid for datetime module
    Match60 = re.match('(\d{1,2}):(\d{2}):(60\.\d{2})', boltwood['boltwood time'])
    if Match60:
        logger.debug('  Changing boltwood time to end in :59.99')
        boltwood['boltwood time'] = '{:2d}:{:2d}:{:5.2f}'.format(\
                                     int(Match60.group(1)),\
                                     int(Match60.group(2)),\
                                     59.99)
                                     

    boltwood['boltwood temp units'] = data[2]          # 'C' or 'F'
    boltwood['boltwood wind units'] = data[3]          # 'K' = km/hr, 'M' = 'mph', 'm' = m/s

    if (float(data[4]) != 999.) and (float(data[4]) != -999.) and (float(data[4]) != -998.):
        boltwood['boltwood sky temp'] = float(data[4])     # 999 for saturated hot, -999 saturated cold, -998 wet
    logger.info('  Sky Temp = {:.2f} {}'.format(float(data[4]), boltwood['boltwood temp units']))

    boltwood['boltwood ambient temp'] = float(data[5]) # 
    logger.debug('  Ambient Temp = {:.2f} {}'.format(boltwood['boltwood ambient temp'], boltwood['boltwood temp units']))

    if (data[6] != '999') and (data[6] != '-999'):
        boltwood['boltwood sensor temp'] = float(data[6])  # 999 for saturated hot, -999 saturated cold
    logger.debug('  Sensor Temp = {:.2f} {}'.format(float(data[6]), boltwood['boltwood temp units']))

    if float(data[7]) >=0:
        boltwood['boltwood wind speed'] = float(data[7])   # -1 = heating up, -2 = wet, -3,-4,-5,-6 = fail
    logger.info('  Wind Speed = {:.2f} {}'.format(float(data[7]), boltwood['boltwood wind units']))

    boltwood['boltwood humidity'] = int(data[8])       # %
    logger.info('  Humidity = {} %'.format(boltwood['boltwood humidity']))

    boltwood['boltwood dew point'] = float(data[9])    # 
    logger.debug('  Dew Point = {:.2f} {}'.format(boltwood['boltwood dew point'], boltwood['boltwood temp units']))

    boltwood['boltwood heater'] = int(data[10])        # heater power in %
    logger.debug('  Heater Power = {} %'.format(boltwood['boltwood heater']))

    boltwood['boltwood rain status'] = int(data[11])          # 0 = dry, 1 = rain in last minute, 2 = rain now
    logger.debug('  Rain Status = {}'.format(boltwood['boltwood rain status']))

    boltwood['boltwood wet status'] = int(data[12])           # 0 = dry, 1 = wet in last minute, 2 = wet now
    logger.debug('  Wetness Status = {}'.format(boltwood['boltwood wet status']))

    boltwood['boltwood since'] = data[13]              # seconds since last valid data
    logger.debug('  Seconds Since Last Valid Data = {}'.format(boltwood['boltwood since']))

    boltwood['boltwood nowdays'] = data[14]           # date/time when boltwood wrote this file
    logger.debug('  Date/time when boltwood wrote this file = {}'.format(boltwood['boltwood nowdays']))

    boltwood['boltwood cloud condition'] = int(data[15])         # 0 = unknown, 1 = clear, 2 = cloudy, 3 = very cloudy
    logger.info('  Cloud Condition = {}'.format(boltwood['boltwood cloud condition']))

    boltwood['boltwood wind condition'] = int(data[16])          # 0 = unknown, 1 = calm, 2 = windy, 3 = very windy
    logger.info('  Wind Condition = {}'.format(boltwood['boltwood wind condition']))

    boltwood['boltwood rain condition'] = int(data[17])          # 0 = unknown, 1 = dry, 2 = wet, 3 = rain
    logger.info('  Rain Condition = {}'.format(boltwood['boltwood rain condition']))

    boltwood['boltwood day condition'] = int(data[18])           # 0 = unknown, 1 = dark, 2 = light, 3 = very light
    logger.info('  Day Condition = {}'.format(boltwood['boltwood day condition']))

    boltwood['boltwood roof close'] = int(data[19])          # 0 = not requested, 1 = requested
    logger.info('  Roof Close = {}'.format(boltwood['boltwood roof close']))


    ## Check that Data File is not Stale
    now = datetime.datetime.now()
    ClarityTime = datetime.datetime.strptime(boltwood['boltwood date']+' '+boltwood['boltwood time'][0:-3], '%Y-%m-%d %H:%M:%S')
    difference = now - ClarityTime
    if difference.seconds > 30.0:
        logger.error('Boltwood data appears stale!')
        return {}

    ## Standardize Temperature Units to Farenheit (F)
    if boltwood['boltwood temp units'] == "C":
        ## Change Units to F
        if 'boltwood sky temp' in boltwood.keys():
            boltwood['boltwood sky temp'] = boltwood['boltwood sky temp']*9./5. + 32.
        if 'boltwood ambient temp' in boltwood.keys():
            boltwood['boltwood ambient temp'] = boltwood['boltwood ambient temp']*9./5. + 32.
        if 'boltwood sensor temp' in boltwood.keys():
            boltwood['boltwood sensor temp'] = boltwood['boltwood sensor temp']*9./5. + 32.
        if 'boltwood dew point' in boltwood.keys():
            boltwood['boltwood dew point'] = boltwood['boltwood dew point']*9./5. + 32.
        boltwood['boltwood temp units'] = 'F'
        logger.debug('  Changed boltwood temperature units to F')
    elif boltwood['boltwood temp units'] == "F":
        pass

    ## Standardize Wind Speed Units to Miles Per Hour (MPH)
    if 'boltwood wind speed' in boltwood.keys():
        if boltwood['boltwood wind units'] == "M":
            ## units are MPH
            pass
        elif boltwood['boltwood wind units'] == "K":
            ## units are KPH
            boltwood['boltwood wind speed'] = boltwood['boltwood wind speed'] * 0.621
            boltwood['boltwood wind units'] = "M"
            logger.debug('  Changed boltwood wind speed units to mph')
        elif boltwood['boltwood wind units'] == "m":
            boltwood['boltwood wind speed'] = boltwood['boltwood wind speed'] * 2.237
            boltwood['boltwood wind units'] = "M"
            logger.debug('  Changed boltwood wind speed units to mph')

    return boltwood


##-------------------------------------------------------------------------
## Query ASCOM ACPHub for Telescope Position and State
##-------------------------------------------------------------------------
def get_telescope_info(logger):
    logger.info('Getting ACP status')
    try:
        ACP = win32com.client.Dispatch("ACP.Telescope")
    except:
        logger.error('Could not connect to ACP ASCOM object.')
        return {}

    telescope_info = {}
    try:
        telescope_info['ACP connected'] = ACP.Connected
        logger.debug('  ACP Connected = {}'.format(telescope_info['ACP connected']))
        if ACP.Connected:
            telescope_info['ACP park status'] = ACP.AtPark
            logger.info('  ACP At Park = {}'.format(telescope_info['ACP park status']))
            telescope_info['ACP alt'] = float(ACP.Altitude)
            logger.info('  ACP Alt = {:.2f}'.format(telescope_info['ACP alt']))
            telescope_info['ACP az']  = float(ACP.Azimuth)
            logger.info('  ACP Az = {:.2f}'.format(telescope_info['ACP az']))
            telescope_info['ACP slewing status']  = ACP.Slewing
            logger.info('  ACP Slewing = {}'.format(telescope_info['ACP slewing status']))
            telescope_info['ACP tracking status'] = ACP.Tracking
            logger.info('  ACP Tracking = {}'.format(telescope_info['ACP tracking status']))
            try:
                telescope_info['ACP target RA'] = ACP.TargetRightAscension
                logger.info('  ACP target RA = {}'.format(telescope_info['ACP target RA']))
                logger.info('  ACP target Dec = {}'.format(telescope_info['ACP target Dec']))
                telescope_info['ACP target Dec'] = ACP.TargetDeclination
            except:
                logger.info('  Could not get target info')
    except:
        telescope_info['ACP connected'] = False
        logger.warning('Queries to ACP object failed')

    return telescope_info


##-------------------------------------------------------------------------
## Query ASCOM Focuser for Position, Temperature, Fan State
##-------------------------------------------------------------------------
def get_focuser_info(telescope, logger):
    logger.info('Getting ASCOM focuser status')
    focuser_info = {}
    if telescope == "V20":
        try:
            RCOST = win32com.client.Dispatch("RCOS_AE.Temperature")
            RCOSF = win32com.client.Dispatch("RCOS_AE.Focuser")
            logger.debug('  Connected to RCOS focuser')
        except:
            logger.error('Could not connect to RCOS ASCOM object.')
            return {}

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
        focuser_info['RCOS temperature units'] = 'F'
        if len(RCOS_Truss_Temps) >= 3:
            focuser_info['RCOS temperature (truss)'] = float(np.median(RCOS_Truss_Temps))
            logger.info('  RCOS temperature (truss) = {:.1f} {}'.format(focuser_info['RCOS temperature (truss)'], focuser_info['RCOS temperature units']))
        if len(RCOS_Primary_Temps) >= 3:
            focuser_info['RCOS temperature (primary)'] = float(np.median(RCOS_Primary_Temps))
            logger.info('  RCOS temperature (primary) = {:.1f} {}'.format(focuser_info['RCOS temperature (primary)'], focuser_info['RCOS temperature units']))
        if len(RCOS_Secondary_Temps) >= 3:
            focuser_info['RCOS temperature (secondary)'] = float(np.median(RCOS_Secondary_Temps))
            logger.info('  RCOS temperature (secondary) = {:.1f} {}'.format(focuser_info['RCOS temperature (secondary)'], focuser_info['RCOS temperature units']))
        if len(RCOS_Fan_Speeds) >= 3:
            focuser_info['RCOS fan speed'] = int(np.median(RCOS_Fan_Speeds))
            logger.info('  RCOS fan speed = {:d} %'.format(focuser_info['RCOS fan speed']))
        if len(RCOS_Focus_Positions) >= 3:
            focuser_info['RCOS focuser position'] = int(np.median(RCOS_Focus_Positions))
            logger.info('  RCOS focuser position = {:d}'.format(focuser_info['RCOS focuser position']))
    elif telescope == "V5":
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
                focuser_info['FocusMax temperature (tube)'] = median_temp
                focuser_info['FocusMax units'] = 'F'
                logger.info('  FocusMax temperature = {:.1f} {}'.format(median_temp, focuser_info['FocusMax units']))
        ## Get Position
        try:
            focuser_info['FocusMax focuser position'] = int(FocusMax.Position)
            logger.info('  FocusMax position = {:d}'.format(focuser_info['FocusMax focuser position']))
        except:
            pass

    return focuser_info


##-------------------------------------------------------------------------
## Query ControlByWeb Temperature Module for Temperature and Fan State
##-------------------------------------------------------------------------
def control_by_web(focuser_info, boltwood, logger):
    logger.info('Getting CBW temperature module status')
    if ('RCOS temperature units' in focuser_info.keys()) and ('RCOS temperature (truss)' in focuser_info.keys()):
        if focuser_info['RCOS temperature units'] == 'F':
            InsideTemp = focuser_info['RCOS temperature (truss)']
        else:
            logger.error('  Focuser temperature unit mismatch')
            return {}
    else:
        logger.error('  Focuser temperature unit not found')
        return {}

    if ('boltwood temp units' in boltwood.keys()) and ('boltwood ambient temp' in boltwood.keys()):
        if boltwood['boltwood temp units'] == 'F':
            OutsideTemp = boltwood['boltwood ambient temp']
        else:
            logger.error('  Boltwood temperature unit mismatch')
            return{}
    else:
        logger.error('  Boltwood temperature unit not found')
        return{}

    CBW_info = {}
    IPaddress = "192.168.1.115"
    try:
        page = urllib.urlopen("http://"+IPaddress+"/state.xml")
        contents = page.read()
        ContentLines = contents.splitlines()
        xmldoc = minidom.parseString(contents)
        CBW_info['CBW temperature units'] = str(xmldoc.getElementsByTagName('units')[0].firstChild.nodeValue)
        CBW_info['CBW temp1'] = float(xmldoc.getElementsByTagName('sensor1temp')[0].firstChild.nodeValue)
        logger.debug('  Temp1 = {:.1f} {}'.format(CBW_info['CBW temp1'], CBW_info['CBW temperature units']))
        CBW_info['CBW temp2'] = float(xmldoc.getElementsByTagName('sensor2temp')[0].firstChild.nodeValue)
        logger.debug('  Temp2 = {:.1f} {}'.format(CBW_info['CBW temp2'], CBW_info['CBW temperature units']))
        CBW_info['CBW fan state'] = bool(xmldoc.getElementsByTagName('relay1state')[0].firstChild.nodeValue)
        logger.debug('  Fans On? = {}'.format(CBW_info['CBW fan state']))
        CBW_info['CBW fan enable'] = bool(xmldoc.getElementsByTagName('relay2state')[0].firstChild.nodeValue)
        logger.debug('  Fan Control Enabled? = {}'.format(CBW_info['CBW fan enable']))
        if CBW_info['CBW temperature units'] == "C":
            CBW_info['CBW temp1'] = CBW_info['CBW temp1']*9./5. + 32.
            CBW_info['CBW temp2'] = CBW_info['CBW temp2']*9./5. + 32.
            CBW_info['CBW temperature units'] = 'F'
            logger.debug('  Temp1 = {:.1f} {}'.format(CBW_info['CBW temp1'], CBW_info['CBW temperature units']))
            logger.debug('  Temp2 = {:.1f} {}'.format(CBW_info['CBW temp2'], CBW_info['CBW temperature units']))
    except:
        logger.error('Could not connect to CBW temperature module.')
        return {}

    ## Control Fans
    DeadbandHigh = 0.5
    DeadbandLow = 3.0

    ## If fan enable not on, return values and stop
    if not CBW_info['CBW fan enable']:
        if CBW_info['CBW fan state']:
            logger.info("  Turning Dome Fan Off.  Remote Control Set to Off.")
            page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
        return CBW_info
    
    ## If fans should be on or off based on the time of day
    operate_fans_now = True
    
    ## Set state of fans based on temperature
    if OutsideTemp and InsideTemp:
        logger.debug('  Inside Temp = {:.1f}'.format(InsideTemp))
        logger.debug('  Outside Temp = {:.1f}'.format(OutsideTemp))
        DeltaT = InsideTemp - OutsideTemp

        ## Turn on Fans if Inside Temperature is High
        if operate_fans_now and (InsideTemp > OutsideTemp + DeadbandHigh):
            if not CBW_info['CBW fan state']:
                logger.info("  Turning Dome Fan On.  DeltaT = %.1f" % DeltaT)
                page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=1")
                CBW_info['CBW fan state'] = True
            else:
                logger.debug("  Leaving Dome Fan On.  DeltaT = %.1f" % DeltaT)
        ## Turn off Fans if Inside Temperature is Low
        elif operate_fans_now and (InsideTemp < OutsideTemp - DeadbandLow):
            if CBW_info['CBW fan state']:
                logger.info("  Turning Dome Fan Off.  DeltaT = %.1f" % DeltaT)
                page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
                CBW_info['CBW fan state'] = False
            else:
                logger.debug("  Leaving Dome Fan Off.  DeltaT = %.1f" % DeltaT)
        ## Turn off Fans if it is night
        elif not operate_fans_now:
            if CBW_info['CBW fan state']:
                logger.info("  Turning Dome Fan Off for Night.  DeltaT = %.1f" % DeltaT)
                page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
                CBW_info['CBW fan state'] = False
            else:
                logger.debug("  Leaving Dome Fan Off.  DeltaT = %.1f" % DeltaT)

    return CBW_info


def get_status_and_log(telescope):

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
        LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
        LogConsoleHandler.setFormatter(LogFormat)
        logger.addHandler(LogConsoleHandler)
        ## Set up file output
        LogFilePath = os.path.join('C:\\', 'Data_'+telescope, 'Logs', DateString)
        if not os.path.exists(LogFilePath):
            os.mkdir(LogFilePath)
        LogFile = os.path.join(LogFilePath, 'get_status.log')
        LogFileHandler = logging.FileHandler(LogFile)
        LogFileHandler.setLevel(logging.DEBUG)
        LogFileHandler.setFormatter(LogFormat)
        logger.addHandler(LogFileHandler)

    logger.info('#### Starting Status Queries ####')

    ##-------------------------------------------------------------------------
    ## Setup File to Recieve Data
    ##-------------------------------------------------------------------------
#     DataFilePath = os.path.join("C:\\", "Data_"+telescope, "Logs", DateString)
#     if not os.path.exists(DataFilePath):
#         logger.debug('  Making directory: {}'.format(DataFilePath))
#         os.mkdir(DataFilePath)
#     DataFileName = "status.yaml"
#     DataFile = os.path.join(DataFilePath, DataFileName)

    ##-------------------------------------------------------------------------
    ## Get Status Info
    ##-------------------------------------------------------------------------
    boltwood_file = os.path.join("C:\\", "Users", "vysosuser", "Documents", "ClarityII", "ClarityData.txt")
    boltwood = get_boltwood(boltwood_file, logger)

    telescope_info = get_telescope_info(logger)

    focuser_info = get_focuser_info(telescope, logger)

    if telescope == 'V20':
        CBW_info = control_by_web(focuser_info, boltwood, logger)

    ##-------------------------------------------------------------------------
    ## Write Environmental Log
    ##-------------------------------------------------------------------------
    logger.info('Writing results to mongo db at 192.168.1.101')
    client = MongoClient('192.168.1.101', 27017)
    status = client.vysos['{}status'.format(telescope)]
    logger.debug('  Getting {}status collection'.format(telescope))

    new_data = {}
    new_data.update({'UT date': DateString, 'UT time': TimeString})
    new_data.update(boltwood)
    new_data.update(telescope_info)
    new_data.update(focuser_info)
    if telescope == 'V20':
        new_data.update(CBW_info)

    id = status.insert(new_data)
    logger.debug('  Inserted datum with ID: {}'.format(id))

    logger.info("Done")


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
        type=str, dest="telescope",
        choices=['V5', 'V20'], required=True,
        help="The telescope system we are querying.")
    args = parser.parse_args()

    telescope = args.telescope

    while True:
        get_status_and_log(telescope)
        time.sleep(10)
