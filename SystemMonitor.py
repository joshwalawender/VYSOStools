#!/usr/bin/env python
# encoding: utf-8
'''
This is a program to check the condition of the various computers at VYSOS.  It
is mostly just a quick and dirty script to play around with.  The script runs
via crontab once every few minutes.
'''

import sys
import os
import subprocess
import time
import math
import re
import logging

from astropy import table
from astropy.io import ascii

##-----------------------------------------------------------------------------
## Function to Ping and Address and Return Stats
##-----------------------------------------------------------------------------
def TestDevice(address, nPings):    
    MatchPingResult = re.compile(".*([0-9]+)\spackets\stransmitted,\s([0-9]+)\spackets received,\s([0-9\.]+).\spacket\sloss.*")
    MatchPingStats  = re.compile(".*round\-trip\smin/avg/max/stddev\s=\s([0-9\.]+)/([0-9\.]+)/([0-9\.]+)/([0-9\.]+)\sms.*")

    try:
        result = subprocess.check_output(["ping", "-c "+str(nPings), address])
    except:
        return 'down', 100, None
    else:
        foo = result.find("statistics ---") + len("statistics ---")
        result = result[foo+1:-1]
        IsMatch = MatchPingResult.match(result)
        if IsMatch:
            PacketLoss = float(IsMatch.group(3))
            bar = result.find("packet loss") + len("packet loss")
            statstring = result[bar+1:]
            IsStats = MatchPingStats.match(statstring)
            if IsStats:
                AvgRT = float(IsStats.group(2))
            else:
                AvgRT = None
        else:
            PacketLoss = None
            AvgRT = None
        if not math.isnan(PacketLoss):
            if PacketLoss <= 50.:
                Status = "up"
            else:
                Status = "down"
        else:
            Status = "unknown"
        return Status, PacketLoss, AvgRT


##-----------------------------------------------------------------------------
## Main Program
##-----------------------------------------------------------------------------
def main():

    ##-------------------------------------------------------------------------
    ## Create Logger Object
    ##-------------------------------------------------------------------------
    now = time.gmtime()
    DateString = time.strftime("%Y%m%dUT", now)
    TimeString = time.strftime("%Y%m%dUTat%H:%M:%S", now)
    homePath = os.path.expandvars("$HOME")
    LogFileName = os.path.join(homePath, "IQMon", "Logs", "SystemStatus", DateString+"_Log.txt")
    logger = logging.getLogger('Logger')
    logger.setLevel(logging.DEBUG)
    LogFileHandler = logging.FileHandler(LogFileName)
    LogFileHandler.setLevel(logging.DEBUG)
    LogConsoleHandler = logging.StreamHandler()
    LogConsoleHandler.setLevel(logging.DEBUG)
    LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
    LogFileHandler.setFormatter(LogFormat)
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)
    logger.addHandler(LogFileHandler)

    ##-------------------------------------------------------------------------
    ## Get CPU Load over Last 1 minute
    ##-------------------------------------------------------------------------
    IOStatOutput = subprocess.check_output('iostat')
    idx_1m = IOStatOutput.split("\n")[1].split().index("1m")
    CPU_1m = float(IOStatOutput.split("\n")[2].split()[idx_1m])
    logger.info("CPU Load over last 1 min = {0:.2f}".format(CPU_1m))
    idx_5m = IOStatOutput.split("\n")[1].split().index("5m")
    CPU_5m = float(IOStatOutput.split("\n")[2].split()[idx_5m])
    logger.info("CPU Load over last 5 min = {0:.2f}".format(CPU_5m))

    ##-------------------------------------------------------------------------
    ## Get Temperatures
    ##-------------------------------------------------------------------------
    TempHeader = subprocess.check_output(['tempmonitor', '-f', '-th'])
    TempOutput = subprocess.check_output(['tempmonitor', '-f', '-tv'])
    idx_cpu = TempHeader.split(",").index('"SMC CPU A PROXIMITY"')
    TempCPU = float(TempOutput.split(",")[idx_cpu])
    logger.info("CPU Temperature = {0:.1f} F".format(TempCPU))

    ##-------------------------------------------------------------------------
    ## Ping Devices
    ##-------------------------------------------------------------------------
    Addresses = {'Router': '192.168.1.1',\
                 'Switch': '192.168.1.2',\
                 'OldRouter': '192.168.1.10',\
                 'Vega': '192.168.1.122',\
                 'Black': '192.168.1.112',\
                 'Panoptes': '192.168.1.50',\
                 'Altair': '192.168.1.102',\
                 'CCTV': '192.168.1.103',\
                 'MLOAllSky': '192.168.1.104',\
                 }
    StatusValues = {}
    PacketLosses = {}
    AvgReturnTimes = {}

    nPings = 3
    ## Loop through devices and get ping results
    for Device in Addresses.keys():
        Status, PacketLoss, AvgRT = TestDevice(Addresses[Device], nPings)
        StatusValues[Device] = Status
        PacketLosses[Device] = PacketLoss
        AvgReturnTimes[Device] = AvgRT
        if (Status == 'up'):
            logger.info("{0:10s} is {1:4s} with {2:3.0f} % loss and {3:5.2f} avg return time.".format(Device, Status, PacketLoss, AvgRT))
        else:
            logger.info("{0:10s} is {1:4s}".format(Device, Status))

    ##-------------------------------------------------------------------------
    ## Check for NFS Mounts
    ##-------------------------------------------------------------------------
    V5_mount = os.path.exists(os.path.join('/', 'Volumes', 'Data_V5'))
    V20_mount = os.path.exists(os.path.join('/', 'Volumes', 'Data_V20'))


    ##-------------------------------------------------------------------------
    ## Write Results to Astropy Table and Save to ASCII File
    ##-------------------------------------------------------------------------
    ResultsFile = os.path.join(homePath, "IQMon", "Logs", "SystemStatus", DateString+".txt")
    
    names = ['time', 'CPU Load(1m)', 'CPU Load(5m)', 'CPU Temperature', 'V5 NFS Mount', 'V20 NFS Mount']
    types = ['a24',  'f4',           'f4',           'f4',              'a6',           'a6']
    TypesDict = dict(zip(names, types))
    for Device in StatusValues.keys():
        names.append(Device)
        types.append('a4')
        TypesDict[Device] = 'a4'
    converters = {}
    for Device in TypesDict.keys():
        converters[Device] = [ascii.convert_numpy(type)]
    if not os.path.exists(ResultsFile):
        ResultsTable = table.Table(names=tuple(names), dtype=tuple(types))
    else:
        ResultsTable = ascii.read(ResultsFile,
                                  guess=False,
                                  header_start=0, data_start=1,
                                  Reader=ascii.basic.Basic,
                                  delimiter="\s",
                                  converters=converters)
    ## Add line to table
    newResults = [TimeString, CPU_1m, CPU_5m, TempCPU, V5_mount, V20_mount]
    for Device in StatusValues.keys():
        newResults.append(StatusValues[Device])
    ResultsTable.add_row(tuple(newResults))
    ascii.write(ResultsTable, ResultsFile, Writer=ascii.basic.Basic)


    ##-------------------------------------------------------------------------
    ## Read Results File and Make Plot of System Status for Today
    ##-------------------------------------------------------------------------
    

if __name__ == '__main__':
    main()
