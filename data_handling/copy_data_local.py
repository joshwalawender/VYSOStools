#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import datetime
import glob
import shutil
import subprocess
import re


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

    ## Safety Feature: do not have delete active if working on today's data
    if date == datetime.datetime.utcnow().strftime('%Y%m%dUT'):
        args.delete = False

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
    LogFilePath = os.path.join('/', 'Users', 'vysosuser', 'logs')
    LogFileHandler = logging.FileHandler(os.path.join(LogFilePath, LogFileName))
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)



    ##-------------------------------------------------------------------------
    ## Copy Data from Windows Share to Drobo and USB Drive
    ##-------------------------------------------------------------------------
    windows_path = os.path.join('/', 'Volumes', 'Data_{}'.format(args.telescope))
    drobo_path = os.path.join('/', 'Volumes', 'Drobo', args.telescope)
    extdrive_paths = [os.path.join('/', 'Volumes', 'WD500B', args.telescope),\
                      os.path.join('/', 'Volumes', 'WD500_C', args.telescope)]
    if os.path.exists(extdrive_paths[0]):
        extdrive_path = extdrive_paths[0]
    elif os.path.exists(extdrive_paths[1]):
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
    if not os.path.exists(os.path.join(drobo_path, 'Images', date)):
        logger.info('Making directory: {}'.format(os.path.join(drobo_path, 'Images', date)))
        os.mkdir(os.path.join(drobo_path, 'Images', date))
    if not os.path.exists(os.path.join(drobo_path, 'Logs', date)):
        logger.info('Making directory: {}'.format(os.path.join(drobo_path, 'Logs', date)))
        os.mkdir(os.path.join(drobo_path, 'Logs', date))

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
    if not os.path.exists(os.path.join(extdrive_path, 'Images', date)):
        logger.info('Making directory: {}'.format(os.path.join(extdrive_path, 'Images', date)))
        os.mkdir(os.path.join(extdrive_path, 'Images', date))
    if not os.path.exists(os.path.join(extdrive_path, 'Logs', date)):
        logger.info('Making directory: {}'.format(os.path.join(extdrive_path, 'Logs', date)))
        os.mkdir(os.path.join(extdrive_path, 'Logs', date))

    ## Make list of files to analyze
    files = glob.glob(os.path.join(windows_path, 'Images', date, '*.fts'))
    if os.path.exists(os.path.join(windows_path, 'Images', date, 'Calibration')):
        files.extend(glob.glob(os.path.join(windows_path, 'Images', date, 'Calibration', '*.fts')))
        if not os.path.exists(os.path.join(drobo_path, 'Images', date, 'Calibration')):
            os.mkdir(os.path.join(drobo_path, 'Images', date, 'Calibration'))
        if not os.path.exists(os.path.join(extdrive_path, 'Images', date, 'Calibration')):
            os.mkdir(os.path.join(extdrive_path, 'Images', date, 'Calibration'))
    if os.path.exists(os.path.join(windows_path, 'Images', date, 'AutoFlat')):
        files.extend(glob.glob(os.path.join(windows_path, 'Images', date, 'AutoFlat', '*.fts')))
        if not os.path.exists(os.path.join(drobo_path, 'Images', date, 'AutoFlat')):
            os.mkdir(os.path.join(drobo_path, 'Images', date, 'AutoFlat'))
        if not os.path.exists(os.path.join(extdrive_path, 'Images', date, 'AutoFlat')):
            os.mkdir(os.path.join(extdrive_path, 'Images', date, 'AutoFlat'))
    files.extend(glob.glob(os.path.join(windows_path, 'Logs', date, '*.*')))
    logger.info('Found {} files to analyze'.format(len(files)))


    counter = 0
    for file in files:
        counter += 1
        filename = os.path.split(file)[1]
        logger.info('Checking file {}/{}: {}'.format(counter, len(files), filename))
        drobo_file = file.replace(windows_path, drobo_path)
        extdrive_file = file.replace(windows_path, extdrive_path)
        original_hash = subprocess.check_output(['shasum', file]).split()[0]

        ## Copy to Drobo
        if not os.path.exists(drobo_file) and copy_to_drobo:
            logger.info('  File does not exist on drobo.  Copying.')
            shutil.copy2(file, drobo_file)
        if os.path.exists(drobo_file):
            logger.debug('  File exists on drobo.  Checking SHAsum.')
            drobo_hash = subprocess.check_output(['shasum', drobo_file]).split()[0]
            if original_hash == drobo_hash:
                logger.info('  SHA sum on drobo confirmed')
            else:
                logger.warning('  SHA sum does not match')
                logger.debug('  Original SHA sum: {}'.format(original_hash))
                logger.debug('  Drobo SHA sum:    {}'.format(drobo_hash))
                logger.info('  Copying file.')
                shutil.copy2(file, drobo_file)
                if args.delete:
                    drobo_hash = subprocess.check_output(['shasum', drobo_file]).split()[0]
        ## Copy to External Drive
        if not os.path.exists(extdrive_file) and copy_to_extdrive:
            logger.info('  File does not exist on external drive.  Copying.')
            shutil.copy2(file, extdrive_file)
        if os.path.exists(extdrive_file):
            logger.debug('  File exists on external drive.  Checking SHAsum.')
            extdrive_hash = subprocess.check_output(['shasum', extdrive_file]).split()[0]
            if original_hash == extdrive_hash:
                logger.info('  SHA sum on external drive confirmed')
            else:
                logger.warning('  SHA sum does not match')
                logger.info('  Original SHA sum: {}'.format(original_hash))
                logger.info('  External SHA sum: {}'.format(extdrive_hash))
                logger.info('  Copying file.')
                shutil.copy2(file, extdrive_file)
                if args.delete:
                    extdrive_hash = subprocess.check_output(['shasum', extdrive_file]).split()[0]
        ## Delete Original File
        if args.delete:
            if (original_hash == drobo_hash) and (original_hash == extdrive_hash):
                logger.info('  All three SHA sums match.  Deleting file.')
                os.remove(file)
            else:
                logger.warning('  SHA sum mismatch.  File not deleted.')

    if args.delete:
        ## Remove Calibration directory if empty
        Calibration_path = os.path.join(windows_path, 'Images', date, 'Calibration')
        if os.path.exists(Calibration_path):
            if len(glob.glob(os.path.join(Calibration_path, '*'))) == 0:
                logger.info('Removing {}'.format(Calibration_path))
                os.rmdir(Calibration_path)
            else:
                logger.warning('Files still remain in {}'.format(Calibration_path))

        ## Remove AutoFlat directory if empty
        AutoFlat_path = os.path.join(windows_path, 'Images', date, 'AutoFlat')
        if os.path.exists(AutoFlat_path):
            if len(glob.glob(os.path.join(AutoFlat_path, '*'))) == 0:
                logger.info('Removing {}'.format(AutoFlat_path))
                os.rmdir(AutoFlat_path)
            else:
                logger.warning('Files still remain in {}'.format(AutoFlat_path))

        ## Remove Images directory if empty
        Images_path = os.path.join(windows_path, 'Images', date)
        if os.path.exists(Images_path):
            if len(glob.glob(os.path.join(Images_path, '*'))) == 0:
                logger.info('Removing {}'.format(Images_path))
                os.rmdir(Images_path)
            else:
                logger.warning('Files still remain in {}'.format(Images_path))

        ## Remove Logs directory if empty
        Logs_path = os.path.join(windows_path, 'Logs', date)
        if os.path.exists(Logs_path):
            if len(glob.glob(os.path.join(Logs_path, '*'))) == 0:
                logger.info('Removing {}'.format(Logs_path))
                os.rmdir(Logs_path)
            else:
                logger.warning('Files still remain in {}'.format(Logs_path))


if __name__ == '__main__':
    main()
