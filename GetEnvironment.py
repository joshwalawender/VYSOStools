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

import astropy.io.ascii as ascii
import win32com.client
import urllib
from xml.dom import minidom
import numpy as np


##-------------------------------------------------------------------------
## Write HTML snippet for inclusion in status web page
##-------------------------------------------------------------------------
def write_html_snippet(ClarityArray, Connected, Tracking, Slewing, AtPark, Altitude, Azimuth, telescope, logger):
    SkyTemp = ClarityArray[1]
    AmbTemp = ClarityArray[2]
    WindSpeed = ClarityArray[3]
    Humidity = ClarityArray[4]
    DewPoint = ClarityArray[5]
    CloudCondition = ClarityArray[6]
    WindCondition = ClarityArray[7]
    RainCondition = ClarityArray[8]
    DayCondition = ClarityArray[9]
    RoofClose = ClarityArray[10]

    logger.info("Writing HTML snippet for status page.")
    HTMLfilename = os.path.join("C:\\", "Data_"+telescope, "Boltwood_"+telescope+".html")
    HTMLsnippet = open(HTMLfilename, 'w')
    ## Telescope Name With Roof Close Condition
    HTMLsnippet.write("<tr>\n")
    if RoofClose == 0:
        if telescope == "V5":
            HTMLsnippet.write("  <td colspan=1 style='background-color:green;align:center'><a style='background-color:green;align:center' href='VYSOS5.html'>VYSOS-5</a></td>\n")
        if telescope == "V20":
            HTMLsnippet.write("  <td colspan=1 style='background-color:green;align:center'><a style='background-color:green;align:center' href='VYSOS20.html'>VYSOS-20</a></td>\n")
        if Connected:
            HTMLsnippet.write(  "<td>Alt = %.1f, Az = %.1f</td>\n" % (Altitude, Azimuth))
            StatusString = ""
            if AtPark:
                StatusString = "Parked"
            elif Slewing:
                StatusString = "Slewing"
            elif Tracking:
                StatusString = "Tracking"
            else:
                StatusString = "Not Tracking"
            HTMLsnippet.write(  "<td>%s</td>\n" % StatusString)
        else:
            HTMLsnippet.write(  "<td>Telescope not connected</td>\n")
            HTMLsnippet.write(  "<td>Telescope not connected</td>\n")
    if RoofClose == 1:
        AlertString = ""
        if CloudCondition == 3:
            AlertString += "Clouds"
        if WindCondition == 3:
            AlertString += "Wind"
        if RainCondition >= 2:
            AlertString += "Rain"
        if DayCondition == 3:
            AlertString += "Day"
        if AlertString == "":
            AlertString = "None"
        if telescope == "V5":
            HTMLsnippet.write("  <td colspan=1 style='background-color:red;align:center'><a style='background-color:red;align:center' href='VYSOS5.html'>VYSOS-5</a> (Alerts = %s)</td>\n" % AlertString)
        if telescope == "V20":
            HTMLsnippet.write("  <td colspan=1 style='background-color:red;align:center'><a style='background-color:red;align:center' href='VYSOS20.html'>VYSOS-20</a> (Alerts = %s)</td>\n" % AlertString)
        if Connected:
            HTMLsnippet.write(  "<td>Alt = %.1f, Az = %.1f</td>\n" % (Altitude, Azimuth))
            StatusString = ""
            if AtPark:
                StatusString = "Parked"
            elif Slewing:
                StatusString = "Slewing"
            elif Tracking:
                StatusString = "Tracking"
            else:
                StatusString = "Not Tracking"                
            HTMLsnippet.write(  "<td>%s</td>\n" % StatusString)
        else:
            HTMLsnippet.write(  "<td>Telescope not connected</td>\n")
            HTMLsnippet.write(  "<td>Telescope not connected</td>\n")
    HTMLsnippet.write("</tr>\n")
    HTMLsnippet.write("<tr>\n")
    ## Cloudiness
    if CloudCondition == 0:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>Cloudiness Unknown (%.1f F)</td>\n" % SkyTemp)
    elif CloudCondition == 1:
        HTMLsnippet.write("  <td style='background-color:green;align:center'>Clear (%.1f F)</td>\n" % SkyTemp)
    elif CloudCondition == 2:
        HTMLsnippet.write("  <td style='background-color:yellow;align:center'>Cloudy (%.1f F)</td>\n" % SkyTemp)
    elif CloudCondition == 3:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>Very Cloudy (%.1f F)</td>\n" % SkyTemp)
    else:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>State Reporting Error (%.1f F)</td>\n" % SkyTemp)
    ## Wind
    if RainCondition == 0:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>Wind Speed Unknown (%.1f mph)</td>\n" % WindSpeed)
    elif RainCondition == 1:
        HTMLsnippet.write("  <td style='background-color:green;align:center'>Calm (%.1f mph)</td>\n" % WindSpeed)
    elif RainCondition == 2:
        HTMLsnippet.write("  <td style='background-color:yellow;align:center'>Windy (%.1f mph)</td>\n" % WindSpeed)
    elif RainCondition == 3:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>Very Windy (%.1f mph)</td>\n" % WindSpeed)
    else:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>State Reporting Error (%.1f mph)</td>\n" % WindSpeed)
    ## Rain
    if RainCondition == 0:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>Rain: Unknown</td>\n")
    elif RainCondition == 1:
        HTMLsnippet.write("  <td style='background-color:green;align:center'>Rain: Dry</td>\n")
    elif RainCondition == 2:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>Rain: Wet</td>\n")
    elif RainCondition == 3:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>Rain: Rain</td>\n")
    else:
        HTMLsnippet.write("  <td style='background-color:red;align:center'>error</td>\n")
    
    HTMLsnippet.write("</tr>\n")
    HTMLsnippet.close()



