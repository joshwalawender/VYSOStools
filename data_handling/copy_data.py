#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
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

from astropy.io import fits

##-------------------------------------------------------------------------
## Copy Data
##-------------------------------------------------------------------------
def copy_data(date, telescope, verbose=False):

    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('DataHandler_{}_{}'.format(telescope, date))
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
    LogFileName = 'DataHandler_{}_{}.log'.format(telescope, date)
    LogFilePath = join('/', 'Users', 'vysosuser', 'logs')
    LogFileHandler = logging.FileHandler(join(LogFilePath, LogFileName))
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)



    ##-------------------------------------------------------------------------
    ## Copy Data from Source to Destination and make second copy
    ##-------------------------------------------------------------------------
    source_path = join(expanduser('~vysosuser'), f"{telescope}Data")

    dest_path = join('/', 'Volumes', 'MLOData', telescope)
    assert exists(join(dest_path, 'Images'))
    assert exists(join(dest_path, 'Logs'))
    if not exists(join(dest_path, 'Images', date[0:4])):
        logger.info(f"Making directory: {join(dest_path, 'Images', date[0:4])}")
        os.mkdir(join(dest_path, 'Images', date[0:4]))
    if not exists(join(dest_path, 'Logs', date[0:4])):
        logger.info(f"Making directory: {join(dest_path, 'Logs', date[0:4])}")
        os.mkdir(join(dest_path, 'Logs', date[0:4]))
    dest_path_images = join(dest_path, 'Images', date[0:4], date)
    dest_path_logs = join(dest_path, 'Logs', date[0:4], date)

    copy_path = join('/', 'Volumes', 'DataCopy', telescope)
    assert exists(join(copy_path, 'Images'))
    assert exists(join(copy_path, 'Logs'))
    if not exists(join(copy_path, 'Images', date[0:4])):
        logger.info(f"Making directory: {join(copy_path, 'Images', date[0:4])}")
        os.mkdir(join(copy_path, 'Images', date[0:4]))
    if not exists(join(copy_path, 'Logs', date[0:4])):
        logger.info(f"Making directory: {join(copy_path, 'Logs', date[0:4])}")
        os.mkdir(join(copy_path, 'Logs', date[0:4]))
    copy_path_images = join(copy_path, 'Images', date[0:4], date)
    copy_path_logs = join(copy_path, 'Logs', date[0:4], date)

    ## Check that date directory has been made on Destination
    if not exists(dest_path_images):
        logger.info(f"Making directory: {dest_path_images}")
        os.mkdir(dest_path_images)
    if not exists(dest_path_logs):
        logger.info(f"Making directory: {dest_path_logs}")
        os.mkdir(dest_path_logs)

    ## Check that date directory has been made on copy
    if not exists(copy_path_images):
        logger.info(f"Making directory: {copy_path_images}")
        os.mkdir(copy_path_images)
    if not exists(copy_path_logs):
        logger.info(f"Making directory: {copy_path_logs}")
        os.mkdir(copy_path_logs)

    ## Make list of files to analyze
    files = glob.glob(join(source_path, 'Images', date, '*.*'))
    if exists(join(source_path, 'Images', date, 'Calibration')):
        files.extend(glob.glob(join(source_path, 'Images', date, 'Calibration', '*.*')))
        if not exists(join(dest_path_images, 'Calibration')):
            os.mkdir(join(dest_path_images, 'Calibration'))
        if not exists(join(copy_path_images, 'Calibration')):
            os.mkdir(join(copy_path_images, 'Calibration'))
    if exists(join(source_path, 'Images', date, 'AutoFlat')):
        files.extend(glob.glob(join(source_path, 'Images', date, 'AutoFlat', '*.*')))
        if not exists(join(dest_path_images, 'AutoFlat')):
            os.mkdir(join(dest_path_images, 'AutoFlat'))
        if not exists(join(copy_path_images, 'AutoFlat')):
            os.mkdir(join(copy_path_images, 'AutoFlat'))
    files.extend(glob.glob(join(source_path, 'Logs', date, '*.*')))
    logger.info('Found {} files to analyze'.format(len(files)))

    # Loop over all files
    for i,file in enumerate(files):
        filename = os.path.split(file)[1]
        fileext = os.path.splitext(filename)[1]
        logger.info('Checking file {}/{}: {}'.format(i+1, len(files), filename))

        if fileext in ['.fts', '.fz', '.fits']:
            dest_file = join(dest_path_images, filename)
            copy_file = join(copy_path_images, filename)
            logger.debug(f"Destination file: {dest_file}")
            logger.debug(f"Copy file: {copy_file}")

            dest_fz = '{}.fz'.format(dest_file)
            copy_fz = '{}.fz'.format(copy_file)
            logger.debug(f"Destination fz file: {dest_fz}")
            logger.debug(f"Copy fz file: {copy_fz}")

            to_dest = False
            if exists(dest_path):
                if not exists(dest_file) and not exists(dest_fz):
                    to_dest=True
                elif exists(dest_file) and not exists(dest_fz):
                    logger.info('  Compressing existing file on drobo')
                    subprocess.call(['fpack', dest_file])
                    if exists(dest_fz):
                        os.remove(dest_file)

            to_ext = False
            if exists(copy_path):
                if not exists(copy_file) and not exists(copy_fz):
                    to_ext=True
                elif exists(copy_file) and not exists(copy_fz):
                    logger.info('  Compressing existing file on ext')
                    subprocess.call(['fpack', copy_file])
                    if exists(copy_fz):
                        os.remove(copy_file)

            if to_dest or to_ext:
                with fits.open(file, checksum=True) as hdul:
                    hdul[0].add_checksum()
                    if to_dest:
                        logger.info('  File does not exist on drobo.  Writing compressed file.')
                        hdul.writeto(dest_file, checksum=True)
                        subprocess.call(['fpack', dest_file])
                        if exists(dest_fz):
                            os.remove(dest_file)
                    if to_ext:
                        logger.info('  File does not exist on copy.  Writing compressed file.')
                        hdul.writeto(copy_file, checksum=True)
                        subprocess.call(['fpack', copy_file])
                        if exists(copy_fz):
                            os.remove(copy_file)
            # Verify checksums on drobo
            failcheck_drobo = bool(subprocess.call(['fitscheck', dest_fz]))
            if failcheck_drobo:
                logger.warning('Checksum failed on {}'.format(dest_fz))
            # Verify checksums on ext
            failcheck_ext = bool(subprocess.call(['fitscheck', copy_fz]))
            if failcheck_ext:
                logger.warning('Checksum failed on {}'.format(copy_fz))

            if not failcheck_drobo and not failcheck_ext:
                if args.delete:
                    logger.info('  All CHECKSUM verifications passed.  Deleting file.')
                    os.remove(file)
                else:
                    logger.info('  All CHECKSUM verifications passed.')

        ## No checksum verification for non-FITS files
        elif fileext in ['.txt', '.log']:
            dest_file = join(dest_path_logs, filename)
            copy_file = join(copy_path_logs, filename)

            if not exists(dest_file):
                logger.info('Copying {} to drobo'.format(file))
                shutil.copy2(file, dest_file)
            if not exists(copy_file):
                logger.info('Copying {} to external'.format(file))
                shutil.copy2(file, dest_file)
            if args.delete and exists(copy_path) and exists(dest_path):
                logger.info('Deleting {}'.format(file))
                os.remove(file)

    if args.delete:
        ## Remove Calibration directory if empty
        Calibration_path = join(source_path, 'Images', date, 'Calibration')
        if exists(Calibration_path):
            if len(glob.glob(join(Calibration_path, '*'))) == 0:
                logger.info('Removing {}'.format(Calibration_path))
                os.rmdir(Calibration_path)
            else:
                logger.warning('Files still remain in {}'.format(Calibration_path))

        ## Remove AutoFlat directory if empty
        AutoFlat_path = join(source_path, 'Images', date, 'AutoFlat')
        if exists(AutoFlat_path):
            if len(glob.glob(join(AutoFlat_path, '*'))) == 0:
                logger.info('Removing {}'.format(AutoFlat_path))
                os.rmdir(AutoFlat_path)
            else:
                logger.warning('Files still remain in {}'.format(AutoFlat_path))

        ## Remove Images directory if empty
        Images_path = join(source_path, 'Images', date)
        if exists(Images_path):
            if len(glob.glob(join(Images_path, '*'))) == 0:
                logger.info('Removing {}'.format(Images_path))
                os.rmdir(Images_path)
            else:
                logger.warning('Files still remain in {}'.format(Images_path))

        ## Remove Logs directory if empty
        Logs_path = join(source_path, 'Logs', date)
        if exists(Logs_path):
            if len(glob.glob(join(Logs_path, '*'))) == 0:
                logger.info('Removing {}'.format(Logs_path))
                os.rmdir(Logs_path)
            else:
                logger.warning('Files still remain in {}'.format(Logs_path))


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
