#!/usr/bin/env python
# encoding: utf-8
"""
Script to watch a directory of images and when a new one appears, run
MeasureImage.py on it.
"""

from __future__ import division, print_function

import sys
import os
from argparse import ArgumentParser
import re
import time
from datetime import datetime as dt
import pymongo
from pymongo import MongoClient
import logging

from astropy import units as u
from astropy.io import fits

from VYSOS import Telescope
from measure_image import measure_image


def main():
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
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    args = parser.parse_args()
    telescope = args.telescope

    ##-------------------------------------------------------------------------
    ## Create Logger Object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('watch_directory')
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
    LogFileName = 'watch_directory.txt'
    LogFile = os.path.join('/', 'var', 'www', 'logs', telescope, LogFileName)
    LogFileHandler = logging.FileHandler(LogFile)
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)

    ##-------------------------------------------------------------------------
    ## Telescope Configuration
    ##-------------------------------------------------------------------------
    tel = Telescope(telescope)
    client = MongoClient(tel.mongo_address, tel.mongo_port)
    db = client[tel.mongo_db]
    images = db[tel.mongo_collection]

    ##-------------------------------------------------------------------------
    ## Operation Loop
    ##-------------------------------------------------------------------------
    Operate = True
#     MatchFilename = re.compile("(.*)\-([0-9]{8})at([0-9]{6})\.fts")
    MatchFilename = re.compile("(.*)\.fts")
    MatchEmpty = re.compile(".*\-Empty\-.*\.fts")
    while Operate:
        ## Set date to tonight
        now = dt.utcnow()
        date_string = now.strftime("%Y%m%dUT")
        DataPath = os.path.join(os.path.expanduser("~"), f"{args.telescope}Data", "Images", date_string)
        
        logger.info('Examining directory {}'.format(DataPath))
        ## Look for files
        if os.path.exists(DataPath):
            files = os.listdir(DataPath)
        else:
            files = []
        logger.info('  Found {} files'.format(len(files)))
        time.sleep(1)
        images_to_analyze = {}
        for file in files:
            IsMatch = MatchFilename.match(file)
            IsEmpty = MatchEmpty.match(file)
            if IsMatch and not IsEmpty:
                analyzed = [x for x in images.find( {"filename" : file} )]
                if (len(analyzed) == 0):
                    target = IsMatch.group(1)
#                     filetime = IsMatch.group(3)
                    hdr = fits.getheader(os.path.join(DataPath, file))
                    DATEOBS = hdr.get('DATEOBS', '')
                    filetime = DATEOBS.replace('-', '').replace(':', '').replace('T', 'at')
                    images_to_analyze[filetime] = file
        logger.debug('  Found {} files to analyze'.format(len(images_to_analyze)))
        for filetime in sorted(images_to_analyze.keys()):
            file = images_to_analyze[filetime]
            try:
                measure_image(os.path.join(DataPath, file), nographics=True)
            except OSError:
                raise
            except:
                logger.warning('  MeasureImage failed on {}.'.format(file))
                logger.error(sys.exc_info())

        time.sleep(30)


if __name__ == "__main__":
    main()
