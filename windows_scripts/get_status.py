#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import shutil
import argparse
import logging
import time
import datetime

import win32com.client
import urllib
from xml.dom import minidom
import numpy as np


def get_clarity(ClarityDataFile):
    with open(ClarityDataFile, 'r') as clarityFO:
        data = clarityFO.read().split()

    if len(data) != 20:
        return {}

    clarity = {}
    clarity['date'] = data[0]                # local date (yyyy-mm-dd)
    clarity['time'] = data[1]                # local time (hh:mm:ss.ss)
    clarity['temp_units'] = data[2]          # 'C' or 'F'
    clarity['wind_units'] = data[3]          # 'K' = km/hr, 'M' = 'mph', 'm' = m/s
    clarity['sky_temp'] = float(data[4])     # 999 for saturated hot, -999 saturated cold, -998 wet
    clarity['ambient_temp'] = float(data[5]) # 
    clarity['sensor_temp'] = float(data[6])  # 999 for saturated hot, -999 saturated cold
    clarity['wind_speed'] = float(data[7])   # -1 = heating up, -2 = wet, -3,-4,-5,-6 = fail
    clarity['humidity'] = int(data[8])       # %
    clarity['dew_point'] = float(data[9])    # 
    clarity['heater'] = int(data[10])        # heater power in %
    clarity['rain'] = int(data[11])          # 0 = dry, 1 = rain in last minute, 2 = rain now
    clarity['wet'] = int(data[12])           # 0 = dry, 1 = wet in last minute, 2 = wet now
    clarity['since'] = data[13]              # seconds since last valid data
    clarity['now_days'] = data[14]           # date/time when clarity wrote this file
    clarity['cloud'] = int(data[15])         # 0 = unknown, 1 = clear, 2 = cloudy, 3 = very cloudy
    clarity['wind'] = int(data[16])          # 0 = unknown, 1 = calm, 2 = windy, 3 = very windy
    clarity['rain'] = int(data[17])          # 0 = unknown, 1 = dry, 2 = wet, 3 = rain
    clarity['day'] = int(data[18])           # 0 = unknown, 1 = dark, 2 = light, 3 = very light
    clarity['roof'] = int(data[19])          # 0 = not requested, 1 = requested
#     clarity['alert'] = data[20]            # 0 = no alert, 1 = alert

    ## Check that Data File is not Stale
    now = datetime.datetime.now()
    ClarityTime = datetime.datetime.strptime(clarity['date']+' '+clarity['time'][0:-3], '%Y-%m-%d %H:%M:%S')
    difference = now - ClarityTime
    if difference.seconds > 30.0:
        return {}

    ## Standardize Temperature Units to Farenheit (F)
    if clarity['temp_units'] == "C":
        ## Change Units to F
        clarity['sky_temp'] = clarity['sky_temp']*9./5. + 32.
        clarity['ambient_temp'] = clarity['ambient_temp']*9./5. + 32.
        clarity['sensor_temp'] = clarity['sensor_temp']*9./5. + 32.
        clarity['dew_point'] = clarity['dew_point']*9./5. + 32.
        clarity['temp_units'] = 'F'
    elif clarity['temp_units'] == "F":
        pass
    else:
        return {}

    ## Standardize Wind Speed Units to Miles Per Hour (MPH)
    if clarity['wind_units'] == "M":
        ## units are MPH
        pass
    elif clarity['wind_units'] == "K":
        ## units are KPH
        clarity['wind_speed'] = clarity['wind_speed'] * 0.621
        clarity['wind_units'] = "M"
    elif clarity['wind_units'] == "m":
        clarity['wind_speed'] = clarity['wind_speed'] * 2.237
        clarity['wind_units'] = "M"
    else:
        ClarityGood == False

    return clarity


