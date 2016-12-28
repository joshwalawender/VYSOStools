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


def process_folder(path):
    files = glob(os.path.join(path, '*.fts'))
    files.extend(glob(os.path.join(path, '*.fits')))
    nfiles = len(files)
    print('Exmining {} files'.format(nfiles))
    for i,file in enumerate(files):
        print('{}/{}: {}'.format(i+1, nfiles, file))
        compress(file)


if __name__ == '__main__':
    for folder in glob('/Volumes/MLOData/uncompressed/V5/Images/20*/*'):
        process_folder(folder)

