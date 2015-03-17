import os
import sys
import re
import logging
import argparse

import socket
import datetime
import time
import subprocess
import pymongo
from pymongo import MongoClient


##-----------------------------------------------------------------------------
##  Define Generic Device on the Network
##-----------------------------------------------------------------------------
class NetworkedDevice:
    def __init__(self, address, logger=None):
        """Class for generic device on the network.  Device must have an IP
        address or hostname.

        Args:
            address (str): Address (IP or hostname) of the device on the network
            logger (logger): Logger object which device will send log messages to.
        """
        try:
            hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(address)
            self.hostname = hostname
            self.ip = ipaddrlist[0]
        except:
            self.hostname = None
            if socket.inet_aton(address):
                self.ip = address
            else:
                self.ip = None
                if logger: logger.critical('Could not determine hostname or IP address from input: {0}'.format(address))
        self.logger = logger
        self.type = None


    def ping(self):
        """Ping device.

        Returns:
            bool: True if device responds to ping, False if not.
        """
        ## Ping Options (from man page of version installed on fmosobcp on 2014/04)
        ##    [fmosobcp] ~ > ping -V
        ##    ping utility, iputils-ss020927
        ## -i = Wait  interval  seconds between sending each packet.
        ## -q = Quiet output.  Nothing is displayed except the summary lines at
        ##      startup time and when finished.
        ## -c = Stop after sending count ECHO_REQUEST packets.
        ## -W = Time  to  wait for a response, in seconds.
        ping_command = ['ping', '-i', '0.2', '-q', '-c', '2', '-W', '2', self.ip]
        try:
            if self.logger:
                if self.hostname: self.logger.debug('Pinging {0}'.format(self.hostname))
                else: self.logger.debug('Pinging {0}'.format(self.ip))
            result = subprocess.check_call(ping_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            if e.returncode == 2:
                ## Reurncode of 1 means no responses, so host is down
                result = 2
            else:
                if self.logger: self.logger.error("Ping failed.  Command: {0}".format(e.cmd))
                if self.logger: self.logger.error("Ping failed.  Returncode: {0}".format(e.returncode))
                if self.logger: self.logger.error("Ping failed.  Output: {0}".format(e.output))
                result = e.returncode
        except:
            if self.logger: self.logger.error("Ping failed.")
            raise
        if (result == 0):
            if self.logger:
                if self.hostname: self.logger.debug('Host {0} is UP'.format(self.hostname))
                else: self.logger.debug('Host {0} is UP'.format(self.ip))
        else:
            if self.logger:
                if self.hostname: self.logger.debug('Host {0} is DOWN'.format(self.hostname))
                else: self.logger.debug('Host {0} is DOWN'.format(self.ip))
        return (result == 0)


##-----------------------------------------------------------------------------
## Main Program
##-----------------------------------------------------------------------------
def main(verbose=False):

    ##-------------------------------------------------------------------------
    ## Create Logger Object
    ##-------------------------------------------------------------------------
    now = datetime.datetime.utcnow()
    DateString = now.strftime("%Y%m%dUT")
    TimeString = now.strftime("%H:%M:%S")
    logger = logging.getLogger('get_system_status_{}'.format(DateString))
    logger.setLevel(logging.DEBUG)
    ## Set up console output
    LogConsoleHandler = logging.StreamHandler()
    if verbose:
        LogConsoleHandler.setLevel(logging.DEBUG)
    else:
        LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)
    ## Set up file output
#     LogFilePath = os.path.join()
#     if not os.path.exists(LogFilePath):
#         os.mkdir(LogFilePath)
#     LogFile = os.path.join(LogFilePath, 'get_status.log')
#     LogFileHandler = logging.FileHandler(LogFile)
#     LogFileHandler.setLevel(logging.DEBUG)
#     LogFileHandler.setFormatter(LogFormat)
#     logger.addHandler(LogFileHandler)


    results = {}

    ##-------------------------------------------------------------------------
    ## Get CPU Load on Local Machine
    ##-------------------------------------------------------------------------
    try:
        logger.info('Running iostat to get CPU load')
        IOStatOutput = subprocess.check_output('iostat')
        for line in IOStatOutput.split('\n'):
            logger.debug(' iostat output: {}'.format(line))
        idx_1m = IOStatOutput.split("\n")[1].split().index("1m")
        results['CPU 1 min'] = float(IOStatOutput.split("\n")[2].split()[idx_1m])
        logger.info("CPU Load over last 1 min = {0:.2f}".format(results['CPU 1 min']))
        idx_5m = IOStatOutput.split("\n")[1].split().index("5m")
        results['CPU 5 min'] = float(IOStatOutput.split("\n")[2].split()[idx_5m])
        logger.info("CPU Load over last 5 min = {0:.2f}".format(results['CPU 5 min']))
    except:
        logger.warning('Failed to read CPU load from iostat')


    ##-------------------------------------------------------------------------
    ## Ping Devices
    ##-------------------------------------------------------------------------
    Addresses = {'Router': '192.168.1.1',\
                 'Altair': '192.168.1.102',\
                 'CCTV': '192.168.1.103',\
                 'Black': '192.168.1.112',\
                 'Vega': '192.168.1.122',\
                 'Panoptes': '192.168.1.50',\
                 'RasPi': '192.168.1.51',\
                 }

    status = {True: 'UP', False: 'DOWN'}
    for Device in Addresses.keys():
        results['Ping {}'.format(Device)] = NetworkedDevice(Addresses[Device], logger=logger).ping()
        logger.info('{} is {}'.format(Device, status[results['Ping {}'.format(Device)]]))

    ##-------------------------------------------------------------------------
    ## Write Status Log
    ##-------------------------------------------------------------------------
    logger.info('Writing results to mongo db at 192.168.1.101')
    client = MongoClient('192.168.1.101', 27017)
    status = client.vysos['system_status']
    logger.debug('  Getting system_status collection')

    new_data = {}
    new_data.update({'UT date': DateString, 'UT time': TimeString})
    new_data.update(results)

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
    args = parser.parse_args()

    main(verbose=args.verbose)
