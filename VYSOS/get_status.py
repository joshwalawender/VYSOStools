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
import numpy as np
import pymongo

import win32com.client
import pywintypes

# import mongoengine as me
# from VYSOS.schema import telstatus

##-------------------------------------------------------------------------
## Query ASCOM ACPHub for Telescope Position and State
##-------------------------------------------------------------------------
def get_telescope_info(status, logger):
    logger.info('Getting ACP status')
    try:
        ACP = win32com.client.Dispatch("ACP.Telescope")
    except:
        logger.error('Could not connect to ACP ASCOM object.')
        return status

    try:
        status['connected'] = ACP.Connected
        logger.debug('  ACP Connected = {}'.format(status['connected']))
        if status['connected']:
            status['park'] = ACP.AtPark
            logger.info('  ACP At Park = {}'.format(status['park']))
            status['slewing'] = ACP.Slewing
            logger.info('  ACP Slewing = {}'.format(status['slewing']))
            status['tracking'] = ACP.Tracking
            logger.info('  ACP Tracking = {}'.format(status['tracking']))
            status['alt'] = float(ACP.Altitude)
            logger.info('  ACP Alt = {:.2f}'.format(status['alt']))
            status['az'] = float(ACP.Azimuth)
            logger.info('  ACP Az = {:.2f}'.format(status['az']))
            try:
                status['RA'] = ACP.TargetRightAscension * 15.0
                status['DEC'] = ACP.TargetDeclination
                logger.info('  ACP target RA = {:.4f}'.format(status['RA']))
                logger.info('  ACP target Dec = {:.4f}'.format(status['DEC']))
            except:
                logger.info('  Could not get target info')
    except pywintypes.com_error as err:
        logger.warning('COM error:')
        logger.warning('  {}'.format(err.message))
        status['ACPerr'] = '{}'.format(err.message)
    except:
        status['connected'] = False
        logger.warning('Queries to ACP object failed')

    return status


##-------------------------------------------------------------------------
## Query ASCOM Focuser for Position, Temperature, Fan State
##-------------------------------------------------------------------------
def get_focuser_info(status, logger):
    logger.info('Getting ASCOM focuser status')
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
        return status

    ## Get Average of 3 Temperature Readings
    FocusMax_Temps = []
    for i in range(0,3,1):
        try:
            newtemp = float(FocusMax.Temperature)
            logger.debug('  Queried FocusMax temperature = {:.1f}'.format(newtemp))
            FocusMax_Temps.append(newtemp)
        except:
            pass
    if len(FocusMax_Temps) > 0:
        ## Filter out bad values
        median_temp = np.median(FocusMax_Temps)
        if (median_temp > -10) and (median_temp < 150):
            status['focuser_temperature'] = median_temp
            logger.info('  FocusMax temperature = {:.1f} {}'.format(status['focuser_temperature'], 'C'))
    ## Get Position
    try:
        status['focuser_position'] = int(FocusMax.Position)
        logger.info('  FocusMax position = {:d}'.format(status['focuser_position']))
    except:
        pass

    return status


##-------------------------------------------------------------------------
## Query RCOS TCC
##-------------------------------------------------------------------------
def get_RCOS_info(status, logger):
    logger.info('Getting RCOS TCC status')
    try:
        RCOST = win32com.client.Dispatch("RCOS_AE.Temperature")
        RCOSF = win32com.client.Dispatch("RCOS_AE.Focuser")
        logger.debug('  Connected to RCOS focuser')
    except:
        logger.error('Could not connect to RCOS ASCOM object.')
        return status

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
    if len(RCOS_Truss_Temps) >= 3:
        status['truss_temperature'] = (float(np.median(RCOS_Truss_Temps)) - 32.)/1.8
        logger.info('  RCOS temperature (truss) = {:.1f} {}'.format(
                    status['truss_temperature'], 'C'))
    if len(RCOS_Primary_Temps) >= 3:
        status['primary_temperature'] = (float(np.median(RCOS_Primary_Temps)) - 32.)/1.8
        logger.info('  RCOS temperature (primary) = {:.1f} {}'.format(
                    status['primary_temperature'], 'C'))
    if len(RCOS_Secondary_Temps) >= 3:
        status['secondary_temperature'] = (float(np.median(RCOS_Secondary_Temps)) - 32.)/1.8
        logger.info('  RCOS temperature (secondary) = {:.1f} {}'.format(
                    status['secondary_temperature'], 'C'))
    if len(RCOS_Fan_Speeds) >= 3:
        status['fan_speed'] = float(np.median(RCOS_Fan_Speeds))
        logger.info('  RCOS fan speed = {:.0f} %'.format(status['fan_speed']))

    return status



##-------------------------------------------------------------------------
## Query ControlByWeb Temperature Module for Temperature and Fan State
##-------------------------------------------------------------------------
def control_by_web(status, logger):
    logger.info('Getting CBW temperature module status')
    address = 'http://192.168.1.115/state.xml'
    import urllib2
    response = urllib2.urlopen(address)
    raw_result = response.read()
    tunits = re.search('<units>(\w+)</units>', raw_result).group(1)
    assert tunits in ['F', 'C']
    temp1 = float(re.search('<sensor1temp>(\d+\.\d*)</sensor1temp>', raw_result).group(1))
    r1state = bool(int(re.search('<relay1state>(\d)</relay1state>', raw_result).group(1)))
    r2state = bool(int(re.search('<relay2state>(\d)</relay2state>', raw_result).group(1)))

    if tunits == 'C':
        temp1 = temp1*9./5. + 32.
        tunits = 'F'

    status['dome_temperature'] = temp1
    status['fan_state'] = r1state
    status['fan_enable'] = r2state

    return status


def get_status_and_log(telescope, logger):

    ##-------------------------------------------------------------------------
    ## Get Status Info
    ##-------------------------------------------------------------------------
    logger.info('#### Starting Status Queries ####')
    status = {'telescope': telescope,
              'date':datetime.datetime.utcnow()
             }
    status = get_telescope_info(status, logger)
    status = get_focuser_info(status, logger)
    if telescope == 'V20':
        status = get_RCOS_info(status, logger)

    ##-------------------------------------------------------------------------
    ## Write to Mongo
    ##-------------------------------------------------------------------------
    done = False
    while done is False:
        try:
            logger.info('Connecting to mongo db at 192.168.1.101')
            client = pymongo.MongoClient('192.168.1.101', 27017)
            db = client.vysos
            status_collection = db['{}status'.format(telescope)]
        except:
            logger.error('Failed to connect to mongo')
        else:
            ## Save new "current" document
            try:
                inserted_id = status_collection.insert_one(status).inserted_id
                logger.info("  Inserted document id: {}".format(inserted_id))
                done = True
            except:
                e = sys.exc_info()[0]
                logger.error('Failed to add new document')
                logger.error('Will wait 10 seconds and try again')
                logger.error(e)
                time.sleep(10)
            client.close()


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
        type=str, dest="telescope", default='',
        choices=['V5', 'V20', ''], required=False,
        help="The telescope system we are querying.  Will query weather if not specified.")
    args = parser.parse_args()

    telescope = args.telescope

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
        LogFormat = logging.Formatter('%(asctime)s %(levelname)8s: %(message)s',
                                      datefmt='%Y%m%d %H:%M:%S')
        LogConsoleHandler.setFormatter(LogFormat)
        logger.addHandler(LogConsoleHandler)


    run = True
    while run:
        get_status_and_log(telescope, logger)
#         run = False
        logging.shutdown()
        time.sleep(20)
