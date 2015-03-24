import sys
import os
import re
import logging
from glob import glob
from datetime import datetime as dt
from datetime import timedelta as tdelta
from argparse import ArgumentParser
import subprocess

import measure_image
import make_nightly_plots

def main(startdate, enddate, logger):
    MatchFilename = re.compile("(.*)\-([0-9]{8})at([0-9]{6})\.fts")
    MatchEmpty = re.compile(".*\-Empty\-.*\.fts")
    oneday = tdelta(1, 0)
    now = startdate
    while now <= enddate:
        date_string = now.strftime('%Y%m%dUT')
        logger.info('Checking for images from {}'.format(date_string))
        images = []
        V5_path = os.path.join("/Volumes", "Drobo", "V5", "Images", date_string)
        V20_path = os.path.join("/Volumes", "Drobo", "V20", "Images", date_string)
        if os.path.exists(V5_path):
            V5_images = glob(os.path.join(V5_path, '*.fts'))
            logger.info('  Found {} images for the night of {} for V5'.format(len(V5_images), date_string))
            images.extend(V5_images)
        if os.path.exists(V20_path):
            V20_images = glob(os.path.join(V20_path, '*.fts'))
            logger.info('  Found {} images for the night of {} for V20'.format(len(V20_images), date_string))
            images.extend(V20_images)
        for image in images:
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
                                 zero_point=False,\
                                 analyze_image=False)
        make_nightly_plots.make_plots(date_string, 'V5', logger)
        make_nightly_plots.make_plots(date_string, 'V20', logger)
        now += oneday

    
    
    
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

    main(startdate, enddate, logger)
