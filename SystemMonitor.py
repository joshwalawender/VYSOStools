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
import datetime
import time
import math
import re
import logging
import numpy as np
import copy

from astropy import table
from astropy.io import ascii

import matplotlib.pyplot as plt

##-----------------------------------------------------------------------------
## Function to Ping and Address and Return Stats
##-----------------------------------------------------------------------------
def TestDevice(address, nPings):    
    MatchPingResult = re.compile(".*([0-9]+)\spackets\stransmitted,\s([0-9]+)\spackets received,\s([0-9\.]+).\spacket\sloss.*")
    MatchPingStats  = re.compile(".*round\-trip\smin/avg/max/stddev\s=\s([0-9\.]+)/([0-9\.]+)/([0-9\.]+)/([0-9\.]+)\sms.*")

    try:
        result = subprocess.check_output(["ping", "-c "+str(nPings), '-t 3', address])
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
    now = datetime.datetime.utcnow()
    DateString = now.strftime("%Y%m%dUT")
    TimeString = now.strftime("%Y%m%dUTat%H:%M:%S")
    HourDecimal = now.hour + now.minute/60. + now.second/3600.
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
#                  'Switch': '192.168.1.2',\
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
    if not (V5_mount and V20_mount):
        subprocess.call(['open', os.path.join(os.path.expanduser('~vysosuser'), 'bin', 'ConnectToData.app')])
