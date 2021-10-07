#!/usr/env/python

## Import General Tools
from pathlib import Path
import sys
import os
from os.path import join, exists, expanduser
import argparse
import logging
import datetime
import glob
import shutil
import subprocess
import re

import numpy as np
from astropy.io import fits



##-------------------------------------------------------------------------
## Copy Data
##-------------------------------------------------------------------------
def copy_data(date, tel, verbose=False, run=True):

    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('DataHandler_{}_{}'.format(tel, date))
    logger.setLevel(logging.DEBUG)
    ## Set up console output
    LogConsoleHandler = logging.StreamHandler()
    if args.verbose:
        LogConsoleHandler.setLevel(logging.DEBUG)
    else:
        LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(asctime)s %(levelname)8s: %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)
    ## Set up file output
    LogFileName = 'DataHandler_{}_{}.log'.format(tel, date)
    LogFilePath = join('/', 'Users', 'vysosuser', 'logs')
    LogFileHandler = logging.FileHandler(join(LogFilePath, LogFileName))
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)


    ##-------------------------------------------------------------------------
    ## Copy Data from Source to Destination and make second copy
    ##-------------------------------------------------------------------------
    subdirs = ['Images', 'Logs']
    for subdir in subdirs:
        path = None
        files = []
        source_path = join(expanduser('~vysosuser'), f"{tel}Data", subdir, date)
        logger.info(f"Checking for files in {source_path}")
        dest_paths = [join('/', 'Volumes', 'VYSOSData', tel, subdir, date[0:4], date)]

        nfiles = 0
        ndirs = 0
        for entry in os.walk(source_path):
            path = entry[0]
            files = entry[2]
            logger.info(f"  Found {len(files)} in {path}")
            ndirs += 1
            nfiles += len(files)
        logger.info(f"Found a total of {nfiles} files in {ndirs} directories")

        filecount = 0
        for entry in os.walk(source_path):
            path = entry[0]
            files = entry[2]
            logger.info(f"  Handling {len(files)} in {path}")
            for file in files:
                filecount += 1
                logger.info(f"Checking source {filecount} of {nfiles}: {join(path, file)}")
                ok2del = [False]*len(dest_paths)
                for i,dest_path in enumerate(dest_paths):
                    destination = path.replace(source_path, dest_path)
                    dest_file = join(destination, file)
                    logger.info(f"  Checking Destination: {destination}")
                    if not os.path.exists(destination):
                        try:
                            logger.info(f'mkdir {destination}')
#                             if run: os.mkdir(destination)
                            if run:
                                p = Path(destination)
                                p.mkdir(parents=True, exist_ok=True)
                        except PermissionError as e:
                            logger.error(e)
                            raise
                        except FileExistsError as e:
                            logger.warning(e)
                        except:
                            if run:
                                logger.info(f'mkdir {os.path.split(destination)[0]}')
                                os.mkdir(os.path.split(destination)[0])
                                logger.info(f'mkdir {destination}')
                                os.mkdir(destination)
                    if run: assert os.path.exists(destination)
                    fileext = os.path.splitext(file)[1]
                    
                    # Handle FITS files
                    if fileext in ['.fts', '.fits']:
                        source_fz = f'{file}.fz'
                        dest_fz = f'{dest_file}.fz'


                        if not exists(dest_file) and not exists(dest_fz):
                            logger.info(f'    File does not exist on {dest_path}. Writing file.')
                            if run:
                                with fits.open(join(path, file), checksum=True) as hdul:
                                    hdul[0].add_checksum()
                                    hdul.writeto(dest_file, checksum=True)
                        if exists(dest_file) and not exists(dest_fz):
                            logger.debug(f'    Compressing file: {dest_file}')
                            if run:
                                subprocess.call(['fpack', dest_file])
                                if exists(dest_fz):
                                    os.remove(dest_file)
                        if exists(dest_fz):
                            logger.debug(f'    File {os.path.split(dest_fz)[1]} exists on {dest_path}')
                            if run:
                                failcheck = bool(subprocess.call(['fitscheck', dest_fz]))
                                if failcheck is True:
                                    logger.error("    Checksum Failed")
                                else:
                                    logger.info("    Checksum Passed")
                                ok2del[i] = not failcheck
                            else:
                                ok2del[i] = True
                    # Handle non-FITS files
                    else:
                        if not exists(dest_file):
                            logger.info(f'    Copying {file} to {destination}')
                            if run: shutil.copy2(join(path, file), dest_file)
                        if os.path.exists(dest_file) or not run:
                            ok2del[i] = True
                if args.delete and np.all(ok2del):
                    logger.info(f'  Deleting {file}')
                    if run: os.remove(join(path, file))
            if args.delete:
                if len(glob.glob(join(path, '*'))) == 0:
                    logger.info('Removing {}'.format(path))
                    if run: os.rmdir(path)
                else:
                    logger.warning(f'Files still remain in {path}')
        if args.delete:
            if run:
                try:
                    os.rmdir(source_path)
                    logger.info('Final rmdir {}'.format(source_path))
                except FileNotFoundError:
                    pass


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
    parser.add_argument("--delete",
        action="store_true", dest="delete",
        default=False, help="Delete the file after confirmation of SHA sum?")
    ## add arguments
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    parser.add_argument("-d", "--date",
        type=str, dest="date",
        help="The date to copy.")
    args = parser.parse_args()

    if args.date is not None:
        if re.match('\d{8}UT', args.date):
            date = args.date
        elif args.date == 'yesterday':
            today = datetime.datetime.utcnow()
            oneday = datetime.timedelta(1, 0)
            date = (today - oneday).strftime('%Y%m%dUT')
        else:
            print(f'Could not parse "{args.date}"')
    else:
        date = datetime.datetime.utcnow().strftime('%Y%m%dUT')

    copy_data(date, args.telescope, verbose=args.verbose)
