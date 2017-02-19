import sys
import os
import re
import logging
import time
from glob import glob
from datetime import datetime as dt
from datetime import timedelta as tdelta
from argparse import ArgumentParser
import subprocess
import ephem
import pymongo
from pymongo import MongoClient

import measure_image
import make_nightly_plots

import IQMon

def main(startdate, enddate, logger, nice=False, skip=False):
    if startdate > enddate:
        oneday = tdelta(-1, 0)
    else:
        oneday = tdelta(1, 0)

    ##------------------------------------------------------------------------
    ## Use pyephem determine sunrise and sunset times
    ##------------------------------------------------------------------------
    now = dt.utcnow()
    if nice:
        Observatory = ephem.Observer()
        Observatory.lon = "-155:34:33.9"
        Observatory.lat = "+19:32:09.66"
        Observatory.elevation = 3400.0
        Observatory.temp = 10.0
        Observatory.pressure = 680.0
        Observatory.horizon = '0.0'
        Observatory.date = now.strftime('%Y/%m/%d %H:%M:%S')
        TheSun = ephem.Sun()

    MatchFilename = re.compile("(.*)\-([0-9]{8})at([0-9]{6})\.fts")
    MatchEmpty = re.compile(".*\-Empty\-.*\.fts")

    date = startdate
    while True:
        date_string = date.strftime('%Y%m%dUT')
        logger.info('Checking for images from {}'.format(date_string))
        images = []
        V5_path = os.path.join("/Volumes", "Drobo", "V5", "Images", date_string)
        V20_path = os.path.join("/Volumes", "Drobo", "V20", "Images", date_string)
        if os.path.exists(V5_path):
            V5_images = glob(os.path.join(V5_path, '*.fts'))
            logger.info('  Found {} images for the night of {} for V5'.format(\
                        len(V5_images), date_string))
            images.extend(V5_images)
        if os.path.exists(V20_path):
            V20_images = glob(os.path.join(V20_path, '*.fts'))
            logger.info('  Found {} images for the night of {} for V20'.format(\
                        len(V20_images), date_string))
            images.extend(V20_images)
        ## Sort Images by Observation time
        properties = []
        for image in images:
            skip_this_image = False
            imagename = os.path.split(image)[1]
            FNmatch = MatchFilename.match(imagename)
            Ematch = MatchEmpty.match(imagename)
            ## If skip is enabled, skip images which are already in mongo db
            if skip:
                telescope = None
                V5match = re.match("V5.*\.fi?ts", imagename)
                V20match = re.match("V20.*\.fi?ts", imagename)
                if V5match and not V20match:
                    telescope = "V5"
                elif V20match and not V5match:
                    telescope = "V20"
                else:
                    with fits.open(image) as hdulist:
                        if hdulist[0].header['OBSERVAT']:
                            if re.search('VYSOS-?20', hdulist[0].header['OBSERVAT']):
                                telescope = "V20"
                            elif re.search('VYSOS-?5', hdulist[0].header['OBSERVAT']):
                                telescope = "V5"
                            else:
                                print("Can not determine valid telescope from arguments or filename or header.")
                        else:
                            print("Can not determine valid telescope from arguments or filename or header.")
                if telescope:
                    config_file = os.path.join(os.path.expanduser('~'), '.{}.yaml'.format(telescope))
                    tel = IQMon.Telescope(config_file)
                    client = MongoClient(tel.mongo_address, tel.mongo_port)
                    db = client[tel.mongo_db]
                    data = db[tel.mongo_collection]
                    matches = [item for item in data.find( {"filename" : imagename} )]
                    if len(matches) > 0:
#                         images.remove(image)
                        skip_this_image = True
            ## Remove images with Empty in filenme
            if Ematch:
#                 images.remove(image)
                skip_this_image = True

            if not FNmatch:
#                 images.remove(image)
                skip_this_image = True

            if not skip_this_image:
                try:
                    image_dt = dt.strptime('{} {}'.format(\
                       FNmatch.group(2), FNmatch.group(3)), '%Y%m%d %H%M%S')
                except:
                    image_dt = dt.utcnow()
                properties.append([image, image_dt])
        properties = sorted(properties, key=lambda entry:entry[1])
        ## Process Images
        count = 0
        for entry in properties:
            count += 1
            print('')
            print('Examining image {} out of {} for the night of {}'.format(\
                   count, len(properties), date_string))
            image = entry[0]
            if nice:
                now = dt.utcnow()
                Observatory.date = now.strftime('%Y/%m/%d %H:%M:%S')
                TheSun.compute(Observatory)
                if TheSun.alt < 0:
                    print('The Sun is down (alt = {:.1f})'.format(TheSun.alt*180./ephem.pi))
                    sunrise = Observatory.next_rising(TheSun).datetime()
                    until_sunrise = (sunrise - now).total_seconds()/60./60.
                    logger.info('Sleeping {:.1f} hours until sunrise'.format(until_sunrise))
                    time.sleep(until_sunrise + 300)
                    now = dt.utcnow()
                    Observatory.date = now.strftime('%Y/%m/%d %H:%M:%S')
                    sunset  = Observatory.next_setting(ephem.Sun()).datetime()
                    sunrise = Observatory.next_rising(ephem.Sun()).datetime()
                    logger.info('Resuming processing ...')
                    logger.info('  Next sunset at {}'.format(sunset.strftime('%Y/%m/%d %H:%M:%S')))
            if MatchFilename.match(image) and not MatchEmpty.match(image):
                try:
                    measure_image.MeasureImage(image,\
                                 clobber_logs=True,\
                                 zero_point=True,\
                                 analyze_image=True)
                except:
                    logger.warning('MeasureImage failed on {}'.format(image))
                    measure_image.MeasureImage(image,\
                                 clobber_logs=False,\
                                 zero_point=True,\
                                 analyze_image=False)
        make_nightly_plots.make_plots(date_string, 'V5', logger)
        make_nightly_plots.make_plots(date_string, 'V20', logger)
        if date == enddate:
            break
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
    parser.add_argument("--nice",
        action="store_true", dest="nice",
        default=False, help="Be nice by not processing data at night.")
    parser.add_argument("--skip",
        action="store_true", dest="skip",
        default=False, help="Skip images already in mongo db.")
#     parser.add_argument("--revise",
#         action="store_true", dest="revise",
#         default=False, help="Reprocess images if IQMon version is newer.")
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
#     LogFilePath = os.path.join()
#     if not os.path.exists(LogFilePath):
#         os.mkdir(LogFilePath)
#     LogFile = os.path.join(LogFilePath, 'get_status.log')
#     LogFileHandler = logging.FileHandler(LogFile)
#     LogFileHandler.setLevel(logging.DEBUG)
#     LogFileHandler.setFormatter(LogFormat)
#     logger.addHandler(LogFileHandler)

    startdate = dt.strptime(args.start, '%Y%m%dUT')
    enddate = dt.strptime(args.end, '%Y%m%dUT')

    main(startdate, enddate, logger, nice=args.nice, skip=args.skip)
