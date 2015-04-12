import sys
import os
from argparse import ArgumentParser
import logging
from datetime import datetime as dt
from datetime import timedelta as tdelta
import numpy
import astropy.io.ascii as ascii
import pymongo
from pymongo import MongoClient
import make_nightly_plots

def main(startdate, enddate, logger):

    logger.info('Writing results to mongo db at 192.168.1.101')
    try:
        client = MongoClient('192.168.1.101', 27017)
    except:
        logger.error('Could not connect to mongo db')
        raise
    else:
        V5status = client.vysos['V5.status']
        logger.debug('  Getting V5.status collection')
        V20status = client.vysos['V20.status']
        logger.debug('  Getting V20.status collection')


    oneday = tdelta(1, 0)
    date = startdate
    while date <= enddate:
        date_string = date.strftime('%Y%m%dUT')
        logger.info('')
        logger.info('Checking for environmental logs from {}'.format(date_string))
        ## VYSOS-5
        telescope = 'V5'
        logfile = os.path.join('/', 'Volumes', 'Drobo', telescope, 'Logs', date_string, 'EnvironmentalLog.txt')
        if not os.path.exists(logfile):
            logger.warning('  No logfile found for {} on {}'.format(telescope, date_string))
        else:
            logger.info('  Found logfile: {}'.format(logfile))

#             ColStarts = [ 0, 11, 22, 32, 42, 52, 62, 72, 82,  92, 102, 112]
#             ColEnds   = [ 9, 20, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121]
#             ColNames  = ['Date', 'TimeString', 'TubeTemp', 'FocusPos', 
#                          'SkyTemp', 'OutsideTemp', 'WindSpeed', 'Humidity', 'DewPoint', 'Altitude', 'Azimuth', 'Condition']
#             env_table = ascii.read(logfile, data_start=2, Reader=ascii.FixedWidth, 
#                          col_starts=ColStarts, col_ends=ColEnds, names=ColNames, 
#                          guess=False, comment=";", header_start=0,
#                          converters={
#                          'Date': [ascii.convert_numpy(numpy.str)],
#                          'TimeString': [ascii.convert_numpy(numpy.str)],
#                          'TubeTemp': [ascii.convert_numpy(numpy.float)],
#                          'FocusPos': [ascii.convert_numpy(numpy.int)],
#                          'SkyTemp': [ascii.convert_numpy(numpy.float)],
#                          'OutsideTemp': [ascii.convert_numpy(numpy.float)],
#                          'WindSpeed': [ascii.convert_numpy(numpy.float)],
#                          'Humidity': [ascii.convert_numpy(numpy.int)],
#                          'DewPoint': [ascii.convert_numpy(numpy.float)],
#                          'Altitude': [ascii.convert_numpy(numpy.float)],
#                          'Azimuth': [ascii.convert_numpy(numpy.float)],
#                          'Condition': [ascii.convert_numpy(numpy.str)]
#                          }
#                          )
            with open(logfile, 'r') as FO:
                env_table = FO.readlines()

            for line in env_table:
                if line[0] != '#':
                    try:
                        entry = line.split()
                        new_data = {}
                        ## Date and Time
                        dto_utc = dt.strptime('{} {}'.format(entry[0], entry[1]), '%Y/%m/%d %H:%M:%SUT')
                        dto_hst = dto_utc - tdelta(0, 10*60*60)
                        new_data.update({'UT date': dto_utc.strftime('%Y%m%dUT'),\
                                         'UT time': dto_utc.strftime("%H:%M:%S"),\
                                         'UT timestamp': dto_utc})
                        ## Define Boltwood Data
                        boltwood = {}
                        boltwood['boltwood date'] = dto_hst.strftime('%Y-%m-%d')  # local date (yyyy-mm-dd)
                        boltwood['boltwood time'] = dto_hst.strftime("%H:%M:%S.00")  # local time (hh:mm:ss.ss)
                        boltwood['boltwood timestamp'] = dto_hst
                        boltwood['boltwood temp units'] = 'F'
                        boltwood['boltwood wind units'] = 'K'
                        boltwood['boltwood sky temp'] = float(entry[4])
                        boltwood['boltwood ambient temp'] = float(entry[5])
                        boltwood['boltwood wind speed'] = float(entry[6])
                        boltwood['boltwood humidity'] = int(entry[7])
                        boltwood['boltwood dew point'] = float(entry[8])
                        boltwood['boltwood rain condition'] = int(entry[11][0])
                        boltwood['boltwood cloud condition'] = int(entry[11][1])
                        boltwood['boltwood wind condition'] = int(entry[11][2])
                        new_data.update(boltwood)
                    except:
                        print(line)
                        print(entry)
                        raise

                    ##-------------------------------------------------------------------------
                    ## Write Environmental Log
                    ##-------------------------------------------------------------------------
                    ## Check if this image is already in the collection
                    matches = [item for item in V5status.find( {"UT timestamp" : new_data['UT timestamp']} )]
                    if len(matches) > 0:
                        logger.debug('    Found {} previous entries for {} {}.  Deleting old entries.'.format(\
                                       len(matches), new_data['UT date'], new_data['UT time']))
                        for match in matches:
                            logger.debug('    Removing entry for {} {}'.format(match["UT date"], match["UT time"]))
                            V5status.remove( {"_id" : match["_id"]} )
                            logger.debug('    Removed "_id": {}'.format(match["_id"]))

                    id = V5status.insert(new_data)
                    logger.info('    Inserted datum for {} on {} {}'.format(\
                                   telescope, new_data['UT date'], new_data['UT time']))
        make_nightly_plots.make_plots(date_string, 'V5', logger)


        ## VYSOS-20
        telescope = 'V20'
        logfile = os.path.join('/', 'Volumes', 'Drobo', telescope, 'Logs', date_string, 'EnvironmentalLog.txt')
        if not os.path.exists(logfile):
            logger.warning('  No logfile found for {} on {}'.format(telescope, date_string))
        else:
            logger.info('  Found logfile: {}'.format(logfile))