##-------------------------------------------------------------------------
## Read Clarity File
##-------------------------------------------------------------------------
def GetClarity(ClarityDataFile, logger):
    ## Cloud Condition   | Wind Condition   | Rain Condition | Day Condition    | RoofClose
    ##   0 = unknown     |   0 = unknown    |   0 = unknown  |   0 = unknown    |  0 = not requested
    ##   1 = clear       |   1 = calm       |   1 = dry      |   1 = dark       |  1 = requested
    ##   2 = cloudy      |   2 = windy      |   2 = wet      |   2 = light      |
    ##   3 = very cloudy |   3 = very windy |   3 = rain     |   3 = very light | 

    ClarityGood = None
    try:
        ClarityData = ascii.read(ClarityDataFile, guess=False, delimiter=" ", comment="#", data_start=0, Reader=ascii.NoHeader)
        Date             = str(ClarityData[0][0])
        Time             = str(ClarityData[0][1])
        TempUnits        = str(ClarityData[0][2])
        WindUnits        = str(ClarityData[0][3])
        SkyTemp          = float(ClarityData[0][4])
        AmbTemp          = float(ClarityData[0][5])
        SensorTemp       = float(ClarityData[0][6])
        WindSpeed        = float(ClarityData[0][7])
        Humidity         = float(ClarityData[0][8])
        DewPoint         = float(ClarityData[0][9])
        Heater           = ClarityData[0][10]
        RainFlag         = int(ClarityData[0][11])
        WetFlag          = int(ClarityData[0][12])
        Since            = ClarityData[0][13]
        VB6Now           = ClarityData[0][14]
        CloudCondition   = int(ClarityData[0][15])
        WindCondition    = int(ClarityData[0][16])
        RainCondition    = int(ClarityData[0][17])
        DayCondition     = int(ClarityData[0][18])
        RoofClose        = int(ClarityData[0][19])
    except:
        return None

    ## Check that Data File is not Stale
    now = datetime.datetime.now()
    logger.debug('  Clarity File: {} {}'.format(Date, Time))
    logger.debug('  Current (HST): {}'.format(now.strftime('%Y-%m-%d %H:%M:%S')))
    ClarityTime = datetime.datetime.strptime(Date+' '+Time[0:-3], '%Y-%m-%d %H:%M:%S')
    difference = now - ClarityTime
    logger.debug('  Clarity file is stale by {} seconds.'.format(difference.seconds))
    if difference.seconds <= 30.0: ClarityGood = True

    ## Standardize Temperature Units to Farenheit (F)
    if TempUnits == "C":
        ## Change Units to F
        SkyTemp    = SkyTemp*9./5. + 32.
        AmbTemp    = AmbTemp*9./5. + 32.
        DewPoint   = DewPoint*9./5. + 32.
    elif TempUnits == "F":
        pass
    else:
        ClarityGood=False

    ## Standardize Wind Speed Units to Miles Per Hour (MPH)
    if WindUnits == "M":
        ## units are MPH
        pass
    elif WindUnits == "K":
        ## units are KPH
        WindSpeed = WindSpeed * 0.621
    elif WindUnits == "m":
        WindSpeed = WindSpeed * 2.237
    else:
        ClarityGood == False

    if ClarityGood:
        return [ClarityTime, SkyTemp, AmbTemp, WindSpeed, Humidity, DewPoint, CloudCondition, WindCondition, RainCondition, DayCondition, RoofClose]
    else:
        return None

