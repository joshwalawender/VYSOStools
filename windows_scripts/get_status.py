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


def GetClarity(ClarityDataFile, logger):
    ## Cloud Condition   | Wind Condition   | Rain Condition | Day Condition    | RoofClose
    ##   0 = unknown     |   0 = unknown    |   0 = unknown  |   0 = unknown    |  0 = not requested
    ##   1 = clear       |   1 = calm       |   1 = dry      |   1 = dark       |  1 = requested
    ##   2 = cloudy      |   2 = windy      |   2 = wet      |   2 = light      |
    ##   3 = very cloudy |   3 = very windy |   3 = rain     |   3 = very light | 

    with open(ClarityDataFile, 'r') as clarityFO:
        contents = clarityFO.read()
    print(contents)

#     ClarityGood = None
#     try:
#         ClarityData = ascii.read(ClarityDataFile, guess=False, delimiter=" ", comment="#", data_start=0, Reader=ascii.NoHeader)
#         Date             = str(ClarityData[0][0])
#         Time             = str(ClarityData[0][1])
#         TempUnits        = str(ClarityData[0][2])
#         WindUnits        = str(ClarityData[0][3])
#         SkyTemp          = float(ClarityData[0][4])
#         AmbTemp          = float(ClarityData[0][5])
#         SensorTemp       = float(ClarityData[0][6])
#         WindSpeed        = float(ClarityData[0][7])
#         Humidity         = float(ClarityData[0][8])
#         DewPoint         = float(ClarityData[0][9])
#         Heater           = ClarityData[0][10]
#         RainFlag         = int(ClarityData[0][11])
#         WetFlag          = int(ClarityData[0][12])
#         Since            = ClarityData[0][13]
#         VB6Now           = ClarityData[0][14]
#         CloudCondition   = int(ClarityData[0][15])
#         WindCondition    = int(ClarityData[0][16])
#         RainCondition    = int(ClarityData[0][17])
#         DayCondition     = int(ClarityData[0][18])
#         RoofClose        = int(ClarityData[0][19])
#     except:
#         return None
# 
#     ## Check that Data File is not Stale
#     now = datetime.datetime.now()
#     logger.debug('  Clarity File: {} {}'.format(Date, Time))
#     logger.debug('  Current (HST): {}'.format(now.strftime('%Y-%m-%d %H:%M:%S')))
#     ClarityTime = datetime.datetime.strptime(Date+' '+Time[0:-3], '%Y-%m-%d %H:%M:%S')
#     difference = now - ClarityTime
#     logger.debug('  Clarity file is stale by {} seconds.'.format(difference.seconds))
#     if difference.seconds <= 30.0: ClarityGood = True
# 
#     ## Standardize Temperature Units to Farenheit (F)
#     if TempUnits == "C":
#         ## Change Units to F
#         SkyTemp    = SkyTemp*9./5. + 32.
#         AmbTemp    = AmbTemp*9./5. + 32.
#         DewPoint   = DewPoint*9./5. + 32.
#     elif TempUnits == "F":
#         pass
#     else:
#         ClarityGood=False
# 
#     ## Standardize Wind Speed Units to Miles Per Hour (MPH)
#     if WindUnits == "M":
#         ## units are MPH
#         pass
#     elif WindUnits == "K":
#         ## units are KPH
#         WindSpeed = WindSpeed * 0.621
#     elif WindUnits == "m":
#         WindSpeed = WindSpeed * 2.237
#     else:
#         ClarityGood == False
# 
#     if ClarityGood:
#         return [ClarityTime, SkyTemp, AmbTemp, WindSpeed, Humidity, DewPoint, CloudCondition, WindCondition, RainCondition, DayCondition, RoofClose]
#     else:
#         return None


def main():
    ClarityDataFile = os.path.join("C:\\", "Users", "vysosuser", "Documents", "ClarityII", "ClarityData.txt")
    ClarityArray = GetClarity(ClarityDataFile, logger)

if __name__ == '__main__':
    main()
