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


def checksum_ok(file):
    with fits.open(file, 'update', checksum=True) as hdul:
        if 'CHECKSUM' not in hdul[0].header.keys():
            hdul[0].add_checksum()
            hdul.flush()
    failcheck = bool(subprocess.call(['fitscheck', file]))
    if failcheck:
        print('WARNING: Checksum failed on {}'.format(file))
    return not failcheck


def compress(file):
    if checksum_ok(file):
        print('  Compressing')
        subprocess.call(['fpack', file])
        if os.path.exists('{}.fz'.format(file)):
            print('  Removing uncompressed file')
            os.remove(file)


def compress_files(telescope, date):
    assert re.match('\d{8}UT', date)
    drobo_path = '/Volumes/Drobo/{}/Images/{}'.format(telescope, date)
    ext_path = '/Volumes/WD500B/{}/Images/{}'.format(telescope, date)
    files = glob(os.path.join(ext_path, '*.fts'))
    files.extend(glob(os.path.join(ext_path, '*.fits')))
    files.extend(glob(os.path.join(drobo_path, '*.fts')))
    files.extend(glob(os.path.join(drobo_path, '*.fits')))
    nfiles = len(files)
    print('Exmining {} files'.format(nfiles))
    for i,file in enumerate(files):
        filename = os.path.basename(file)
        drobo_file = os.path.join(drobo_path, filename)
        print('{}/{}: {}'.format(i+1, nfiles, file))
        compress(file)


if __name__ == '__main__':
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = argparse.ArgumentParser(
             description="Program description.")
    ## add flags
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    parser.add_argument("-d", "--date",
        type=str, dest="date",
        help="The date to copy (in YYYYMMDDUT format)")
    args = parser.parse_args()
    
    compress_files(args.telescope, args.date)
