#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Josh Walawender on 2012-10-11.
Copyright (c) 2012 . All rights reserved.
"""

import sys
import os
from argparse import ArgumentParser
import re
import string
import fnmatch
import time
import datetime
import logging
import math
import numpy
import matplotlib.pyplot as pyplot

import ephem
from astropy.io import ascii
from astropy import table
import IQMon


def TimeStringToDecimal(TimeString):
    hms = string.split(TimeString, ":")
    DecimalTime = float(hms[0])+ float(hms[1])/60.0 + float(hms[2])/60.0/60.0
    return DecimalTime

def ConvertHSTtoUTString(TimeString):
    hmsHST = string.split(TimeString, ":")
    if int(hmsHST[0]) >= 14:
        UTString = str(int(hmsHST[0])+10-24)+":"+hmsHST[1]+":"+hmsHST[2]
    else:
        UTString = str(int(hmsHST[0])+10)+":"+hmsHST[1]+":"+hmsHST[2]
    return UTString


###########################################################
## Read ACP Logs
## - extract ACP FWHM and Pointing Error
##
## VYSOSDATAPath
## DateString
## FoundACPLog (should be output)
## ACPdata (output)
def ReadACPLog(DateString, VYSOSDATAPath, PixelScale, logger):
    MatchStartOfImage  = re.compile("(\d{2}:\d{2}:\d{2})\s*Imaging\sto\s([a-zA-Z0-9@\-_\+]*)")
    MatchPointingError = re.compile("(\d{2}:\d{2}:\d{2})\s*Pointing\serror\sis\s([0-9\.]+)\sarcmin.*")
    MatchImageFWHM     = re.compile("(\d{2}:\d{2}:\d{2})\s*Image\sFWHM\sis\s[0-9\.]{2,5}\sarcsec\s\(([0-9\.]{2,5})\spixels\)")
    MatchAvgFWHM       = re.compile("(\d{2}:\d{2}:\d{2})\s*\(avg\sFWHM\s=\s([0-9\.]{2,5})\sarcsec\)")
    MatchRunComplete   = re.compile("(\d{2}:\d{2}:\d{2})\s*Run\scomplete")
    ACPLogDirectory = os.path.join(VYSOSDATAPath, "Logs", DateString)
    if os.path.exists(ACPLogDirectory):
        logger.debug("Found ACP Log Directory: "+ACPLogDirectory)
        FoundACPLog = True
        colNames = ('TimeDecimal', 'ImageFile', 'TimeString', 'ImageFWHM', 'AvgFWHM', 'PointingError')
        colTypes = ('f4', 'S80', 'S8', 'f4', 'f4', 'f4')
        ACPdata = table.Table(names=colNames, dtypes=colTypes)
        ACPLogFiles = os.listdir(ACPLogDirectory)
        ## Loop through all log files
        for LogFile in ACPLogFiles:
            if fnmatch.fnmatch(LogFile,"*.log"):
                input = open(os.path.join(ACPLogDirectory, LogFile), 'r')
                ImageFile = ""
                ImageFWHM = float("NaN")
                AvgFWHM = float("NaN")
                TimeString = ""
                TimeDecimal = float("NaN")
                ACPPointingError = float("NaN")
                for line in input:
                    IsStartOfImage = MatchStartOfImage.match(line)
                    if IsStartOfImage:
                        if (ImageFile != "") and (not re.match(".*Empty.*", ImageFile)):
                            ACPdata.add_row((TimeDecimal, ImageFile, TimeString, ImageFWHM, AvgFWHM, ACPPointingError))
#                             ACPdata.append([TimeDecimal, ImageFile, TimeString, ImageFWHM, AvgFWHM, ACPPointingError])
                        ImageFile = IsStartOfImage.group(2)
                        TimeString = IsStartOfImage.group(1)
                        TimeDecimal = TimeStringToDecimal(TimeString)
                    IsPointingError = MatchPointingError.match(line)
                    if IsPointingError:
                        ACPPointingError = float(IsPointingError.group(2))
                    IsImageFWHM = MatchImageFWHM.match(line)
                    if IsImageFWHM:
                        ImageFWHM = float(IsImageFWHM.group(2))
                    IsAvgFWHM = MatchAvgFWHM.match(line)
                    if IsAvgFWHM:
                        AvgFWHM = float(IsAvgFWHM.group(2))/PixelScale
                    IsRunComplete = MatchRunComplete.match(line)
                    if IsRunComplete:
                        ACPdata.add_row((TimeDecimal, ImageFile, TimeString, ImageFWHM, AvgFWHM, ACPPointingError))
#                         ACPdata.append([TimeDecimal, ImageFile, TimeString, ImageFWHM, AvgFWHM, ACPPointingError])
                input.close()
        nACPImages = len(ACPdata)
        logger.info("Data for %d images (Empty filter images excluded) extracted from ACP Logs." % nACPImages)
    else:
        logger.warning("Failed to Find ACP Log Directory: "+ACPLogDirectory)
        ACPdata = None

    return ACPdata


###########################################################
## Read IQMon Logs
## - extract IQMon FWHM, ellipticity, pointing error
def ReadIQMonLog(config, telescope, DateString, logger):
    IQMonTable = None
    if telescope == "V5":
        telname = "VYSOS-5"
    if telescope == "V20":
        telname = "VYSOS-20"
    if os.path.exists(os.path.join(config.pathLog, telname)):
        FoundIQMonFile = True
        logger.debug("Found directory with IQMon summary files.")
        Files = os.listdir(os.path.join(config.pathLog, telname))
        if telescope == "V5":
            MatchIQMonFile = re.compile("([0-9]{8}UT)_V5_Summary\.txt")
        if telescope == "V20":
            MatchIQMonFile = re.compile("([0-9]{8}UT)_V20_Summary\.txt")
        for File in Files:
            IsIQMonFile = MatchIQMonFile.match(File)
            if IsIQMonFile:
                FullIQMonFile = os.path.join(config.pathLog, telname, File)
                IQMonFileDate = IsIQMonFile.group(1)
                if IQMonFileDate == DateString:
                    logger.debug("IQMon Summary file for "+DateString+" is "+File)
                    FoundIQMonFile = True
                    try:
                        IQMonTable = ascii.read(FullIQMonFile, fill_values=("--", float("nan")))
                        IQMonTimeDecimals = []
                        for i in range(0,len(IQMonTable),1):
                            IQMonTimeDecimals.append(TimeStringToDecimal(IQMonTable[i]['ExpStart'][11:19]))
                        IQMonTable.add_column(table.MaskedColumn(data=IQMonTimeDecimals, name='Time'))
                        logger.info("Data for %d images extracted from IQMon summary file." % len(IQMonTable))
                    except:
                        logger.critical("Failed to Read IQMon Log File")
                        IQMonTable = table.Table()
    if not IQMonTable:
        logger.critical("Failed to Find IQMon Logs: "+os.path.join(config.pathLog, telname))

    return IQMonTable


###########################################################
## Read Environmental Logs
def ReadEnvironmentalLogs(DateString, telescope, V5DataPath, V20DataPath, logger):
    logger.info("Reading Environmental Logs")
    V20EnvLogFileName = os.path.join(V20DataPath, "Logs", DateString, "EnvironmentalLog.txt")
    V5EnvLogFileName  = os.path.join(V5DataPath,  "Logs", DateString, "EnvironmentalLog.txt")
    FoundV20EnvLogFile = False
    FoundV5EnvLogFile  = False
    FoundOtherLogFile = False
    if os.path.exists(V20EnvLogFileName):
        logger.debug("Found VYSOS-20 Environmental Logs")
        FoundV20EnvLogFile = True
        ColStarts = [ 0, 11, 22, 32, 42, 52, 62, 72, 82,  92, 102, 112, 122, 132, 142, 152, 162]
        ColEnds   = [ 9, 18, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121, 131, 141, 151, 161, 171]
        ColNames  = ['Date', 'TimeString', 'TubeTemp', 'PrimaryTemp', 'SecTemp', 'FanPower', 'FocusPos',
                     'SkyTemp', 'OutsideTemp', 'WindSpeed', 'Humidity', 'DewPoint', 'Altitude', 'Azimuth',
                     'Condition', 'DomeTemp', 'DomeFanState']
        V20EnvTable = ascii.read(V20EnvLogFileName, data_start=2, Reader=ascii.FixedWidth,
                      col_starts=ColStarts, col_ends=ColEnds, names=ColNames,
                      guess=False, comment=";", header_start=0,
                      converters={
                      'Date': [ascii.convert_numpy('S10')],
                      'TimeString': [ascii.convert_numpy('S10')],
                      'TubeTemp': [ascii.convert_numpy('f4')],
                      'SecTemp': [ascii.convert_numpy('f4')],
                      'FanPower': [ascii.convert_numpy('f4')],
                      'FocusPos': [ascii.convert_numpy('i4')],
                      'SkyTemp': [ascii.convert_numpy('f4')],
                      'OutsideTemp': [ascii.convert_numpy('f4')],
                      'WindSpeed': [ascii.convert_numpy('f4')],
                      'Humidity': [ascii.convert_numpy('i4')],
                      'DewPoint': [ascii.convert_numpy('f4')],
                      'Altitude': [ascii.convert_numpy('f4')],
                      'Azimuth': [ascii.convert_numpy('f4')],
                      'Condition': [ascii.convert_numpy('i4')],
                      'DomeTemp': [ascii.convert_numpy('f4')],
                      'DomeFanState': [ascii.convert_numpy('i4')]
                      }
                      )
        V20SkyDiff   = V20EnvTable['SkyTemp'] #- V20EnvTable['OutsideTemp']
        V20EnvTable.add_column(table.Column(data=V20SkyDiff, name='SkyDiff'))
        V20DomeFan = []
        V20TimeDecimal = []
        V20Wetness = []
        V20Cloudiness = []
        V20Windiness = []
        for i in range(0,len(V20EnvTable),1):
            ## Make Time Decimal
            V20TimeDecimal.append(TimeStringToDecimal(V20EnvTable[i]['TimeString'][0:8]))
            ## Parse Condition String
            ConditionMatch = re.match("([0-3])([0-3])([0-3])", str(V20EnvTable[i]['Condition']))
            if ConditionMatch:
                V20Wetness.append(ConditionMatch.group(1))
                V20Cloudiness.append(ConditionMatch.group(2))
                V20Windiness.append(ConditionMatch.group(3))
            else:
                V20Wetness.append("-1")
                V20Cloudiness.append("-1")
                V20Windiness.append("-1")
            ## Filter Out Bad Sky Diff Values
            if V20EnvTable[i]['SkyTemp'] < -100.: V20EnvTable[i]['SkyTemp'] = float("nan")
            ## Parse Dome Fan State
            FanMatch = re.match(".*([0-1])([0-1]).*", str(V20EnvTable[i]['DomeFanState']))
            if FanMatch:
                V20DomeFan.append(float(FanMatch.group(1))*100)
            else:
                V20DomeFan.append(float(0))
        V20EnvTable.add_column(table.Column(data=V20TimeDecimal, name='Time'))
        V20EnvTable.add_column(table.Column(data=V20Wetness, name='WetCondition'))
        V20EnvTable.add_column(table.Column(data=V20Cloudiness, name='CloudCondition'))
        V20EnvTable.add_column(table.Column(data=V20Windiness, name='WindCondition'))
        V20EnvTable.add_column(table.Column(data=V20DomeFan, name='DomeFan'))
    else:
        ColNames  = ['Date', 'TimeString', 'TubeTemp', 'PrimaryTemp', 'SecTemp', 'FanPower', 'FocusPos',
                     'SkyTemp', 'OutsideTemp', 'WindSpeed', 'Humidity', 'DewPoint', 'Altitude', 'Azimuth', 'Condition', 'DomeTemp', 'DomeFanState']
        V20EnvTable = table.Table(names=ColNames)

    if os.path.exists(V5EnvLogFileName):
        logger.debug("Found VYSOS-5 Environmental Logs")
        FoundV5EnvLogFile = True
        ColStarts = [ 0, 11, 22, 32, 42, 52, 62, 72, 82,  92, 102, 112]
        ColEnds   = [ 9, 18, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121]
        ColNames  = ['Date', 'TimeString', 'TubeTemp', 'FocusPos', 
                     'SkyTemp', 'OutsideTemp', 'WindSpeed', 'Humidity', 'DewPoint', 'Altitude', 'Azimuth', 'Condition']
        V5EnvTable = ascii.read(V5EnvLogFileName, data_start=2, Reader=ascii.FixedWidth, 
                     col_starts=ColStarts, col_ends=ColEnds, names=ColNames, 
                     guess=False, comment=";", header_start=0,
                     converters={
                     'Date': [ascii.convert_numpy('S10')],
                     'TimeString': [ascii.convert_numpy('S10')],
                     'TubeTemp': [ascii.convert_numpy('f4')],
                     'FocusPos': [ascii.convert_numpy('i4')],
                     'SkyTemp': [ascii.convert_numpy('f4')],
                     'OutsideTemp': [ascii.convert_numpy('f4')],
                     'WindSpeed': [ascii.convert_numpy('f4')],
                     'Humidity': [ascii.convert_numpy('i4')],
                     'DewPoint': [ascii.convert_numpy('f4')],
                     'Altitude': [ascii.convert_numpy('f4')],
                     'Azimuth': [ascii.convert_numpy('f4')],
                     'Condition': [ascii.convert_numpy('i4')]
                     }
                     )
        V5SkyDiff   = V5EnvTable['SkyTemp'] - V5EnvTable['OutsideTemp']
        V5EnvTable.add_column(table.Column(data=V5SkyDiff, name='SkyDiff'))
        V5TimeDecimal = []
        V5Wetness = []
        V5Cloudiness = []
        V5Windiness = []
        for i in range(0,len(V5EnvTable),1):
            ## Make Time Decimal
            V5TimeDecimal.append(TimeStringToDecimal(V5EnvTable[i]['TimeString'][0:8]))
            ## Parse Condition String
            ConditionMatch = re.match("\s*([\-0-9])([\-0-9])([\-0-9])\s*", str(V5EnvTable[i]['Condition']))
            if ConditionMatch:
                V5Wetness.append(ConditionMatch.group(1))
                V5Cloudiness.append(ConditionMatch.group(2))
                V5Windiness.append(ConditionMatch.group(3))
            else:
                V5Wetness.append("-1")
                V5Cloudiness.append("-1")
                V5Windiness.append("-1")
            ## Filter Out Bad Sky Diff Values
            if V5EnvTable[i]['SkyTemp'] < -100.: V5EnvTable[i]['SkyTemp'] = float("nan")
        V5EnvTable.add_column(table.Column(data=V5TimeDecimal, name='Time'))
        V5EnvTable.add_column(table.Column(data=V5Wetness, name='WetCondition'))
        V5EnvTable.add_column(table.Column(data=V5Cloudiness, name='CloudCondition'))
        V5EnvTable.add_column(table.Column(data=V5Windiness, name='WindCondition'))
    else:
        ColNames  = ['Date', 'TimeString', 'TubeTemp', 'FocusPos', 
                     'SkyTemp', 'OutsideTemp', 'WindSpeed', 'Humidity', 'DewPoint', 'Altitude', 'Azimuth', 'Condition']
        V5EnvTable = table.Table(names=ColNames)

    return V20EnvTable, V5EnvTable


###########################################################
## Make Plots
def MakePlots(DateString, telescope, logger):
    logger.info("#### Making Nightly Plots for "+telescope+" on the Night of "+DateString+" ####")

    FoundACPLog       = False
    FoundIQMonFile    = False
    FoundFocusMaxFile = False
    FoundV20Env       = False
    FoundV5Env        = False
    pyplot.ioff()

    ##############################################################
    ## Read Configuration File to get the following items
    config = IQMon.Config()

    ##############################################################
    ## Set up pathnames and filenames
    V5DataPath = os.path.join("/Volumes", "Data_V5")
    V20DataPath = os.path.join("/Volumes", "Data_V20")
    if telescope == "V5":
        VYSOSDATAPath = V5DataPath
        PixelScale = 2.53
        telname = "VYSOS-5"
        OtherTelescope = "V20"
    if telescope == "V20":
        VYSOSDATAPath = V20DataPath
        PixelScale = 0.44
        telname = "VYSOS-20"
        OtherTelescope = "V5"

    ## Set File Name
    PlotFileName = DateString+"_"+telescope+".png"
    PlotFile = os.path.join(config.pathLog, telname, PlotFileName)
    EnvPlotFileName = DateString+"_"+telescope+"_Env.png"
    EnvPlotFile = os.path.join(config.pathLog, telname, EnvPlotFileName)
    RecentPlotFileName = "Recent_"+telname+"_Conditions.png"
    RecentPlotFile = os.path.join(config.pathLog, telname, RecentPlotFileName)

    ## Compile Various Regular Expressions for File Name Matching and ACP Log Parsing
    MatchDir = re.compile(DateString)

    ##############################################################
    ## Use pyephem determine sunrise and sunset times
    Observatory = ephem.Observer()
    Observatory.lon = "-155:34:33.9"
    Observatory.lat = "+19:32:09.66"
    Observatory.elevation = 3400.0
    Observatory.temp = 10.0
    Observatory.pressure = 680.0
    Observatory.date = DateString[0:4]+"/"+DateString[4:6]+"/"+DateString[6:8]+" 10:00:00.0"

    Observatory.horizon = '0.0'
    SunsetTime  = Observatory.previous_setting(ephem.Sun()).datetime()
    SunriseTime = Observatory.next_rising(ephem.Sun()).datetime()
    SunsetDecimal = float(datetime.datetime.strftime(SunsetTime, "%H"))+float(datetime.datetime.strftime(SunsetTime, "%M"))/60.+float(datetime.datetime.strftime(SunsetTime, "%S"))/3600.
    SunriseDecimal = float(datetime.datetime.strftime(SunriseTime, "%H"))+float(datetime.datetime.strftime(SunriseTime, "%M"))/60.+float(datetime.datetime.strftime(SunriseTime, "%S"))/3600.
    Observatory.horizon = '-6.0'
    EveningCivilTwilightTime = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    MorningCivilTwilightTime = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
    EveningCivilTwilightDecimal = float(datetime.datetime.strftime(EveningCivilTwilightTime, "%H"))+float(datetime.datetime.strftime(EveningCivilTwilightTime, "%M"))/60.+float(datetime.datetime.strftime(EveningCivilTwilightTime, "%S"))/3600.
    MorningCivilTwilightDecimal = float(datetime.datetime.strftime(MorningCivilTwilightTime, "%H"))+float(datetime.datetime.strftime(MorningCivilTwilightTime, "%M"))/60.+float(datetime.datetime.strftime(MorningCivilTwilightTime, "%S"))/3600.
    Observatory.horizon = '-12.0'
    EveningNauticalTwilightTime = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    MorningNauticalTwilightTime = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
    EveningNauticalTwilightDecimal = float(datetime.datetime.strftime(EveningNauticalTwilightTime, "%H"))+float(datetime.datetime.strftime(EveningNauticalTwilightTime, "%M"))/60.+float(datetime.datetime.strftime(EveningNauticalTwilightTime, "%S"))/3600.
    MorningNauticalTwilightDecimal = float(datetime.datetime.strftime(MorningNauticalTwilightTime, "%H"))+float(datetime.datetime.strftime(MorningNauticalTwilightTime, "%M"))/60.+float(datetime.datetime.strftime(MorningNauticalTwilightTime, "%S"))/3600.
    Observatory.horizon = '-18.0'
    EveningAstronomicalTwilightTime = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    MorningAstronomicalTwilightTime = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
    EveningAstronomicalTwilightDecimal = float(datetime.datetime.strftime(EveningAstronomicalTwilightTime, "%H"))+float(datetime.datetime.strftime(EveningAstronomicalTwilightTime, "%M"))/60.+float(datetime.datetime.strftime(EveningAstronomicalTwilightTime, "%S"))/3600.
    MorningAstronomicalTwilightDecimal = float(datetime.datetime.strftime(MorningAstronomicalTwilightTime, "%H"))+float(datetime.datetime.strftime(MorningAstronomicalTwilightTime, "%M"))/60.+float(datetime.datetime.strftime(MorningAstronomicalTwilightTime, "%S"))/3600.

    Observatory.date = DateString[0:4]+"/"+DateString[4:6]+"/"+DateString[6:8]+" 0:00:01.0"
    TheMoon = ephem.Moon()
    TheMoon.compute(Observatory)
    MoonsetTime  = Observatory.next_setting(ephem.Moon()).datetime()
    MoonriseTime = Observatory.next_rising(ephem.Moon()).datetime()
    MoonsetDecimal = float(datetime.datetime.strftime(MoonsetTime, "%H"))+float(datetime.datetime.strftime(MoonsetTime, "%M"))/60.+float(datetime.datetime.strftime(MoonsetTime, "%S"))/3600.
    MoonriseDecimal = float(datetime.datetime.strftime(MoonriseTime, "%H"))+float(datetime.datetime.strftime(MoonriseTime, "%M"))/60.+float(datetime.datetime.strftime(MoonriseTime, "%S"))/3600.        

    MoonTimes = numpy.arange(0,24,0.1)
    MoonAlts = []
    for MoonTime in MoonTimes:
        TimeString = "%02d:%02d:%04.1f" % (math.floor(MoonTime), math.floor((MoonTime % 1)*60), ((MoonTime % 1 * 60) % 1)*60.0)
        Observatory.date = DateString[0:4]+"/"+DateString[4:6]+"/"+DateString[6:8]+" "+TimeString
        TheMoon.compute(Observatory)
        MoonAlts.append(TheMoon.alt * 180. / ephem.pi)
    MoonAlts = numpy.array(MoonAlts)
    
    MoonPeakAlt = max(MoonAlts)
    MoonPeakTime = (MoonTimes[(MoonAlts == MoonPeakAlt)])[0]
    MoonPeakTimeString = "%02d:%02d:%04.1f" % (math.floor(MoonPeakTime), math.floor((MoonPeakTime % 1)*60), ((MoonPeakTime % 1 * 60) % 1)*60.0)
    Observatory.date = DateString[0:4]+"/"+DateString[4:6]+"/"+DateString[6:8]+" "+MoonPeakTimeString
    TheMoon.compute(Observatory)
    MoonPhase = TheMoon.phase

    MoonFill = MoonPhase/100.*0.5+0.05

    now = datetime.datetime.utcnow()
    DecimalTime = now.hour+now.minute/60.+now.second/3600.

    ###########################################################
    ## Read ACP Logs
    ACPdata = ReadACPLog(DateString, VYSOSDATAPath, PixelScale, logger)
    if len(ACPdata) > 1: FoundACPLog = True

    ###########################################################
    ## Read IQMon Logs
    ## - extract IQMon FWHM, ellipticity, pointing error
    IQMonTable = ReadIQMonLog(config, telescope, DateString, logger)
    if IQMonTable and len(IQMonTable) > 1: FoundIQMonFile = True

    ###########################################################
    ## Get Environmental Data
    V20EnvTable, V5EnvTable = ReadEnvironmentalLogs(DateString, telescope, V5DataPath, V20DataPath, logger)
    if len(V20EnvTable) > 1: FoundV20Env = True
    if len(V5EnvTable) > 1:  FoundV5Env = True

    ###########################################################
    ## Match up ACP Log and IQMon Results Based on filename
    if FoundIQMonFile and FoundACPLog:
        logger.info("Matching IQMon and ACP data with {0} and {1} lines respectively".format(len(IQMonTable), len(ACPdata)))
        MatchedData = table.Table(
                      names=('ACP Time', 'ACP File', 'ACP FWHM', 'ACP PErr', 'IQMon Time', 'IQMon File', 'IQMon FWHM', 'IQMon PErr'),
                      dtypes=('f',       'S',        'f',        'f',        'S',           'S',         'f',          'f'),
                      masked=True
                      )
        for ACPentry in ACPdata:
            FindID = re.compile(".*(\d{8}at\d{6}).*")
            FindACPID = FindID.match(ACPentry['ImageFile'])
            if FindACPID:
                ACPID = FindACPID.group(1)
            else:
                logger.warning("Could not find ID for ACP file: {0}".format(ACPentry['ImageFile']))
            FoundIQMonMatch = False
            for IQMonEntry in IQMonTable:
                FindIQMonID = FindID.match(IQMonEntry['File'])
                if FindIQMonID:
                    IQMonID = FindIQMonID.group(1)
                else:
                    logger.warning("Could not find ID for IQMon file: {0}".format(IQMonEntry['File']))
                if IQMonID == ACPID:
                    logger.debug("{0} in IQMon results matched to {1} in ACP results.".format(IQMonEntry['File'], ACPentry['ImageFile']))
                    FoundIQMonMatch = True
                    MatchedData.add_row([ACPentry['TimeDecimal'], ACPentry['ImageFile'], ACPentry['ImageFWHM'], ACPentry['PointingError'],
                                         IQMonEntry['ExpStart'], IQMonEntry['File'], IQMonEntry['FWHM (pix)'], IQMonEntry['PointingError (arcmin)']])
                    break
            if not FoundIQMonMatch:
                ACPFile = os.path.join(VYSOSDATAPath, "Images", DateString, ACPentry['ImageFile']+".fts")
                if os.path.exists(ACPFile):
                    logger.warning("Could not find IQMon results for "+ACPentry['ImageFile']+".fts.")
                else:
                    logger.warning("Could not find IQMon result or file for ACP log entry "+ACPentry['ImageFile']+".fts.")
        logger.info("Matched {} images between ACP logs and IQMon results.".format(len(MatchedData)))


    ###########################################################
    ## Make Nightly Sumamry Plot (show only night time)
    ###########################################################
    now = time.gmtime()
    NowString = time.strftime("%Y%m%dUT", now)

    if (DateString != NowString) or (DecimalTime > SunsetDecimal):
        PlotStartUT = math.floor(SunsetDecimal)
        PlotEndUT = math.ceil(SunriseDecimal)
        nUTHours = PlotEndUT-PlotStartUT+1
        time_ticks_values = numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True)
        
        if telescope == "V20":
            plot_positions = [ ( [0.000, 0.765, 0.460, 0.235], [0.540, 0.765, 0.460, 0.235] ),
                               ( [0.000, 0.675, 0.460, 0.070], [0.540, 0.510, 0.460, 0.235] ),
                               ( [0.000, 0.430, 0.460, 0.235], [0.540, 0.420, 0.460, 0.070] ),
                               ( [0.000, 0.255, 0.460, 0.155], [0.540, 0.255, 0.460, 0.155] ),
                               ( [0.000, 0.000, 0.460, 0.235], [0.540, 0.000, 0.460, 0.235] ) ]
        if telescope == "V5":
            plot_positions = [ ( [0.000, 0.765, 0.460, 0.235], [0.540, 0.765, 0.460, 0.235] ),
                               ( [0.000, 0.000, 0.000, 0.000], [0.540, 0.510, 0.460, 0.235] ),
                               ( [0.000, 0.510, 0.460, 0.235], [0.000, 0.000, 0.000, 0.000] ),
                               ( [0.000, 0.255, 0.460, 0.235], [0.540, 0.255, 0.460, 0.235] ),
                               ( [0.000, 0.000, 0.460, 0.235], [0.540, 0.000, 0.460, 0.235] ) ]
        logger.info("Writing Output File: "+PlotFileName)
        dpi=100
        Figure = pyplot.figure(figsize=(13,9.5), dpi=dpi)

        ###########################################################
        ## Temperatures
        if FoundV20Env or FoundV5Env:
            TemperatureAxes = pyplot.axes(plot_positions[0][0])
            pyplot.title("Environmental Data for "+telescope + " on the Night of " + DateString)

            if telescope == "V20" and FoundV20Env:
                logger.debug("Found {} lines in VYSOS-20 Environment Log.".format(len(V20EnvTable)))
                if FoundV5Env:
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['OutsideTemp'], 'ko-', alpha=0.2, \
                                markersize=2, markeredgewidth=0, drawstyle="default", \
                                label="Outside Temp ("+OtherTelescope+")")
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['TubeTemp'], 'go-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Tube Temp")
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['OutsideTemp'], 'ko-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Outside Temp ("+telescope+")")
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['PrimaryTemp'], 'ro-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Mirror Temp")
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['DomeTemp'], 'co-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Dome Temp")

            if telescope == "V5" and FoundV5Env:
                logger.debug("Found {} lines in VYSOS-5 Environment Log.".format(len(V5EnvTable)))
                if FoundV20Env:
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['OutsideTemp'], 'ko-', alpha=0.2, \
                                markersize=2, markeredgewidth=0, drawstyle="default", \
                                label="Outside Temp ("+OtherTelescope+")")
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['TubeTemp'], 'go-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Tube Temp")
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['OutsideTemp'], 'ko-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Outside Temp ("+telescope+")")

            pyplot.legend(loc='best', prop={'size':10})
            pyplot.ylabel("Temperature (F)")
            pyplot.xticks(time_ticks_values)
            
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.grid()

            ## Overplot Twilights
            pyplot.axvspan(SunsetDecimal, EveningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)
            pyplot.axvspan(EveningCivilTwilightDecimal, EveningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
            pyplot.axvspan(EveningNauticalTwilightDecimal, EveningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
            pyplot.axvspan(EveningAstronomicalTwilightDecimal, MorningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.5)
            pyplot.axvspan(MorningAstronomicalTwilightDecimal, MorningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
            pyplot.axvspan(MorningNauticalTwilightDecimal, MorningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
            pyplot.axvspan(MorningCivilTwilightDecimal, SunriseDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)

            ## Overplot Moon Up Time
            MoonAxes = TemperatureAxes.twinx()
            MoonAxes.set_ylabel('Moon Alt (%.0f%% full)' % MoonPhase, color='y')
            pyplot.plot(MoonTimes, MoonAlts, 'y-')
            pyplot.ylim(0,100)
            pyplot.yticks([10,30,50,70,90], color='y')
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.fill_between(MoonTimes, 0, MoonAlts, where=MoonAlts>0, color='yellow', alpha=MoonFill)

            ## Add Fan Power (if VYSOS-20)
            if telescope == "V20" and FoundV20Env:
                Figure.add_axes(plot_positions[1][0], xticklabels=[])
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['DomeFan'], 'co-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Dome Fan")
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['FanPower'], 'bo-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Mirror Fans")
                pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
                pyplot.xlim(PlotStartUT,PlotEndUT)
                pyplot.ylim(-10,110)
                pyplot.yticks(numpy.linspace(0,100,3,endpoint=True))
                pyplot.ylabel('Fan (%)')
                pyplot.grid()

        ###########################################################
        ## Sky Condition (Cloudiness)
        if FoundV20Env or FoundV5Env:
            Figure.add_axes(plot_positions[2][0], xticklabels=[])
            if telescope == "V20" and FoundV20Env:
                if FoundV5Env:
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['SkyTemp'], 'ko-', alpha=0.2, \
                                markersize=2, markeredgewidth=0, drawstyle="default", \
                                label="Cloudiness ("+OtherTelescope+")")
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['SkyTemp'], 'bo-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Cloudiness ("+telescope+")")
                pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="1"), color='green', alpha=0.5)
                pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="2"), color='yellow', alpha=0.8)
                pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="3"), color='red', alpha=0.8)
            if telescope == "V5" and FoundV5Env:
                if FoundV20Env:
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['SkyTemp'], 'ko-', alpha=0.2, \
                                markersize=2, markeredgewidth=0, drawstyle="default", \
                                label="Cloudiness ("+OtherTelescope+")")
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['SkyTemp'], 'bo-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Cloudiness ("+telescope+")")
                pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="1"), color='green', alpha=0.5)
                pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="2"), color='yellow', alpha=0.8)
                pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="3"), color='red', alpha=0.8)
            pyplot.ylabel("Cloudiness (F)")
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.ylim(-100,-20)
            pyplot.grid()

        ###########################################################
        ## Humidity
        if FoundV20Env or FoundV5Env:
            Figure.add_axes(plot_positions[3][0], xticklabels=[])
            if telescope == "V5" and FoundV5Env:
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['Humidity'], 'bo-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Humidity ("+telescope+")")
                if FoundV20Env:
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['Humidity'], 'ko-', alpha=0.2, \
                                markersize=2, markeredgewidth=0, drawstyle="default", \
                                label="Humidity ("+OtherTelescope+")")
                pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="1"), color='green', alpha=0.5)
                pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="2"), color='red', alpha=0.5)
                pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="3"), color='red', alpha=0.8)            
            if telescope == "V20" and FoundV20Env:
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['Humidity'], 'bo-', 
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Humidity ("+telescope+")")
                if FoundV5Env:
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['Humidity'], 'ko-', alpha=0.2, \
                                markersize=2, markeredgewidth=0, drawstyle="default", \
                                label="Humidity ("+OtherTelescope+")")
                pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="1"), color='green', alpha=0.5)
                pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="2"), color='red', alpha=0.5)
                pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="3"), color='red', alpha=0.8)
            pyplot.ylabel("Humidity (%)")
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.ylim(-5,105)
            pyplot.grid()

        ###########################################################
        ## Wind Speed
        if FoundV20Env or FoundV5Env:
            Figure.add_axes(plot_positions[4][0])
            if telescope == "V20" and FoundV20Env:
                if FoundV5Env:
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['WindSpeed'], 'ko-', alpha=0.2, \
                                markersize=2, markeredgewidth=0, drawstyle="default", \
                                label="Wind Speed ("+OtherTelescope+")")
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['WindSpeed'], 'bo-', \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Wind Speed ("+telescope+")")
                pyplot.ylim(0,max([max(V20EnvTable['WindSpeed'])*1.1,35.]))
                pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="1"), color='green', alpha=0.5)
                pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="2"), color='yellow', alpha=0.8)
                pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="3"), color='red', alpha=0.8)
            if telescope == "V5" and FoundV5Env:
                if FoundV20Env:
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['WindSpeed'], 'ko-', alpha=0.2, \
                                markersize=2, markeredgewidth=0, drawstyle="default", \
                                label="Wind Speed ("+OtherTelescope+")")
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['WindSpeed'], 'b-', label="Wind Speed ("+telescope+")")
                pyplot.ylim(0,max([max(V5EnvTable['WindSpeed'])*1.1,35.]))
                pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="1"), color='green', alpha=0.5)
                pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="2"), color='yellow', alpha=0.8)
                pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="3"), color='red', alpha=0.8)
            pyplot.ylabel("Wind Speed (mph)")
            pyplot.xlabel("Time in Hours UT")
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.grid()

        ###########################################################
        ## FWHM vs. Time
        if FoundIQMonFile:
            Figure.add_axes(plot_positions[0][1])
            pyplot.title("IQ Mon Results for "+telescope + " on the Night of " + DateString)
            if telescope == "V20":
                pyplot.plot(MatchedData['ACP Time'], MatchedData['IQMon FWHM']*PixelScale, 'k.', drawstyle="steps-post", label="FWHM (IQMon)")
                pyplot.ylabel("FWHM (arcsec)")
            if telescope == "V5":
                pyplot.plot(MatchedData['ACP Time'], MatchedData['IQMon FWHM'], 'k.', drawstyle="steps-post", label="FWHM (IQMon)")
                pyplot.ylabel("FWHM (pixels)")
            pyplot.yticks(numpy.linspace(0,15,16,endpoint=True))
            pyplot.ylim(0,5)
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.grid()
            if FoundFocusMaxFile:
                for FocusRun in FocusRuns:
                    pyplot.axvspan(FocusRun[2], FocusRun[3], color="gray", alpha=0.7)

            ## Overplot Twilights
            pyplot.axvspan(SunsetDecimal, EveningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)
            pyplot.axvspan(EveningCivilTwilightDecimal, EveningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
            pyplot.axvspan(EveningNauticalTwilightDecimal, EveningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
            pyplot.axvspan(EveningAstronomicalTwilightDecimal, MorningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.5)
            pyplot.axvspan(MorningAstronomicalTwilightDecimal, MorningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
            pyplot.axvspan(MorningNauticalTwilightDecimal, MorningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
            pyplot.axvspan(MorningCivilTwilightDecimal, SunriseDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)


        ###########################################################
        ## Focus Position (if VYSOS-5) or Temperature Differences (if VYSOS-20)
        Figure.add_axes(plot_positions[1][1], xticklabels=[])
        if (telescope == "V5" and FoundV5Env and FoundIQMonFile):
            pyplot.plot(V5EnvTable['Time'], V5EnvTable['FocusPos'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Focus Position")
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            ## Clip the extreme values off of the focus position list (bad values?)
            nFocusPos = len(V5EnvTable['FocusPos'])
            ClippingFactor = 0.02
            nClipped = int(nFocusPos*ClippingFactor)
            ylimlower = (sorted(V5EnvTable['FocusPos']))[nClipped]
            ylimupper = (sorted(V5EnvTable['FocusPos']))[nFocusPos-nClipped]
            ylimrange = max([100 , ylimupper - ylimlower])
            pyplot.ylim(ylimlower-0.15*ylimrange, ylimupper+0.15*ylimrange)
            pyplot.ylabel("Focus Position (steps)")
            pyplot.legend(loc='best', prop={'size':10})
            pyplot.grid()
        if (telescope == "V20" and FoundV20Env):
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['TubeTemp']-V20EnvTable['OutsideTemp'], 'go-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Tube Temp")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['PrimaryTemp']-V20EnvTable['OutsideTemp'], 'ro-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Mirror Temp")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['DomeTemp']-V20EnvTable['OutsideTemp'], 'co-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Dome Temp")
            pyplot.plot([PlotStartUT,PlotEndUT], [0,0], 'k-')
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.ylim(-2.25,4.5)
            pyplot.ylabel("Temperature Difference (F)")
            pyplot.legend(loc='best', prop={'size':10})
            pyplot.grid()

            ## Add Fan Power (if VYSOS-20)
            Figure.add_axes(plot_positions[2][1], xticklabels=[])
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['DomeFan'], 'co-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Dome Fan")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['FanPower'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Mirror Fans")
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.ylim(-10,110)
            pyplot.yticks(numpy.linspace(0,100,3,endpoint=True))
            pyplot.ylabel('Fan (%)')
            pyplot.grid()


        ###########################################################
        ## Ellipticity vs. Time
        if FoundIQMonFile:
            Figure.add_axes(plot_positions[3][1], xticklabels=[])
            pyplot.plot(IQMonTable['Time'], IQMonTable['Ellipticity'], 'b.', drawstyle="steps-post", label="Ellipticity")
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.ylabel("Ellipticity")
            pyplot.ylim(0,1)
            pyplot.grid()


        ###########################################################
        ## Pointing Error vs. Time
        if FoundIQMonFile:
            Figure.add_axes(plot_positions[4][1])
            pyplot.plot(MatchedData['ACP Time'], MatchedData['IQMon PErr'], 'b.', drawstyle="steps-post", label="IQMon")
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.ylabel("Pointing Error (arcmin)")
            if telescope == "V5": PErrPlotMax = 10
            if telescope == "V20": PErrPlotMax = 4
            pyplot.ylim(0,PErrPlotMax)
            pyplot.grid()

        pyplot.savefig(PlotFile, dpi=dpi, bbox_inches='tight', pad_inches=0.10)


    ###########################################################
    ## Make Environmental Plot (show entire day)
    ###########################################################
    logger.info("Writing Output File: "+EnvPlotFileName)
    dpi=100
    Figure = pyplot.figure(figsize=(13,9.5), dpi=dpi)
    PlotStartUT = 0
    PlotEndUT = 24
    nUTHours = 25
    
    ###########################################################
    ## Temperatures
    if FoundV20Env or FoundV5Env:
        TemperatureAxes = pyplot.axes([0.0, 0.765, 1.0, 0.235])
        pyplot.title("Environmental Data for "+telescope + " on the Night of " + DateString)

        if telescope == "V20" and FoundV20Env:
            if FoundV5Env:
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['OutsideTemp'], 'ko-', alpha=0.2, \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Outside Temp ("+OtherTelescope+")")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['TubeTemp'], 'go-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Tube Temp")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['OutsideTemp'], 'ko-', 
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Outside Temp ("+telescope+")")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['PrimaryTemp'], 'ro-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Mirror Temp")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['DomeTemp'], 'co-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Dome Temp")

        if telescope == "V5" and FoundV5Env:
            if FoundV20Env:
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['OutsideTemp'], 'ko-', alpha=0.2, \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Outside Temp ("+OtherTelescope+")")
            pyplot.plot(V5EnvTable['Time'], V5EnvTable['TubeTemp'], 'go-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Tube Temp")
            pyplot.plot(V5EnvTable['Time'], V5EnvTable['OutsideTemp'], 'ko-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Outside Temp ("+telescope+")")

        pyplot.legend(loc='best', prop={'size':10})
        pyplot.ylabel("Temperature (F)")
        pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
        pyplot.xlim(PlotStartUT,PlotEndUT)
        pyplot.grid()

        ## Overplot Twilights
        pyplot.axvspan(SunsetDecimal, EveningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)
        pyplot.axvspan(EveningCivilTwilightDecimal, EveningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
        pyplot.axvspan(EveningNauticalTwilightDecimal, EveningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
        pyplot.axvspan(EveningAstronomicalTwilightDecimal, MorningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.5)
        pyplot.axvspan(MorningAstronomicalTwilightDecimal, MorningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
        pyplot.axvspan(MorningNauticalTwilightDecimal, MorningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
        pyplot.axvspan(MorningCivilTwilightDecimal, SunriseDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)

        ## Overplot Moon Up Time
        MoonAxes = TemperatureAxes.twinx()
        MoonAxes.set_ylabel('Moon Alt (%.0f%% full)' % MoonPhase, color='y')
        pyplot.plot(MoonTimes, MoonAlts, 'y-')
        pyplot.ylim(0,100)
        pyplot.yticks([10,30,50,70,90], color='y')
        pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
        pyplot.xlim(PlotStartUT,PlotEndUT)
        pyplot.fill_between(MoonTimes, 0, MoonAlts, where=MoonAlts>0, color='yellow', alpha=MoonFill)        

        ## Add Fan Power (if VYSOS-20)
        if telescope == "V20" and FoundV20Env:
            Figure.add_axes([0.0, 0.675, 1.0, 0.07], xticklabels=[])
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['DomeFan'], 'co-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Dome Fan State")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['FanPower'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Mirror Fans (%)")
            
            pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
            pyplot.xlim(PlotStartUT,PlotEndUT)
            pyplot.ylim(-10,110)
            pyplot.yticks(numpy.linspace(0,100,3,endpoint=True))
            pyplot.legend(loc='best', prop={'size':10})
            pyplot.grid()


    ###########################################################
    ## Sky Condition (Cloudiness)
    if FoundV20Env or FoundV5Env:
        # Figure.add_axes([0.0, 0.255, 1.0, 0.235])
        if telescope == "V20" and FoundV20Env:
            Figure.add_axes([0.0, 0.430, 1.0, 0.235])
            if FoundV5Env:
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['SkyTemp'], 'ko-', alpha=0.2, \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Cloudiness ("+OtherTelescope+")")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['SkyTemp'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Cloudiness ("+telescope+")")
            pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="1"), color='green', alpha=0.5)
            pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="2"), color='yellow', alpha=0.8)
            pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="3"), color='red', alpha=0.8)
        if telescope == "V5" and FoundV5Env:
            Figure.add_axes([0.0, 0.510, 1.0, 0.235])
            if FoundV20Env:
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['SkyTemp'], 'ko-', alpha=0.2, \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Cloudiness ("+OtherTelescope+")")
            pyplot.plot(V5EnvTable['Time'], V5EnvTable['SkyTemp'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Cloudiness ("+telescope+")")
            pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="1"), color='green', alpha=0.5)
            pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="2"), color='yellow', alpha=0.8)
            pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="3"), color='red', alpha=0.8)

        pyplot.legend(loc='best', prop={'size':10})
        pyplot.ylabel("Cloudiness (Delta T) (F)")
        pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
        pyplot.xlim(PlotStartUT,PlotEndUT)
        pyplot.ylim(-100,-20)
        pyplot.grid()

    ###########################################################
    ## Humidity
    if FoundV20Env or FoundV5Env:
        if telescope == "V5" and FoundV5Env:
            # Figure.add_axes([0.0, 0.510, 1.0, 0.235])
            Figure.add_axes([0.0, 0.255, 1.0, 0.235])
            if FoundV20Env:
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['Humidity'], 'ko-', alpha=0.2, \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Humidity ("+OtherTelescope+")")
            pyplot.plot(V5EnvTable['Time'], V5EnvTable['Humidity'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Humidity ("+telescope+")")
            pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="1"), color='green', alpha=0.5)
            pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="2"), color='red', alpha=0.5)
            pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="3"), color='red', alpha=0.8)            
        if telescope == "V20" and FoundV20Env:
            # Figure.add_axes([0.0, 0.510, 1.0, 0.155])
            Figure.add_axes([0.0, 0.255, 1.0, 0.155])
            if FoundV5Env:
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['Humidity'], 'ko-', alpha=0.2, \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Humidity ("+OtherTelescope+")")            
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['Humidity'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Humidity ("+telescope+")")
            pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="1"), color='green', alpha=0.5)
            pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="2"), color='red', alpha=0.5)
            pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="3"), color='red', alpha=0.8)            
        pyplot.legend(loc='best', prop={'size':10})
        pyplot.ylabel("Humidity (%)")
        pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
        pyplot.xlim(PlotStartUT,PlotEndUT)
        pyplot.ylim(-5,105)
        pyplot.grid()

    ###########################################################
    ## Wind Speed
    if FoundV20Env or FoundV5Env:
        Figure.add_axes([0.0, 0.000, 1.0, 0.235])
        if telescope == "V20" and FoundV20Env:
            if FoundV5Env:
                pyplot.plot(V5EnvTable['Time'], V5EnvTable['WindSpeed'], 'ko-', alpha=0.2, \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Wind Speed ("+OtherTelescope+")")
            pyplot.plot(V20EnvTable['Time'], V20EnvTable['WindSpeed'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Wind Speed ("+telescope+")")
            pyplot.ylim(0,max([max(V20EnvTable['WindSpeed'])*1.1,35.]))
            pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="1"), color='green', alpha=0.5)
            pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="2"), color='yellow', alpha=0.8)
            pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="3"), color='red', alpha=0.8)
        if telescope == "V5" and FoundV5Env:
            if FoundV20Env:
                pyplot.plot(V20EnvTable['Time'], V20EnvTable['WindSpeed'], 'ko-', alpha=0.2, \
                            markersize=2, markeredgewidth=0, drawstyle="default", \
                            label="Wind Speed ("+OtherTelescope+")")
            pyplot.plot(V5EnvTable['Time'], V5EnvTable['WindSpeed'], 'bo-', \
                        markersize=2, markeredgewidth=0, drawstyle="default", \
                        label="Wind Speed ("+telescope+")")
            pyplot.ylim(0,max([max(V5EnvTable['WindSpeed'])*1.1,35.]))
            pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="1"), color='green', alpha=0.5)
            pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="2"), color='yellow', alpha=0.8)
            pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="3"), color='red', alpha=0.8)

        pyplot.legend(loc='best', prop={'size':10})
        pyplot.ylabel("Wind Speed (mph)")
        pyplot.xlabel("Time in Hours UT")
        pyplot.xticks(numpy.linspace(PlotStartUT,PlotEndUT,nUTHours,endpoint=True))
        pyplot.xlim(PlotStartUT,PlotEndUT)
        pyplot.grid()

    pyplot.savefig(EnvPlotFile, dpi=dpi, bbox_inches='tight', pad_inches=0.10)


    ###########################################################
    ## Make Recent Conditions Plot (Last 2 hours)
    ###########################################################
    if (DateString == NowString):
        logger.info("Writing Output File: "+RecentPlotFileName)
        dpi=100
        Figure = pyplot.figure(figsize=(13,6.7), dpi=dpi)
        now = datetime.datetime.utcnow()
        nowDateString = "%04d%02d%02dUT" % (now.year, now.month, now.day)
        nowDecimal = now.hour + now.minute/60. + now.second/3600.

        if nowDateString == DateString:
            if nowDecimal < 2:
                PlotStartUT = 0
                PlotEndUT = 2
            else:
                PlotStartUT = nowDecimal-2.
                PlotEndUT = nowDecimal
            nUTHours = 3

            time_ticks_values = numpy.arange(math.floor(PlotStartUT),math.ceil(PlotEndUT),0.25)
            time_tick_labels = ['{:d}:{:02d}'.format(int(math.floor(value)), int((value % 1)*60)) for value in time_ticks_values]

            ###########################################################
            ## Temperatures
            if FoundV20Env or FoundV5Env:
                TemperatureAxes = pyplot.axes([0.0, 0.53, 0.45, 0.47])
                TemperatureAxes.set_xticklabels(time_tick_labels)
                pyplot.title("Recent Environmental Data for "+telescope)

                if telescope == "V20" and FoundV20Env:
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['TubeTemp'], 'go-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Tube Temp")
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['OutsideTemp'], 'ko-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Outside Temp ("+telescope+")")
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['PrimaryTemp'], 'ro-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Mirror Temp")
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['DomeTemp'], 'co-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Dome Temp")

                if telescope == "V5" and FoundV5Env:
#                     if FoundV20Env:
#                         pyplot.plot(V20EnvTable['Time'], V20EnvTable['OutsideTemp'], 'ko-', alpha=0.2, \
#                                     markersize=3, markeredgewidth=0, drawstyle="default", \
#                                     label="Outside Temp ("+OtherTelescope+")")
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['TubeTemp'], 'go-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Tube Temp")
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['OutsideTemp'], 'ko-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Outside Temp ("+telescope+")")

                pyplot.legend(loc='best', prop={'size':10})
                pyplot.ylabel("Temperature (F)")
                pyplot.xticks(time_ticks_values)
                pyplot.xlim(PlotStartUT,PlotEndUT)
                pyplot.grid()

                ## Overplot Twilights
                pyplot.axvspan(SunsetDecimal, EveningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)
                pyplot.axvspan(EveningCivilTwilightDecimal, EveningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
                pyplot.axvspan(EveningNauticalTwilightDecimal, EveningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
                pyplot.axvspan(EveningAstronomicalTwilightDecimal, MorningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.5)
                pyplot.axvspan(MorningAstronomicalTwilightDecimal, MorningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
                pyplot.axvspan(MorningNauticalTwilightDecimal, MorningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
                pyplot.axvspan(MorningCivilTwilightDecimal, SunriseDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)

                ## Add Fan Power (if VYSOS-20)
                if telescope == "V20":
                    Figure.add_axes([0.0, 0.34, 0.45, 0.13], xticklabels=[])
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['DomeFan'], 'co-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Dome Fan State")
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['FanPower'], 'bo-', 
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Mirror Fans (%)")
                    pyplot.xticks(time_ticks_values)
                    pyplot.xlim(PlotStartUT,PlotEndUT)
                    pyplot.ylim(-10,110)
                    pyplot.yticks(numpy.linspace(0,100,3,endpoint=True))
                    pyplot.legend(loc='center left', prop={'size':10})
                    pyplot.grid()


            ###########################################################
            ## Humidity
            if FoundV20Env or FoundV5Env:
                if telescope == "V5" and FoundV5Env:
                    Figure.add_axes([0.0, 0.0, 0.45, 0.47], xticklabels=time_tick_labels)
                    if FoundV20Env:
                        pyplot.plot(V20EnvTable['Time'], V20EnvTable['Humidity'], 'ko-', alpha=0.2, \
                                    markersize=3, markeredgewidth=0, drawstyle="default", \
                                    label="Humidity ("+OtherTelescope+")")
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['Humidity'], 'bo-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Humidity ("+telescope+")")
                    pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="1"), color='green', alpha=0.5)
                    pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="2"), color='red', alpha=0.5)
                    pyplot.fill_between(V5EnvTable['Time'], -5, V5EnvTable['Humidity'], where=(V5EnvTable['WetCondition']=="3"), color='red', alpha=0.8)            
                if telescope == "V20" and FoundV20Env:
                    Figure.add_axes([0.0, 0.0, 0.45, 0.33])
                    if FoundV5Env:
                        pyplot.plot(V5EnvTable['Time'], V5EnvTable['Humidity'], 'ko-', alpha=0.2, \
                                    markersize=3, markeredgewidth=0, drawstyle="default", \
                                    label="Humidity ("+OtherTelescope+")")            
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['Humidity'], 'bo-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Humidity ("+telescope+")")
                    pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="1"), color='green', alpha=0.5)
                    pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="2"), color='red', alpha=0.5)
                    pyplot.fill_between(V20EnvTable['Time'], -5, V20EnvTable['Humidity'], where=(V20EnvTable['WetCondition']=="3"), color='red', alpha=0.8)            
                pyplot.legend(loc='best', prop={'size':10})
                pyplot.ylabel("Humidity (%)")
                pyplot.xticks(time_ticks_values)
                pyplot.xlim(PlotStartUT,PlotEndUT)
                pyplot.ylim(-5,105)
                pyplot.grid()

            ###########################################################
            ## Sky Condition (Cloudiness)
            if FoundV20Env or FoundV5Env:
                Figure.add_axes([0.53, 0.53, 0.45, 0.47], xticklabels=time_tick_labels)
                if telescope == "V20" and FoundV20Env:
                    if FoundV5Env:
                        pyplot.plot(V5EnvTable['Time'], V5EnvTable['SkyTemp'], 'ko-', alpha=0.2, \
                                    markersize=3, markeredgewidth=0, drawstyle="default", \
                                    label="Cloudiness ("+OtherTelescope+")")
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['SkyTemp'], 'bo-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Cloudiness ("+telescope+")")
                    pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="1"), color='green', alpha=0.5)
                    pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="2"), color='yellow', alpha=0.8)
                    pyplot.fill_between(V20EnvTable['Time'], -140, V20EnvTable['SkyTemp'], where=(V20EnvTable['CloudCondition']=="3"), color='red', alpha=0.8)
                if telescope == "V5" and FoundV5Env:
                    if FoundV20Env:
                        pyplot.plot(V20EnvTable['Time'], V20EnvTable['SkyTemp'], 'ko-', alpha=0.2, \
                                    markersize=3, markeredgewidth=0, drawstyle="default", \
                                    label="Cloudiness ("+OtherTelescope+")")
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['SkyTemp'], 'bo-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Cloudiness ("+telescope+")")
                    pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="1"), color='green', alpha=0.5)
                    pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="2"), color='yellow', alpha=0.8)
                    pyplot.fill_between(V5EnvTable['Time'], -140, V5EnvTable['SkyTemp'], where=(V5EnvTable['CloudCondition']=="3"), color='red', alpha=0.8)

                pyplot.legend(loc='best', prop={'size':10})
                pyplot.ylabel("Cloudiness (Delta T) (F)")
                pyplot.xticks(time_ticks_values)
                pyplot.xlim(PlotStartUT,PlotEndUT)
                pyplot.ylim(-100,-20)
                pyplot.grid()

            ###########################################################
            ## Wind Speed
            if FoundV20Env or FoundV5Env:
                Figure.add_axes([0.53, 0.0, 0.45, 0.47], xticklabels=time_tick_labels)
                if telescope == "V20" and FoundV20Env:
                    if FoundV5Env:
                        pyplot.plot(V5EnvTable['Time'], V5EnvTable['WindSpeed'], 'ko-', alpha=0.2, \
                                    markersize=3, markeredgewidth=0, drawstyle="default", \
                                    label="Wind Speed ("+OtherTelescope+")")
                    pyplot.plot(V20EnvTable['Time'], V20EnvTable['WindSpeed'], 'bo-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Wind Speed ("+telescope+")")
                    pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="1"), color='green', alpha=0.5)
                    pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="2"), color='yellow', alpha=0.8)
                    pyplot.fill_between(V20EnvTable['Time'], 0, V20EnvTable['WindSpeed'], where=(V20EnvTable['WindCondition']=="3"), color='red', alpha=0.8)
                    pyplot.ylim(0,max([max(V20EnvTable['WindSpeed'])*1.1,35.]))
                if telescope == "V5" and FoundV5Env:
                    if FoundV20Env:
                        pyplot.plot(V20EnvTable['Time'], V20EnvTable['WindSpeed'], 'ko-', alpha=0.2, \
                                    markersize=3, markeredgewidth=0, drawstyle="default", \
                                    label="Wind Speed ("+OtherTelescope+")")
                    pyplot.plot(V5EnvTable['Time'], V5EnvTable['WindSpeed'], 'bo-', \
                                markersize=3, markeredgewidth=0, drawstyle="default", \
                                label="Wind Speed ("+telescope+")")
                    pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="1"), color='green', alpha=0.5)
                    pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="2"), color='yellow', alpha=0.8)
                    pyplot.fill_between(V5EnvTable['Time'], 0, V5EnvTable['WindSpeed'], where=(V5EnvTable['WindCondition']=="3"), color='red', alpha=0.8)
                    pyplot.ylim(0,max([max(V5EnvTable['WindSpeed'])*1.1,35.]))

                pyplot.legend(loc='best', prop={'size':10})
                pyplot.ylabel("Wind Speed (mph)")
                pyplot.xlabel("Time in Hours UT")
                pyplot.xticks(time_ticks_values)
                pyplot.xlim(PlotStartUT,PlotEndUT)
                pyplot.grid()

            pyplot.savefig(RecentPlotFile, dpi=dpi, bbox_inches='tight', pad_inches=0.10)

    logger.info('Done.')

    if os.path.exists(PlotFile):
        return True
    else:
        return False


def main(argv=None):
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add arguments
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    parser.add_argument("-d", "--date", 
        dest="date", required=False, default="", type=str,
        help="UT date of night to analyze. (i.e. '20130805UT')")
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    args = parser.parse_args()

    ##-------------------------------------------------------------------------
    ## Make logger
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('MakeNightlyPlotsLogger')
    logger.setLevel(logging.DEBUG)
    LogConsoleHandler = logging.StreamHandler()
    if args.verbose:
        LogConsoleHandler.setLevel(logging.DEBUG)
    else:
        LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)


    ##-------------------------------------------------------------------------
    ## Set date to tonight if not specified
    ##-------------------------------------------------------------------------
    now = time.gmtime()
    DateString = time.strftime("%Y%m%dUT", now)
    if not args.date:
        args.date = DateString

    ## Run MakePlots Function
    Success = MakePlots(args.date, args.telescope, logger)


if __name__ == '__main__':
    main()

