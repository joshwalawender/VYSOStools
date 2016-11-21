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
        print('    Compressing')
        subprocess.call(['fpack', file])
        if os.path.exists('{}.fz'.format(file)):
            print('  Removing uncompressed file')
            os.remove(file)


def compress_files(telescope, date):
    assert re.match('\d{8}UT', date)
    drobo_path = '/Volumes/Drobo/{}/Images/{}'.format(telescope, date)
    ext_path = '/Volumes/WD500B/{}/Images/{}'.format(telescope, date)
    assert os.path.exists(drobo_path)
    assert os.path.exists(ext_path)
    files = glob(os.path.join(ext_path, '*.fts'))
    files.extend(glob(os.path.join(ext_path, '*.fits')))
    nfiles = len(files)
    print('Exmining {} files in:'.format(nfiles))
    print('  {}'.format(ext_path))
    print('  {}'.format(drobo_path))
    for i,file in enumerate(files):
        filename = os.path.basename(file)
        drobo_file = os.path.join(drobo_path, filename)

        print('Examining {}/{}: {}'.format(i+1, nfiles, filename))
        assert os.path.exists(file)
        compress(file)

        assert os.path.exists(drobo_file)
        compress(drobo_file)


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
    ## add arguments
    parser.add_argument("telescope",
        type=str,
        help="Telescope (V5 or V20)")
    parser.add_argument("date",
        type=str,
        help="Date (e.g. 20161125UT)")
    args = parser.parse_args()
    
    compress_files(args.telescope, args.date)