##-------------------------------------------------------------------------
## Query ASCOM ACPHub for Telescope Position and State
##-------------------------------------------------------------------------
def get_telescope_info():
    ACP = None
    ACP_is_connected = None
    try:
        ACP = win32com.client.Dispatch("ACP.Telescope")
    except:
        return {}

    telescope_info = {}
    telescope_info['connected'] = ACP.Connected
    if ACP.Connected:
        telescope_info['at_park'] = ACP.AtPark
        telescope_info['alt'] = float(ACP.Altitude)
        telescope_info['az']  = float(ACP.Azimuth)
        telescope_info['slewing']  = ACP.Slewing
        telescope_info['tracking'] = ACP.Tracking

    return telescope_info


##-------------------------------------------------------------------------
## Query ASCOM Focuser for Position, Temperature, Fan State
##-------------------------------------------------------------------------
def get_focuser_info(telescope):
    focuser_info = {}
    if telescope == "V20":
        try:
            RCOST = win32com.client.Dispatch("RCOS_AE.Temperature")
            RCOSF = win32com.client.Dispatch("RCOS_AE.Focuser")
        except:
            return {}

        ## Get Average of 5 Temperature Readings
        RCOS_Truss_Temps = []
        RCOS_Primary_Temps = []
        RCOS_Secondary_Temps = []
        RCOS_Fan_Speeds = []
        RCOS_Focus_Positions = []
        print(' RCOS Data:  {:>7s}, {:>7s}, {:>7s}, {:>7s}, {:>5s}'.format('Truss', 'Pri', 'Sec', 'Fan', 'Foc'))
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

                print('  RCOS Data:  {:5.1f} F, {:5.1f} F, {:5.1f} F, {:5.0f} %, {:5d}'.format(new_Truss_Temp, new_Pri_Temp, new_Sec_Temp, new_Fan_Speed, new_Focus_Pos))
            except:
                pass
            time.sleep(1)
        if len(RCOS_Truss_Temps) >= 3:
            focuser_info['temperature (truss)'] = float(np.median(RCOS_Truss_Temps))
        else:
            focuser_info['temperature (truss)'] = float('nan')
        if len(RCOS_Primary_Temps) >= 3:
            focuser_info['temperature (primary)'] = float(np.median(RCOS_Primary_Temps))
        else:
            focuser_info['temperature (primary)'] = float('nan')
        if len(RCOS_Secondary_Temps) >= 3:
            focuser_info['temperature (secondary)'] = float(np.median(RCOS_Secondary_Temps))
        else:
            focuser_info['temperature (secondary)'] = float('nan')
        if len(RCOS_Fan_Speeds) >= 3:
            focuser_info['fan speed'] = int(np.median(RCOS_Fan_Speeds))
        else:
            focuser_info['fan speed'] = float('nan')
        if len(RCOS_Focus_Positions) >= 3:
            focuser_info['position'] = int(np.median(RCOS_Focus_Positions))
        else:
            focuser_info['position'] = float('nan')
    elif telescope == "V5":
        try:
            FocusMax = win32com.client.Dispatch("FocusMax.Focuser")
            if not FocusMax.Link:
                try:
                    FocusMax.Link = True
                except:
                    return {}
        except:
                    return {}

        ## Get Average of 3 Temperature Readings
        FocusMax_Temps = []
        for i in range(0,3,1):
            try:
                newtemp = float(FocusMax.Temperature)*9./5. + 32.
                FocusMax_Temps.append(newtemp)
            except:
                pass
        if len(FocusMax_Temps) > 0:
            ## Filter out bad values
            median_temp = np.median(FocusMax_Temps)
            if (median_temp > -10) and (median_temp < 150):
                focuser_info['temperature (tube)'] = median_temp
        ## Get Position
        try:
            focuser_info['position'] = int(FocusMax.Position)
        except:
            pass

    return focuser_info