#         time.sleep(30)
#         V5_mount = os.path.exists(os.path.join('/', 'Volumes', 'Data_V5'))
#         V20_mount = os.path.exists(os.path.join('/', 'Volumes', 'Data_V20'))



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
    logger.info('Writing results to table: {}'.format(ResultsFile))
    ascii.write(ResultsTable, ResultsFile, Writer=ascii.basic.Basic)


    ##-------------------------------------------------------------------------
    ## Read Results File and Make Plot of System Status for Today
    ##-------------------------------------------------------------------------
    plot_file = os.path.join(homePath, "IQMon", "Logs", "SystemStatus", DateString+".png")
    plot_positions = [ [0.050, 0.480, 0.700, 0.470], [0.760, 0.480, 0.190, 0.470],\
                       [0.050, 0.280, 0.700, 0.180], [0.760, 0.280, 0.190, 0.180],\
                       [0.050, 0.080, 0.700, 0.180], [0.760, 0.080, 0.190, 0.180] ]

    logger.info('Making plot: {}'.format(plot_file))
    dpi=100
    fig = plt.figure(figsize=(12,6), dpi=dpi)

    time = [datetime.datetime.strptime(entry['time'], "%Y%m%dUTat%H:%M:%S") for entry in ResultsTable]
    time_decimal = [(val.hour + val.minute/60. + val.second/3600.) for val in time]
    V5_NFSmount = [(val == True) for val in ResultsTable['V5 NFS Mount']]
    V20_NFSmount = [(val == True) for val in ResultsTable['V20 NFS Mount']]
    router_up = [(val == 'up') for val in ResultsTable['Router']]
    altair_up = [(val == 'up') for val in ResultsTable['Altair']]
    vega_up = [(val == 'up') for val in ResultsTable['Vega']]
    black_up = [(val == 'up') for val in ResultsTable['Black']]
    panoptes_up = [(val == 'up') for val in ResultsTable['Panoptes']]
    cctv_up = [(val == 'up') for val in ResultsTable['CCTV']]

    ## CPU Load
    CPU_load_axes = plt.axes(plot_positions[0], xticklabels=[])
    plt.title('System Status for {}'.format(DateString), size=10)
    plt.plot(time_decimal, ResultsTable['CPU Load(1m)'], 'g,-', label='CPU Load (1m)')
    plt.plot(time_decimal, ResultsTable['CPU Load(5m)'], 'b,-', label='CPU Load (5m)')
    plt.xticks(np.linspace(0,24,25,endpoint=True))
    plt.xlim(0,24)
    plt.ylim(0,4)
    plt.grid()
    plt.ylabel('CPU Load', size=10)
    plt.legend(loc='best', fontsize=10)

    ## CPU Temperature
    CPU_temp_axes = CPU_load_axes.twinx()
    plt.plot(time_decimal, ResultsTable['CPU Temperature'], 'r,-')
    plt.ylim(0,200)
    plt.yticks([])
    plt.xticks(np.linspace(0,24,25,endpoint=True))
    plt.xlim(0,24)

    ## Recent CPU Load
    CPU_load_axes2 = plt.axes(plot_positions[1], xticklabels=[], yticklabels=[])
    plt.plot(time_decimal, ResultsTable['CPU Load(1m)'], 'g,-', label='CPU Load (1m)')
    plt.plot(time_decimal, ResultsTable['CPU Load(5m)'], 'b,-', label='CPU Load (5m)')
    plt.xticks(np.linspace(0,24,25,endpoint=True))
    if HourDecimal > 1:
        plt.xlim(HourDecimal-1,HourDecimal+0.1)
    else:
        plt.xlim(0,1.1)
    plt.ylim(0,4)
    plt.grid()

    ## Recent CPU Temperature
    CPU_temp_axes2 = CPU_load_axes2.twinx()
    CPU_temp_axes2.set_ylabel('CPU Temperature', color='r', size=10)
    plt.plot(time_decimal, ResultsTable['CPU Temperature'], 'r,-')
    plt.ylim(0,200)
    plt.yticks(np.linspace(0,200,11,endpoint=True), color='r', size=10)
    plt.xticks(np.linspace(0,24,25,endpoint=True))
    if HourDecimal > 1:
        plt.xlim(HourDecimal-1,HourDecimal+0.1)
    else:
        plt.xlim(0,1.1)



    ## Computer Status
    fig.add_axes(plot_positions[2], xticklabels=[], yticklabels=['Dn', 'Up'])
    plt.plot(time_decimal, router_up, 'b^',\
             alpha=0.5,mew=0,\
             label='Router')
    plt.plot(time_decimal, vega_up, 'bv',\
             alpha=0.5,mew=0,\
             label='Vega (V5)')
    plt.plot(time_decimal, black_up, 'b>',\
             alpha=0.5,mew=0,\
             label='Black (V20)')
    plt.plot(time_decimal, cctv_up, 'bs',\
             alpha=0.5,mew=0,\
             label='CCTV')
    plt.plot(time_decimal, panoptes_up, 'g<',\
             alpha=0.5,mew=0,\
             label='Panoptes')
    plt.xticks(np.linspace(0,24,25,endpoint=True))
    plt.xlim(0,24)
    plt.ylim(-0.2,1.2)
    plt.yticks([0,1])
    plt.legend(loc='best', fontsize=8)
    plt.grid()
    plt.ylabel('Computer Status', size=10)

    ## Recent Computer Status
    fig.add_axes(plot_positions[3], xticklabels=[], yticklabels=[])
    plt.plot(time_decimal, router_up, 'b^',\
             alpha=0.5,mew=0,\
             label='Router')
    plt.plot(time_decimal, vega_up, 'bv',\
             alpha=0.5,mew=0,\
             label='Vega (V5)')
    plt.plot(time_decimal, black_up, 'b>',\
             alpha=0.5,mew=0,\
             label='Black (V20)')
    plt.plot(time_decimal, cctv_up, 'bs',\
             alpha=0.5,mew=0,\
             label='CCTV')
    plt.plot(time_decimal, panoptes_up, 'g<',\
             alpha=0.5,mew=0,\
             label='Panoptes')
    plt.xticks(np.linspace(0,24,25,endpoint=True))
    if HourDecimal > 1:
        plt.xlim(HourDecimal-1,HourDecimal+0.1)
    else:
        plt.xlim(0,1.1)
    plt.ylim(-0.2,1.2)
    plt.yticks([0,1])
    plt.grid()


    ## NFS Mount Status
    fig.add_axes(plot_positions[4], yticklabels=['N', 'Y'])
    plt.plot(time_decimal, V5_NFSmount, 'b^',\
             alpha=0.5,mew=0,\
             label='V5 NFS Mount')
    plt.plot(time_decimal, V20_NFSmount, 'bv',\
             alpha=0.5,mew=0,\
             label='V20 NFS Mount')
    plt.xticks(np.linspace(0,24,25,endpoint=True))
    plt.xlim(0,24)
    plt.ylim(-0.2,1.2)
    plt.yticks([0,1])
    plt.legend(loc='best', fontsize=10)
    plt.grid()
    plt.ylabel('NFS Mounts', size=10)
    plt.xlabel('Time (UT Hours)', size=10)

    ## Recent NFS Mount Status
    fig.add_axes(plot_positions[5], yticklabels=[])
    plt.plot(time_decimal, V5_NFSmount, 'b^',\
             alpha=0.5,mew=0,\
             label='V5 NFS Mount')
    plt.plot(time_decimal, V20_NFSmount, 'bv',\
             alpha=0.5,mew=0,\
             label='V20 NFS Mount')
    plt.xticks(np.linspace(0,24,25,endpoint=True))
    if HourDecimal > 1:
        plt.xlim(HourDecimal-1,HourDecimal+0.1)
    else:
        plt.xlim(0,1.1)
    plt.ylim(-0.2,1.2)
    plt.yticks([0,1])
    plt.grid()
    plt.xlabel('Time (UT Hours)', size=10)



    plt.savefig(plot_file, dpi=dpi)
    logger.info('Done')



if __name__ == '__main__':
    main()
