#!/usr/bin/env python
# encoding: utf-8

import sys
import os
import re
import fnmatch
import numpy
from datetime import datetime as dt
import glob
from argparse import ArgumentParser
import astropy.io.fits as fits

import IQMon
from measure_image import measure_image


def main(argv=None):
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add flags
    parser.add_argument("-n", "--no-clobber",
        dest="clobber", action="store_false", default=True, 
        help="Delete previous logs and summary files for this night. (default = True)")
    ## add arguments
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    parser.add_argument("-d", "--date", 
        dest="date", required=False, default="", type=str,
        help="UT date of night to analyze. (i.e. '20130805UT')")
    args = parser.parse_args()
    
    
    ##-------------------------------------------------------------------------
    ## Set date to tonight if not specified
    ##-------------------------------------------------------------------------
    now = dt.utcnow()
    if args.date is None:
        args.date = now.strftime("%Y%m%dUT")
    
    ## Set Path to Data for this night
    paths = [
             os.path.join(os.path.expanduser("~"), f"{args.telescope}Data", "Images", args.date),
             os.path.join('/', 'Volumes', 'MLOData', args.telescope, 'Images', args.date[:4], args.date),
             os.path.join('/', 'Volumes', 'DataCopy', args.telescope, 'Images', args.date[:4], args.date),
            ]


    for path in paths:
        if os.path.exists(path):
            print('Found data folder at: {}'.format(path))
            location = path
    if location is None:
        print('Could not find data path for {}'.format(args.telescope))
    else:
        print("Analyzing data for night of "+args.date)
        print("Found data at: {}".format(location))
    
        files = glob.glob(os.path.join(location, '*.fts'))
        print(f"Found {len(files):d} files in images directory")
        for file in files:
            measure_image(file, nographics=True)


if __name__ == "__main__":
    main()

