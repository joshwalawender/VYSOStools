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

    result = subprocess.check_output(["ping", "-c "+str(nPings), address])
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
    CPU_1m = IOStatOutput.split("\n")[2].split()[idx_1m]
    logger.info("CPU Load over last 1 min = {0}".format(CPU_1m))
    idx_5m = IOStatOutput.split("\n")[1].split().index("5m")
    CPU_5m = IOStatOutput.split("\n")[2].split()[idx_5m]
    logger.info("CPU Load over last 5 min = {0}".format(CPU_5m))

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
    names = ['Router', 'Switch', 'OldRouter', 'Panoptes', 'Altair', 'CCTV', 'MLOAllSky']
    IPs = ['192.168.1.1', '192.168.1.2', '192.168.1.10', '192.168.1.50', '192.168.1.102', '192.168.1.103', '192.168.1.104']
    Addresses = dict(zip(names, IPs))
    nPings = 3
    ## Loop through devices and get ping results
    DeviceStatusList = []
    for Device in names:
        Status, PacketLoss, AvgRT = TestDevice(Addresses[Device], nPings)
        DeviceStatusList.append(Status)
        logger.info("{0} status is {1} with {2} % loss and {3} avg return time.".format(Device, Status, PacketLoss, AvgRT))

    ##-------------------------------------------------------------------------
    ## Write Results to Astropy Table and Save to ASCII File
    ##-------------------------------------------------------------------------
    ResultsFile = os.path.join(homePath, "IQMon", "Logs", "SystemStatus", DateString+".txt")
    ColNames = ["time", "CPU Load", "CPU Temperature"]
    Types = ['a24', 'f4', 'f4']
    for Device in names:
        ColNames.append(Device)
        Types.append('a6')
    converters = {}
    for idx in range(0, len(ColNames)):
        converters[ColNames[idx]] = ascii.convert_numpy(Types[idx])
    if not os.path.exists(ResultsFile):    
        ResultsTable = table.Table(names=tuple(ColNames), dtypes=tuple(Types))
    else:
        ResultsTable = ascii.read(ResultsFile,
                                  guess=False,
                                  header_start=0, data_start=1,
                                  Reader=ascii.basic.Basic,
                                  delimiter="\s",
                                  converters=converters)
    ## Add line to table
    newResults = [TimeString, CPU_5m, TempCPU]
    for DeviceStatus in DeviceStatusList:
        newResults.append(DeviceStatus)
    ResultsTable.add_row(tuple(newResults))
    ascii.write(ResultsTable, ResultsFile, Writer=ascii.basic.Basic)


    ##-------------------------------------------------------------------------
    ## Read Results File and Make Plot of System Status for Today
    ##-------------------------------------------------------------------------
    

if __name__ == '__main__':
    main()
