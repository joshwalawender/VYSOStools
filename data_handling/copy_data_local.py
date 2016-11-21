#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
from os.path import exists
from os.path import join
import argparse
import logging
import datetime
import glob
import shutil
import subprocess
import re

from astropy.io import fits

##-------------------------------------------------------------------------
## Check Free Space on Drive
##-------------------------------------------------------------------------
def free_space(path):
    statvfs = os.statvfs(path)
    size_GB = statvfs.f_frsize * statvfs.f_blocks / 1024 / 1024 / 1024
    avail_GB = statvfs.f_frsize * statvfs.f_bfree / 1024 / 1024 / 1024
    pcnt_used = float(size_GB - avail_GB)/float(size_GB) * 100
    return (size_GB, avail_GB, pcnt_used)


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

    if args.date:
        if re.match('\d{8}UT', args.date):
            date = args.date
        elif args.date == 'yesterday':
            today = datetime.datetime.utcnow()
            oneday = datetime.timedelta(1, 0)
            date = (today - oneday).strftime('%Y%m%dUT')
    else:
        date = datetime.datetime.utcnow().strftime('%Y%m%dUT')

    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('DataHandler_{}_{}'.format(args.telescope, date))
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
    LogFileName = 'DataHandler_{}_{}.log'.format(args.telescope, date)
    LogFilePath = join('/', 'Users', 'vysosuser', 'logs')
    LogFileHandler = logging.FileHandler(join(LogFilePath, LogFileName))
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)



    ##-------------------------------------------------------------------------
    ## Copy Data from Windows Share to Drobo and USB Drive
    ##-------------------------------------------------------------------------
    windows_path = join('/', 'Volumes', 'Data_{}'.format(args.telescope))
    drobo_path = join('/', 'Volumes', 'Drobo', args.telescope)
    extdrive_paths = [join('/', 'Volumes', 'WD500B', args.telescope),\
                      join('/', 'Volumes', 'WD500_C', args.telescope)]
    if exists(extdrive_paths[0]):
        extdrive_path = extdrive_paths[0]
    elif exists(extdrive_paths[1]):
        extdrive_path = extdrive_paths[1]
    else:
        print("Can't find path for external drive")
        sys.exit(1)

    ## Check free space on Drobo
    threshold = 16383.7 - 3500 # True size of drobo is approx 3600 GB
    stats = free_space(drobo_path)
    logger.info('Disk usage on Drobo:')
    logger.info('  Size = {:.1f} GB'.format(stats[0]))
    logger.info('  Available = {:.2f} GB'.format(stats[1]))
    logger.info('  Percent Full = {:.1f} %'.format(stats[2]))
    if stats[1] < threshold:
        logger.warning('Disk {} is low on space'.format(drobo_path))
        copy_to_drobo = False
    else:
        copy_to_drobo = True
    ## Check that date directory has been made on Drobo
    if not exists(join(drobo_path, 'Images', date)):
        logger.info('Making directory: {}'.format(join(drobo_path, 'Images', date)))
        os.mkdir(join(drobo_path, 'Images', date))
    if not exists(join(drobo_path, 'Logs', date)):
        logger.info('Making directory: {}'.format(join(drobo_path, 'Logs', date)))
        os.mkdir(join(drobo_path, 'Logs', date))

    ## Check free space on external drive
    threshold = 20
    stats = free_space(extdrive_path)
    logger.info('Disk usage on {}:'.format(extdrive_path))
    logger.info('  Size = {:.1f} GB'.format(stats[0]))
    logger.info('  Available = {:.2f} GB'.format(stats[1]))
    logger.info('  Percent Full = {:.1f} %'.format(stats[2]))
    if stats[1] < threshold:
        logger.warning('Disk {} is low on space'.format(extdrive_path))
        copy_to_extdrive = False
    else:
        copy_to_extdrive = True

    ## Check that date directory has been made on external drive
    if not exists(join(extdrive_path, 'Images', date)):
        logger.info('Making directory: {}'.format(join(extdrive_path, 'Images', date)))
        os.mkdir(join(extdrive_path, 'Images', date))
    if not exists(join(extdrive_path, 'Logs', date)):
        logger.info('Making directory: {}'.format(join(extdrive_path, 'Logs', date)))
        os.mkdir(join(extdrive_path, 'Logs', date))

    ## Make list of files to analyze
    files = glob.glob(join(windows_path, 'Images', date, '*.*'))
    if exists(join(windows_path, 'Images', date, 'Calibration')):
        files.extend(glob.glob(join(windows_path, 'Images', date, 'Calibration', '*.*')))
        if not exists(join(drobo_path, 'Images', date, 'Calibration')):
            os.mkdir(join(drobo_path, 'Images', date, 'Calibration'))
        if not exists(join(extdrive_path, 'Images', date, 'Calibration')):
            os.mkdir(join(extdrive_path, 'Images', date, 'Calibration'))
    if exists(join(windows_path, 'Images', date, 'AutoFlat')):
        files.extend(glob.glob(join(windows_path, 'Images', date, 'AutoFlat', '*.*')))
        if not exists(join(drobo_path, 'Images', date, 'AutoFlat')):
            os.mkdir(join(drobo_path, 'Images', date, 'AutoFlat'))
        if not exists(join(extdrive_path, 'Images', date, 'AutoFlat')):
            os.mkdir(join(extdrive_path, 'Images', date, 'AutoFlat'))
    files.extend(glob.glob(join(windows_path, 'Logs', date, '*.*')))
    logger.info('Found {} files to analyze'.format(len(files)))

    # Loop over all files
    for i,file in enumerate(files):
        filename = os.path.split(file)[1]
        logger.info('Checking file {}/{}: {}'.format(i+1, len(files), filename))
        drobo_file = file.replace(windows_path, drobo_path)
        ext_file = file.replace(windows_path, extdrive_path)

        if os.path.splitext(file)[1] in ['.fits', '.fts']:
            drobo_fz = '{}.fz'.format(drobo_file)
            ext_fz = '{}.fz'.format(ext_file)

            to_drobo = False
            if copy_to_drobo:
                if not exists(drobo_file) and not exists(drobo_fz):
                    to_drobo=True
                elif exists(drobo_file) and not exists(drobo_fz):
                    logger.info('  Compressing existing file on drobo')
                    subprocess.call(['fpack', drobo_file])
                    if exists(drobo_fz):
                        os.remove(drobo_file)

            to_ext = False
            if copy_to_extdrive:
                if not exists(ext_file) and not exists(ext_fz):
                    to_ext=True
                elif exists(ext_file) and not exists(ext_fz):
                    logger.info('  Compressing existing file on ext')
                    subprocess.call(['fpack', ext_file])
                    if exists(ext_fz):
                        os.remove(ext_file)

            if to_drobo or to_ext:
                with fits.open(file, checksum=True) as hdul:
                    hdul[0].add_checksum()
                    if to_drobo:
                        logger.info('  File does not exist on drobo.  Writing compressed file.')
                        hdul.writeto(drobo_file, checksum=True)
                        subprocess.call(['fpack', drobo_file])
                        if exists(drobo_fz):
                            os.remove(drobo_file)
                    if to_ext:
                        logger.info('  File does not exist on external.  Writing compressed file.')
                        hdul.writeto(ext_file, checksum=True)
                        subprocess.call(['fpack', ext_file])
                        if exists(ext_fz):
                            os.remove(ext_file)
            # Verify checksums on drobo
            failcheck_drobo = bool(subprocess.call(['fitscheck', drobo_fz]))
            if failcheck_drobo:
                logger.warning('Checksum failed on {}'.format(drobo_fz))
            # Verify checksums on ext
            failcheck_ext = bool(subprocess.call(['fitscheck', ext_fz]))
            if failcheck_ext:
                logger.warning('Checksum failed on {}'.format(ext_fz))

            if not failcheck_drobo and not failcheck_ext:
                if args.delete:
                    logger.info('  All CHECKSUM verifications passed.  Deleting file.')
                    os.remove(file)
                else:
                    logger.info('  All CHECKSUM verifications passed.')

        ## No checksum verification for non-FITS files
        else:
            if not exists(drobo_file) and copy_to_drobo:
                logger.info('Copying {} to drobo'.format(file))
                shutil.copy2(file, drobo_file)
            if not exists(ext_file) and copy_to_extdrive:
                logger.info('Copying {} to external'.format(file))
                shutil.copy2(file, drobo_file)
            if args.delete and copy_to_extdrive and copy_to_drobo:
                logger.info('Deleting {}'.format(file))
                os.remove(file)

    if args.delete:
        ## Remove Calibration directory if empty
        Calibration_path = join(windows_path, 'Images', date, 'Calibration')
        if exists(Calibration_path):
            if len(glob.glob(join(Calibration_path, '*'))) == 0:
                logger.info('Removing {}'.format(Calibration_path))
                os.rmdir(Calibration_path)
            else:
                logger.warning('Files still remain in {}'.format(Calibration_path))

        ## Remove AutoFlat directory if empty
        AutoFlat_path = join(windows_path, 'Images', date, 'AutoFlat')
        if exists(AutoFlat_path):
            if len(glob.glob(join(AutoFlat_path, '*'))) == 0:
                logger.info('Removing {}'.format(AutoFlat_path))
                os.rmdir(AutoFlat_path)
            else:
                logger.warning('Files still remain in {}'.format(AutoFlat_path))

        ## Remove Images directory if empty
        Images_path = join(windows_path, 'Images', date)
        if exists(Images_path):
            if len(glob.glob(join(Images_path, '*'))) == 0:
                logger.info('Removing {}'.format(Images_path))
                os.rmdir(Images_path)
            else:
                logger.warning('Files still remain in {}'.format(Images_path))

        ## Remove Logs directory if empty
        Logs_path = join(windows_path, 'Logs', date)
        if exists(Logs_path):
            if len(glob.glob(join(Logs_path, '*'))) == 0:
                logger.info('Removing {}'.format(Logs_path))
                os.rmdir(Logs_path)
            else:
                logger.warning('Files still remain in {}'.format(Logs_path))


if __name__ == '__main__':
    main()
