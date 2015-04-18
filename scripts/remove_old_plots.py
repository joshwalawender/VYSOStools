#!/usr/env/python
'''
This script cleans up the IQMon directories where the Logs, Plots, and temporary
files are kept.  This deletes old files so that data products which are easily
reproduced don't fill up the drive.
'''

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
    LogFileName = os.path.join('/', 'var', 'www', 'logs', 'CleanupLog.txt')
    LogFileHandler = logging.FileHandler(LogFileName)
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)

    V5 = IQMon.Telescope(os.path.expanduser('~/.V5.yaml'))
    V20 = IQMon.Telescope(os.path.expanduser('~/.V20.yaml'))
    telescopes = [V5, V20]

    days_to_keep = 60

    ##-------------------------------------------------------------------------
    ## Remove old files from Plots directory
    ##-------------------------------------------------------------------------
    for tel in telescopes:
        logger.info('Examining {} for files that are {} days old.'.format(\
                    tel.plot_file_path, days_to_keep))
        now = datetime.datetime.today()
        files = glob.glob(os.path.join(tel.plot_file_path, '*'))
        n_removed = 0
        for file in files:
            file_mod = datetime.datetime.fromtimestamp(os.stat(file).st_mtime)
            age = now - file_mod
            if age.days >= days_to_keep:
                n_removed += 1
                os.remove(file)
        logger.info('  Removed {} files from Plots directory.'.format(n_removed))




if __name__ == '__main__':
    main()
