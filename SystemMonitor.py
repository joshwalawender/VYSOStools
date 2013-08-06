#!/usr/bin/env python
# encoding: utf-8

import sys
import os
import subprocess32
import time
import math
import re
import logging

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
        if PacketLoss <= 2./7.*100.:
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
    homePath = os.path.expandvars("$HOME")
    LogFileName = os.path.join(homePath, "IQMon", "Logs", DateString+"_StatusLog.txt")
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


    ## Get CPU Load over Last 1 minute
    IOStatOutput = subprocess32.check_output('iostat', timeout=5)
    idx_1m = IOStatOutput.split("\n")[1].split().index("1m")
    CPU_1m = IOStatOutput.split("\n")[2].split()[idx_1m]
    logger.info("CPU Load over last minute = {0}".format(CPU_1m))

    ## Get Temperatures
    TempHeader = subprocess32.check_output(['tempmonitor', '-f', '-th'], timeout=5)
    TempOutput = subprocess32.check_output(['tempmonitor', '-f', '-tv'], timeout=5)
    idx_cpu = TempHeader.split(",").index('"SMC CPU A PROXIMITY"')
    TempCPU = float(TempOutput.split(",")[idx_cpu])
    logger.info("CPU Temperature = {0:.1f} F".format(TempCPU))

    ## Ping Devices
    names = ['Router', 'Switch', 'OldRouter', 'Panoptes', 'Altair', 'CCTV', 'MLOAllSky']
    IPs = ['192.168.1.1', '192.168.1.2', '192.168.1.10', '192.168.1.50', '192.168.1.102', '192.168.1.103', '192.168.1.104']
    Addresses = dict(zip(names, IPs))
    nPings = 7
    ## Loop through devices and get ping results
    for Device in names:
        Status, PacketLoss, AvgRT = TestDevice(Addresses[Device], nPings)
        logger.info("{0} status is {1} with {2} % loss and {3} avg return time.".format(Device, Status, PacketLoss, AvgRT))



if __name__ == '__main__':
    main()