##-------------------------------------------------------------------------
## Query ControlByWeb Temperature Module for Temperature and Fan State
##-------------------------------------------------------------------------
def control_by_web(InsideTemp, OutsideTemp):
    CBW_info = {}
    IPaddress = "192.168.1.115"
    try:
        page = urllib.urlopen("http://"+IPaddress+"/state.xml")
        contents = page.read()
        ContentLines = contents.splitlines()
        xmldoc = minidom.parseString(contents)
        CBW_info['units'] = str(xmldoc.getElementsByTagName('units')[0].firstChild.nodeValue)
        CBW_info['temp1'] = float(xmldoc.getElementsByTagName('sensor1temp')[0].firstChild.nodeValue)
        CBW_info['temp2'] = float(xmldoc.getElementsByTagName('sensor2temp')[0].firstChild.nodeValue)
        CBW_info['fan state'] = bool(xmldoc.getElementsByTagName('relay1state')[0].firstChild.nodeValue)
        CBW_info['fan enable'] = bool(xmldoc.getElementsByTagName('relay2state')[0].firstChild.nodeValue)
        if CBW_info['units'] == "C":
            CBW_info['temp1'] = CBW_info['temp1']*9./5. + 32.
            CBW_info['temp2'] = CBW_info['temp2']*9./5. + 32.
            CBW_info['units'] = 'F'
    except:
        return {}

    for item in CBW_info:
        print(item, CBW_info[item])

    ## Control Fans
    DeadbandHigh = 0.1
    DeadbandLow = 2.0

    ## If fan enable not on, return values and stop
    if not CBW_info['fan enable']:
        if CBW_info['fan state']:
            print("  Turning Dome Fan Off.  Remote Control Set to Off.")
            page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
        return CBW_info
    
    ## If fans should be on or off based on the time of day
    operate_fans_now = True
    
    ## Set state of fans based on temperature
    if OutsideTemp and InsideTemp:
        print('Inside Temp = {:.1f}'.format(InsideTemp))
        print('Outside Temp = {:.1f}'.format(OutsideTemp))
        DeltaT = InsideTemp - OutsideTemp

        ## Turn on Fans if Inside Temperature is High
        if operate_fans_now and (InsideTemp > OutsideTemp + DeadbandHigh):
            if not CBW_info['fan state']:
                print("  Turning Dome Fan On.  DeltaT = %.1f" % DeltaT)
                page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=1")
                CBW_info['fan state'] = True
        ## Turn off Fans if Inside Temperature is Low
        elif operate_fans_now and (InsideTemp < OutsideTemp - DeadbandLow):
            if CBW_info['fan state']:
                print("  Turning Dome Fan Off.  DeltaT = %.1f" % DeltaT)
                page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
                CBW_info['fan state'] = False
        ## Turn off Fans if it is night
        elif not operate_fans_now:
            if CBW_info['fan state']:
                print("  Turning Dome Fan Off for Night.  DeltaT = %.1f" % DeltaT)
                page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
                CBW_info['fan state'] = False

    return CBW_info


def main():
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

    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('get_status')
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
    now = datetime.datetime.utcnow()
    DateString = now.strftime("%Y%m%dUT")
    LogFilePath = os.path.join('C:\\', 'Data_'+telescope, 'Logs', DateString)
    if not os.path.exists(LogFilePath):
        os.mkdir(LogFilePath)
    LogFile = os.path.join(LogFilePath, 'get_status.log')
    LogFileHandler = logging.FileHandler(LogFile)
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)

    ##-------------------------------------------------------------------------
    ## Get Status Info
    ##-------------------------------------------------------------------------
    clarity_file = os.path.join("C:\\", "Users", "vysosuser", "Documents", "ClarityII", "ClarityData.txt")
    clarity = get_clarity(clarity_file)
#     for item in clarity:
#         print(item, clarity[item])

    telescope_info = get_telescope_info()
    for item in telescope_info:
        print(item, telescope_info[item])

    focuser_info = get_focuser_info(telescope)
    for item in focuser_info:
        print(item, focuser_info[item])

    if telescope == 'V20':
        CBW_info = control_by_web(focuser_info['temperature (truss)'], clarity['ambient_temp'])
        for item in CBW_info:
            print(item, CBW_info[item])




if __name__ == '__main__':
    main()