##-------------------------------------------------------------------------
## Main Program
##-------------------------------------------------------------------------
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
    logger = logging.getLogger('GetEnvironment')
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
    LogFile = os.path.join(LogFilePath, 'GetEnvironment.log')
    LogFileHandler = logging.FileHandler(LogFile)
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)


    ##-------------------------------------------------------------------------
    ## Setup File to Recieve Data
    ##-------------------------------------------------------------------------
    logger.info('#### Starting GetEnvironment.py ####')
    DataFilePath = os.path.join("C:\\", "Data_"+telescope, "Logs", DateString)
    if not os.path.exists(DataFilePath):
        logger.debug('  Making directory: {}'.format(DataFilePath))
        os.mkdir(DataFilePath)
    DataFileName = "EnvironmentalLog.txt"
    DataFile = os.path.join(DataFilePath, DataFileName)
    logger.info('  Writing data to {}'.format(DataFile))


    ##-------------------------------------------------------------------------
    ## Query ASCOM ACPHub for Telescope Position and State
    ##-------------------------------------------------------------------------
#     logger.info('ACP Status:')
    ACP = None
    ACP_is_connected = None
#     try:
#         ACP = win32com.client.Dispatch("ACP.Telescope")
#         ACP_is_connected = ACP.Connected
#     except:
#         ACP = False
#         ACP_is_connected = False
    if ACP and ACP_is_connected:
        try:
            ACP_AtPark   = ACP.AtPark
            ACP_Altitude = float(ACP.Altitude)
            ACP_Azimuth  = float(ACP.Azimuth)
            ACP_Slewing  = ACP.Slewing
            ACP_Tracking = ACP.Tracking
        except:
            pass
        logger.info('  ACP Park Status = {}'.format(ACP_AtPark))
        logger.info('  ACP Altitude = {:.1f}'.format(ACP_Altitude))
        logger.info('  ACP Azimuth = {:.1f}'.format(ACP_Azimuth))
        logger.info('  ACP Slewing = {:.1f}'.format(ACP_Slewing))
        logger.info('  ACP Tracking = {:.1f}'.format(ACP_Tracking))
    else:
        ACP_AtPark   = None
        ACP_Altitude = float('nan')
        ACP_Azimuth  = float('nan')
        ACP_Slewing  = None
        ACP_Tracking = None
