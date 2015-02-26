#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import subprocess
import re
import astropy.io.fits as fits

def check_compressed(file, logger):
    is_compressed = False
    result = subprocess.check_output(['fpack', '-L', file])
    found_compression_info = False
    for line in result.split('\n'):
        IsMatch = re.match('\s*\d+\s+IMAGE\s+([\w/=\.]+)\s(BITPIX=[\-\d]+)\s(\[.*\])\s([\w]+)', line)
        if IsMatch:
            logger.debug('  funpack -L Output: {}'.format(line))
            if re.search('not_tiled', IsMatch.group(4)) and not re.search('no_pixels', IsMatch.group(3)):
                logger.debug('  Image is not compressed')
                found_compression_info = True
            elif re.search('tiled_rice', IsMatch.group(4)):
                logger.debug('  Image is rice compressed.')
                found_compression_info = True
                is_compressed = True
    if not found_compression_info:
        logger.warning('Could not determine compression status')
    return is_compressed



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
    parser.add_argument("path",
        type=str,
        help="Base path to look for fits file in")
    args = parser.parse_args()

    startpath = os.path.abspath(args.path)

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
    LogFileName = 'CompressFits.log'
    LogFile = os.path.join(startpath, LogFileName)
    LogFileHandler = logging.FileHandler(LogFile)
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)

    ##-------------------------------------------------------------------------
    ## Loop Through Files in Directory and fpack the FITS files
    ##-------------------------------------------------------------------------
    for root, dirs, files in os.walk(startpath):
        for file in files:
            basename, ext = os.path.splitext(file)
            if ext in ['.fts', '.fit', '.fits']:
                logger.info('Checking: {}'.format(os.path.join(root, file)))
                is_compressed = check_compressed(os.path.join(root, file), logger)
                if not is_compressed:
                    ## Check if the File is floating point (not raw data)
                    header = fits.getheader(os.path.join(root, file))
                    if int(header['BITPIX']) in [8, 16, 32]:
                        logger.debug('  BITPIX = {}'.format(header['BITPIX']))
                        ## Compress the file
                        logger.info('  Compressing file with fpack -F')
                        cmd = ['fpack', '-F', os.path.join(root, file)]
                        logger.debug('  Running: {}'.format(' '.join(cmd)))
                        try:
                            subprocess.call(cmd)
                            logger.info('  fpack command succeeded.')
                        except:
                            logger.error('  fpack command failed.')
                    else:
                        logger.debug('  BITPIX = {}'.format(header['BITPIX']))
                        logger.info('  Header BITPIX value is floating point.  Skipping.')
                else:
                    logger.info('  File is already compressed.  Skipping.')
            else:
                logger.debug('File {} does not appear to be a fits file.  Skipping.'.format(file))



if __name__ == '__main__':
    main()