#             ColStarts = [ 0, 11, 22, 32, 42, 52, 62, 72, 82,  92, 102, 112, 122, 132, 142, 152, 162]
#             ColEnds   = [ 9, 20, 31, 41, 51, 61, 71, 81, 91, 101, 111, 121, 131, 141, 151, 161, 171]
#             ColNames  = ['Date', 'TimeString', 'TubeTemp', 'PrimaryTemp', 'SecTemp', 'FanPower', 'FocusPos',
#                          'SkyTemp', 'OutsideTemp', 'WindSpeed', 'Humidity', 'DewPoint', 'Altitude', 'Azimuth',
#                          'Condition', 'DomeTemp', 'DomeFanState']
#             env_table = ascii.read(logfile, data_start=2, Reader=ascii.FixedWidth,
#                           col_starts=ColStarts, col_ends=ColEnds, names=ColNames,
#                           guess=False, comment=";", header_start=0,
#                           converters={
#                           'Date': [ascii.convert_numpy('S10')],
#                           'TimeString': [ascii.convert_numpy('S10')],
#                           'TubeTemp': [ascii.convert_numpy('f4')],
#                           'SecTemp': [ascii.convert_numpy('f4')],
#                           'FanPower': [ascii.convert_numpy('f4')],
#                           'FocusPos': [ascii.convert_numpy('i4')],
#                           'SkyTemp': [ascii.convert_numpy('f4')],
#                           'OutsideTemp': [ascii.convert_numpy('f4')],
#                           'WindSpeed': [ascii.convert_numpy('f4')],
#                           'Humidity': [ascii.convert_numpy('i4')],
#                           'DewPoint': [ascii.convert_numpy('f4')],
#                           'Altitude': [ascii.convert_numpy('f4')],
#                           'Azimuth': [ascii.convert_numpy('f4')],
#                           'Condition': [ascii.convert_numpy('S3')],
#                           'DomeTemp': [ascii.convert_numpy('f4')],
#                           'DomeFanState': [ascii.convert_numpy('i4')]
#                           }
#                           )

            with open(logfile, 'r') as FO:
                env_table = FO.readlines()

            for line in env_table:
                if line[0] != '#':
                    try:
                        entry = line.split()
                        new_data = {}
                        ## Date and Time
                        dto_utc = dt.strptime('{} {}'.format(entry[0], entry[1]), '%Y/%m/%d %H:%M:%SUT')
                        dto_hst = dto_utc - tdelta(0, 10*60*60)
                        new_data.update({'UT date': dto_utc.strftime('%Y%m%dUT'),\
                                         'UT time': dto_utc.strftime("%H:%M:%S"),\
                                         'UT timestamp': dto_utc})
                        ## Define Boltwood Data
                        boltwood = {}
                        boltwood['boltwood date'] = dto_hst.strftime('%Y-%m-%d')  # local date (yyyy-mm-dd)
                        boltwood['boltwood time'] = dto_hst.strftime("%H:%M:%S.00")  # local time (hh:mm:ss.ss)
                        boltwood['boltwood timestamp'] = dto_hst
                        boltwood['boltwood temp units'] = 'F'
                        boltwood['boltwood wind units'] = 'K'
                        boltwood['boltwood sky temp'] = float(entry[7])
                        boltwood['boltwood ambient temp'] = float(entry[8])
                        boltwood['boltwood wind speed'] = float(entry[9])
                        boltwood['boltwood humidity'] = int(entry[10])
                        boltwood['boltwood dew point'] = float(entry[11])
                        boltwood['boltwood rain condition'] = int(entry[14][0])
                        boltwood['boltwood cloud condition'] = int(entry[14][1])
                        boltwood['boltwood wind condition'] = int(entry[14][2])
                        new_data.update(boltwood)
                        ## Define Focuser Data
                        focuser_info = {}
                        focuser_info['RCOS temperature units'] = 'F'
                        focuser_info['RCOS temperature (truss)'] = float(entry[2])
                        focuser_info['RCOS temperature (primary)'] = float(entry[3])
                        focuser_info['RCOS temperature (secondary)'] = float(entry[4])
                        focuser_info['RCOS fan speed'] = int(entry[5])
                        focuser_info['RCOS focuser position'] = int(entry[6])
                        new_data.update(focuser_info)
                    except:
                        print(entry)
                        raise

                    ##-------------------------------------------------------------------------
                    ## Write Environmental Log
                    ##-------------------------------------------------------------------------
                    ## Check if this image is already in the collection
                    matches = [item for item in V20status.find( {"UT timestamp" : new_data['UT timestamp']} )]
                    if len(matches) > 0:
                        logger.debug('    Found {} previous entries for {} {}.  Deleting old entries.'.format(\
                                       len(matches), new_data['UT date'], new_data['UT time']))
                        for match in matches:
                            logger.debug('    Removing entry for {} {}'.format(match["UT date"], match["UT time"]))
                            V20status.remove( {"_id" : match["_id"]} )
                            logger.debug('    Removed "_id": {}'.format(match["_id"]))

                    id = V20status.insert(new_data)
                    logger.info('    Inserted datum for {} on {} {}'.format(\
                                   telescope, new_data['UT date'], new_data['UT time']))

        make_nightly_plots.make_plots(date_string, 'V20', logger)

        date += oneday



if __name__ == "__main__":
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    ## add arguments
    parser.add_argument("-s", "--start", 
        dest="start", required=True, type=str,
        help="UT date of first night to analyze. (i.e. '20130805UT')")
    parser.add_argument("-e", "--end", 
        dest="end", required=True, type=str,
        help="UT date of last night to analyze. (i.e. '20130805UT')")
    args = parser.parse_args()

    ##-------------------------------------------------------------------------
    ## Create Logger Object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('process_dates')
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
    LogFilePath = os.path.expanduser('~')
    if not os.path.exists(LogFilePath):
        os.mkdir(LogFilePath)
    LogFile = os.path.join(LogFilePath, 'migrate_envlog.log')
    LogFileHandler = logging.FileHandler(LogFile)
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)

    startdate = dt.strptime(args.start, '%Y%m%dUT')
    enddate = dt.strptime(args.end, '%Y%m%dUT')

    main(startdate, enddate, logger)