#         logger.info('  ACP is not connected.')



    ##-------------------------------------------------------------------------
    ## Query ASCOM Focuser for Position, Temperature, Fan State
    ##-------------------------------------------------------------------------
    if telescope == "V20":
        logger.info('RCOS TCC Data:')
        try:
            RCOST = win32com.client.Dispatch("RCOS_AE.Temperature")
            RCOSF = win32com.client.Dispatch("RCOS_AE.Focuser")
        except:
            RCOST = None
            RCOSF = None
        if RCOST and RCOSF:
            ## Get Average of 5 Temperature Readings
            RCOS_Truss_Temps = []
            RCOS_Primary_Temps = []
            RCOS_Secondary_Temps = []
            RCOS_Fan_Speeds = []
            RCOS_Focus_Positions = []
            logger.debug(' RCOS Data:  {:>7s}, {:>7s}, {:>7s}, {:>7s}, {:>5s}'.format('Truss', 'Pri', 'Sec', 'Fan', 'Foc'))
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
                    logger.debug('  RCOS Data:  {:5.1f} F, {:5.1f} F, {:5.1f} F, {:5.0f} %, {:5d}'.format(new_Truss_Temp, new_Pri_Temp, new_Sec_Temp, new_Fan_Speed, new_Focus_Pos))
                except:
                    pass
                time.sleep(1)
            if len(RCOS_Truss_Temps) >= 3:
                RCOS_Truss_Temp = float(np.median(RCOS_Truss_Temps))
            else:
                RCOS_Truss_Temp = float('nan')
            if len(RCOS_Primary_Temps) >= 3:
                RCOS_Primary_Temp = float(np.median(RCOS_Primary_Temps))
            else:
                RCOS_Primary_Temp = float('nan')
            if len(RCOS_Secondary_Temps) >= 3:
                RCOS_Secondary_Temp = float(np.median(RCOS_Secondary_Temps))
            else:
                RCOS_Secondary_Temp = float('nan')
            if len(RCOS_Fan_Speeds) >= 3:
                RCOS_Fan_Speed = int(np.median(RCOS_Fan_Speeds))
            else:
                RCOS_Fan_Speed = float('nan')
            if len(RCOS_Focus_Positions) >= 3:
                RCOS_Focus_Position = int(np.median(RCOS_Focus_Positions))
            else:
                RCOS_Focus_Position = float('nan')
            logger.info('  RCOS Truss Temperature = {:.1f}'.format(RCOS_Truss_Temp))
            logger.info('  RCOS Primary Temperature = {:.1f}'.format(RCOS_Primary_Temp))
            logger.info('  RCOS Secondary Temperature = {:.1f}'.format(RCOS_Secondary_Temp))
            logger.info('  RCOS Fan Speed = {:.0f}'.format(RCOS_Fan_Speed))
            logger.info('  RCOS Focus Position = {:.1f}'.format(RCOS_Focus_Position))
    if telescope == "V5":
        logger.info('FocusMax Data:')
        try:
            FocusMax = win32com.client.Dispatch("FocusMax.Focuser")
            if not FocusMax.Link:
                try:
                    FocusMax.Link = True
                except:
                    FocusMax = None
        except:
            FocusMax = None
        if FocusMax:
            ## Get Average of 3 Temperature Readings
            FocusMax_Temps = []
            for i in range(0,3,1):
                try:
                    newtemp = float(FocusMax.Temperature)*9./5. + 32.
                    FocusMax_Temps.append(newtemp)
                    logger.debug('  FocusMax Temperature {} = {:.1f}'.format(i, newtemp))
                except:
                    logger.debug('  Failed to get FocusMax Temperature')
            if len(FocusMax_Temps) > 0:
                FocusMax_Temp = np.median(FocusMax_Temps)
                ## Filter out bad values
                if (FocusMax_Temp > -10) and (FocusMax_Temp < 150):
                    pass
                else:
                    FocusMax_Temp = float('nan')
            else:
                FocusMax_Temp = float('nan')  #float(np.median(FocusMax_Temps))
            logger.info('  FocusMax Temperature = {:.1f}'.format(FocusMax_Temp))
            ## Get Position
            try:
                FocusMax_Pos = int(FocusMax.Position)
            except:
                FocusMax_Pos = -1
            logger.info('  FocusMax Position = {:d}'.format(FocusMax_Pos))
        else:
            FocusMax_Temp = float('nan')
            FocusMax_Pos = -1


    ##-------------------------------------------------------------------------
    ## Query Clarity Data File for Boltwood Stats
    ##-------------------------------------------------------------------------
    logger.info('Clarity Data:')
    ClarityDataFile = os.path.join("C:\\", "Users", "vysosuser", "Documents", "ClarityII", "ClarityData.txt")
    ClarityArray = GetClarity(ClarityDataFile, logger)
    if ClarityArray:
        logger.info('  Boltwood Sky Temp = {:.1f} F'.format(ClarityArray[1]))
        logger.info('  Boltwood Ambient Temp = {:.1f} F'.format(ClarityArray[2]))
        logger.info('  Boltwood Wind Speed = {:.1f} MPH'.format(ClarityArray[3]))
        logger.info('  Boltwood Humidity = {:.1f} %'.format(ClarityArray[4]))
        logger.info('  Boltwood Dew Point = {:.1f} F'.format(ClarityArray[5]))
        logger.info('  Boltwood Cloud Condition = {:d}'.format(ClarityArray[6]))
        logger.info('  Boltwood Wind Condition = {:d}'.format(ClarityArray[7]))
        logger.info('  Boltwood Rain Condition = {:d}'.format(ClarityArray[8]))
        logger.info('  Boltwood Day Condition = {:d}'.format(ClarityArray[9]))
        logger.info('  Boltwood Roof Close = {:d}'.format(ClarityArray[10]))
    else:
        logger.critical('  Could not read Clarity data file.')


    ##-------------------------------------------------------------------------
    ## Make Copies of Clarity Data for ATLAS
    ##-------------------------------------------------------------------------
    ## Make Copy of Clarity's daily log
    HSTnow = datetime.datetime.now()
    if HSTnow.hour == 8 and HSTnow.minute < 15:
        HSTyesterday = HSTnow - datetime.timedelta(1)
        yesterdays_log_file = os.path.join("C:\\", "Users", "vysosuser", "Documents", "ClarityII", HSTyesterday.strftime('%Y-%m-%d')+'.txt')
        yesterdays_log_copy = os.path.join("C:\\", "Data_"+telescope, "Logs", DateString, "ClarityLog_"+HSTyesterday.strftime('%Y%m%d')+'HST.txt')
        if not os.path.exists(yesterdays_log_copy):
            try:
                logger.debug('Copying yesterday\'s Clarity logs to Logs directory.')
                shutil.copy2(yesterdays_log_file, yesterdays_log_copy)
            except:
                logger.warning('  Could not copy Clarity logs.')
    ## Make copy of raw ClarityData.txt
    ClarityCopy = os.path.join("C:\\", "Data_"+telescope, "ClarityData_raw_"+telescope+".txt")
    try:
        logger.debug('Copying Clarity file to altair for serving to web.')
        shutil.copy2(ClarityDataFile, ClarityCopy)
    except:
        logger.warning('  Could not copy Clarity file.')
    ## Make Processed Data Line for Web
    logger.info("Writing Boltwood Data File for Web Access.")
    TimeString = now.strftime("%Y/%m/%d %H:%M:%SUT")
    OutputClarityDataFile = os.path.join("C:\\", "Data_"+telescope, "ClarityData_"+telescope+".txt")
    OutputClarityDataFO = open(OutputClarityDataFile, 'w')
    OutputClarityDataFO.write("# {:20s} {:9s} {:9s} {:9s} {:9s} {:9s} {:1s} {:1s} {:1s} {:1s} {:1s}\n".format("Date and Time", "SkyTemp", "AmbTemp", "WindSpd", "Humidity", "DewPoint", "C", "W", "R", "D", "R"))
    OutputClarityDataFO.write("{:22s} {:9.1f} {:9.1f} {:9.1f} {:9.1f} {:9.1f} {:1d} {:1d} {:1d} {:1d} {:1d}\n".format(TimeString,
                              ClarityArray[1], ClarityArray[2], ClarityArray[3], ClarityArray[4], ClarityArray[5],
                              ClarityArray[6], ClarityArray[7], ClarityArray[8], ClarityArray[9], ClarityArray[10]))
    OutputClarityDataFO.close()


    ##-------------------------------------------------------------------------
    ## Query ControlByWeb Temperature Module for Temperature and Fan State
    ##-------------------------------------------------------------------------
    if telescope == 'V20':
        logger.info('ControlByWeb Temperature Module:')
        IPaddress = "192.168.1.115"
        try:
            page = urllib.urlopen("http://"+IPaddress+"/state.xml")
            contents = page.read()
            ContentLines = contents.splitlines()
    
            xmldoc = minidom.parseString(contents)
            CBW_units = str(xmldoc.getElementsByTagName('units')[0].firstChild.nodeValue)
            CBW_temp1 = float(xmldoc.getElementsByTagName('sensor1temp')[0].firstChild.nodeValue)
            CBW_temp2 = float(xmldoc.getElementsByTagName('sensor2temp')[0].firstChild.nodeValue)
            CBW_fans = int(xmldoc.getElementsByTagName('relay1state')[0].firstChild.nodeValue)
            CBW_enable = int(xmldoc.getElementsByTagName('relay2state')[0].firstChild.nodeValue)
            if CBW_units == "C":
                CBW_temp1 = CBW_temp1*9./5. + 32.
                CBW_temp2 = CBW_temp2*9./5. + 32.
                CBW_units = 'F'
            logger.info('  ControlByWeb Temp 1 = {:.1f} {}'.format(CBW_temp1, CBW_units))
            logger.info('  ControlByWeb Temp 2 = {:.1f} {}'.format(CBW_temp2, CBW_units))
            logger.info('  ControlByWeb Relay 1 (Fans) = {:d}'.format(CBW_fans))
            logger.info('  ControlByWeb Relay 2 (Enable) = {:d}'.format(CBW_enable))
        except:
            logger.warning('Could not communicate with temperature module')
            CBW_units = None
            CBW_temp1 = float('nan')
            CBW_temp2 = float('nan')
            CBW_fans = -1
            CBW_enable = -1
        ## Set CBW Relay Status to Turn Fans On or Off
        ControlFans = True
        DeadbandHigh = 0.1
        DeadbandLow = 2.0
        logger.info('Setting dome fan state.')
        if CBW_enable and CBW_temp1 and ClarityArray and RCOST:
            InsideTemp = RCOS_Truss_Temp
            OutsideTemp = ClarityArray[2]
            logger.debug('  Inside Temp = {:.1f}'.format(InsideTemp))
            logger.debug('  Outside Temp = {:.1f}'.format(OutsideTemp))
            DeltaT = InsideTemp - OutsideTemp
            if CBW_enable == 0:
                if (CBW_fans == 1):
                    logger.debug("  Turning Dome Fan Off.  Remote Control Set to Off.  DeltaT = %.1f" % DeltaT)
                    page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
                elif (CBW_fans == 0):
                    logger.info("  Leaving Dome Fan Off.  Remote Control Set to Off.  DeltaT = %.1f" % DeltaT)
            else:
                ## Turn on Fans if Inside Temperature is High
                if ControlFans and (CBW_fans == 0) and (InsideTemp > OutsideTemp + DeadbandHigh):
                    logger.info("  Turning Dome Fan On.  DeltaT = %.1f" % DeltaT)
                    page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=1")
                ## Turn off Fans if Inside Temperature is Low
                elif ControlFans and (CBW_fans == 1) and (InsideTemp < OutsideTemp - DeadbandLow):
                    logger.info("  Turning Dome Fan Off.  DeltaT = %.1f" % DeltaT)
                    page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
                ## Turn off Fans if it is night
                elif not ControlFans and (RelayState == 1):
                    logger.info("  Turning Dome Fan Off for Night.  DeltaT = %.1f" % DeltaT)
                    page = urllib.urlopen("http://"+IPaddress+"/state.xml?relay1State=0")
                ## Turn off Fans if Inside Temperature is Low
                else:
                    if CBW_fans == 1:
                        logger.info("  Leaving Dome Fan On.  DeltaT = %.1f", DeltaT)
                    if CBW_fans == 0:
                        logger.info("  Leaving Dome Fan Off.  DeltaT = %.1f", DeltaT)



    ##-------------------------------------------------------------------------
    ## Update Data File With Results
    ##-------------------------------------------------------------------------
    logger.info('Writing results to: {}'.format(DataFile))
    if not os.path.exists(DataFile):
        if telescope == "V20":
            header_lines = ['{:<22s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}'.format( \
                            "#", "Tube", "Primary", "Sec.", "FanPwr", "Focus", "Sky", "Outside", "WindSpd", "Humid", "DewPt", "Alt", "Az", "Wetness", "Dome", "DomeFan", ), \
                            '{:<22s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}'.format( \
                            "# Date & Time UT", "(F)", "(F)", "(F)", "(%)", "Pos.", "(F)", "(F)", "(km/h)", "(%)", "(F)", "(deg)", "(deg)", "()", "(F)", "()")]
        if telescope == "V5":
            header_lines = ['{:<22s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}'.format( \
                            "#", "Tube", "Focus", "Sky", "Outside", "WindSpd", "Humid", "DewPt", "Alt", "Az", "WetCldWnd"), \
                            '{:<22s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}{:>10s}'.format( \
                            "# Date & Time UT", "(F)", "Pos.", "(F)", "(F)", "(km/h)", "(%)", "(F)", "(deg)", "(deg)", "()")]
        logger.debug('  Writing header lines to {}'.format(DataFile))
        output = open(DataFile, 'w')
        for line in header_lines:
            output.write(line+'\n')
        output.close()
    ## Write Data Line
    WetCldWnd = str(ClarityArray[8])+str(ClarityArray[6])+str(ClarityArray[7])
