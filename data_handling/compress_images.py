#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import subprocess
from glob import glob
import re
import astropy.io.fits as fits


def checksum_ok(file, logger=None):
    try:
        with fits.open(file, 'update', checksum=True) as hdul:
            if 'CHECKSUM' not in hdul[0].header.keys():
                hdul[0].add_checksum()
                hdul.flush()
        failcheck = bool(subprocess.call(['fitscheck', file]))
        if failcheck:
            if logger: logger.error('Checksum failed: {}'.format(file))
    except:
        if logger: logger.error('Could not read file: {}'.format(file))
        failcheck = True
    return not failcheck


def compress(file, logger=None):
    if checksum_ok(file, logger=logger):
        if logger: logger.info('  Compressing')
        subprocess.call(['fpack', file])
        if os.path.exists('{}.fz'.format(file)):
            if logger: logger.info('  Removing uncompressed file')
            os.remove(file)


def process_folder(path, logger=None):
    files = glob(os.path.join(path, '*.fts'))
    files.extend(glob(os.path.join(path, '*.fits')))
    nfiles = len(files)
    if logger: logger.info('Exmining {} files in {}'.format(nfiles, path))
    for i,file in enumerate(files):
        if logger: logger.info('{}/{}: {}'.format(i+1, nfiles, file))
        compress(file, logger=logger)


if __name__ == '__main__':
    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('CompressData')
    logger.setLevel(logging.DEBUG)
    ## Set up console output
    LogConsoleHandler = logging.StreamHandler()
    LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)
    ## Set up file output
    LogFileName = 'CompressData.log'
    LogFilePath = os.path.join('/', 'Users', 'vysosuser', 'logs')
    LogFileHandler = logging.FileHandler(os.path.join(LogFilePath, LogFileName))
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)

#     for folder in glob('/Volumes/MLOData/uncompressed/V5/Images/20*/*'):
#         process_folder(folder, logger=logger)

    for folder in glob('/Volumes/MLOData/uncompressed/V20/Images/20*/*'):
        process_folder(folder, logger=logger)

