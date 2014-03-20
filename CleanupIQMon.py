#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import datetime
import glob

import IQMon


##-------------------------------------------------------------------------
## Main Program
##-------------------------------------------------------------------------
def main():

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
    parser.add_argument("--input",
        type=str, dest="input",
        help="The input.")
    args = parser.parse_args()

    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('MyLogger')
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
    LogFileName = os.path.join('/', 'Users', 'vysosuser', 'IQMon', 'Logs', 'CleanupLog.txt')
    LogFileHandler = logging.FileHandler(LogFileName)
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)


    ##-------------------------------------------------------------------------
    ## Remove old files from Plots directory
    ##-------------------------------------------------------------------------
    config = IQMon.Config()
    days_to_keep = 60
    logger.info('Examining {} for files that are {} days old.'.format(config.pathPlots, days_to_keep))
    now = datetime.datetime.utcnow()
    delta_days = datetime.timedelta(days_to_keep)
    then = now - delta_days
    ThenString = then.strftime("%Y%m%d")
    file_pattern = 'V*'+ThenString+'at*jpg'
    logger.info('  Looking for files with filename matching {}'.format(file_pattern))
    files = glob.glob(os.path.join(config.pathPlots, file_pattern))
    logger.info('  Found {} files to remove.'.format(len(files)))
    for file in files:
        os.remove(file)
    logger.info('  Removed {} files.'.format(len(files)))


    ##-------------------------------------------------------------------------
    ## Remove old files from tmp directory
    ##-------------------------------------------------------------------------
    tmp_days_to_keep = 1
    logger.info('Examining {} for files that are {} days old.'.format(config.pathTemp, tmp_days_to_keep))
    tmp_files = glob.glob(os.path.join(config.pathTemp, '*'))
    for tmp_file in tmp_files:
        file_mod = datetime.datetime.fromtimestamp(os.stat(tmp_file).st_mtime)
        now = datetime.datetime.today()
        age = now - file_mod
        if age.days >= tmp_days_to_keep:
            logger.debug('  Removing {}'.format(tmp_file))
            os.remove(tmp_file)




if __name__ == '__main__':
    main()