#     print(type(TimeString))
#     print(type(RCOS_Truss_Temp))
#     print(type(RCOS_Primary_Temp))
#     print(type(RCOS_Secondary_Temp))
#     print(type(RCOS_Fan_Speed))
#     print(type(RCOS_Focus_Position))
#     print(type(ClarityArray[1]))
#     print(type(ClarityArray[2]))
#     print(type(ClarityArray[3]))
#     print(type(ClarityArray[4]))
#     print(type(ClarityArray[5]))
#     print(type(ACP_Altitude))
#     print(type(ACP_Azimuth))
#     print(type(WetCldWnd))
#     print(type(CBW_temp1))
#     print(type(CBW_fans))
#     print(type(CBW_enable))
    if telescope == 'V20':
        data_line = '{:<22s}{:>10.2f}{:>10.2f}{:>10.2f}{:>10d}{:>10d}{:>10.2f}{:>10.2f}{:>10.1f}{:>10.0f}{:>10.2f}{:>10.2f}{:>10.2f}{:>10s}{:>10.1f}{:>9d}{:1d}'.format( \
                    TimeString, RCOS_Truss_Temp, RCOS_Primary_Temp, RCOS_Secondary_Temp, RCOS_Fan_Speed, RCOS_Focus_Position, \
                    ClarityArray[1], ClarityArray[2], ClarityArray[3], ClarityArray[4], ClarityArray[5], \
                    ACP_Altitude, ACP_Azimuth, WetCldWnd, CBW_temp1, CBW_fans, CBW_enable)
    if telescope == 'V5':
        data_line = '{:<22s}{:>10.2f}{:>10d}{:>10.2f}{:>10.2f}{:>10.1f}{:>10.0f}{:>10.2f}{:>10.2f}{:>10.2f}{:>10s}'.format( \
                     TimeString, FocusMax_Temp, FocusMax_Pos, \
                     ClarityArray[1], ClarityArray[2], ClarityArray[3], ClarityArray[4], ClarityArray[5], \
                     ACP_Altitude, ACP_Azimuth, WetCldWnd)
    logger.debug('  Data line: {}'.format(data_line))
    output = open(DataFile, 'a')
    output.write(data_line+'\n')
    output.close()

    ##-------------------------------------------------------------------------
    ## Write HTML snippet for inclusion on VYSOS Status web page
    ##-------------------------------------------------------------------------
    write_html_snippet(ClarityArray, ACP_is_connected, ACP_Tracking, ACP_Slewing, ACP_AtPark, ACP_Altitude, ACP_Azimuth, telescope, logger)

    logger.info('Done.')




if __name__ == '__main__':
    main()
