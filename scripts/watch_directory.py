#!/usr/bin/env python
# encoding: utf-8
"""
Script to watch a directory of images and when a new one appears, run
MeasureImage.py on it.
"""

from __future__ import division, print_function

import sys
import os
from argparse import ArgumentParser
import re
import time
from datetime import datetime as dt
import pymongo
from pymongo import MongoClient

import measure_image


def main():  
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add arguments
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    args = parser.parse_args()
    telescope = args.telescope
    
    ##-------------------------------------------------------------------------
    ## Set date to tonight
    ##-------------------------------------------------------------------------
    now = dt.utcnow()
    date_string = now.strftime("%Y%m%dUT")

    ##-------------------------------------------------------------------------
    ## Set data path
    ##-------------------------------------------------------------------------
    if telescope == "V5":
        DataPath = os.path.join("/Volumes", "Data_V5", "Images", date_string)
        zp = False
    if telescope == "V20":
        DataPath = os.path.join("/Volumes", "Data_V20", "Images", date_string)
        zp = False

    client = MongoClient('192.168.1.101', 27017)
    images = client.vysos['{}.images'.format(telescope)]


    ##-------------------------------------------------------------------------
    ## Operation Loop
    ##-------------------------------------------------------------------------
    Operate = True
    MatchFilename = re.compile("(.*)\-([0-9]{8})at([0-9]{6})\.fts")
    MatchEmpty = re.compile(".*\-Empty\-.*\.fts")
    if not os.path.exists(DataPath): os.mkdir(DataPath)
    analyzed = []
    while Operate:
        ## Set date to tonight
        now = dt.utcnow()
        files = os.listdir(DataPath)
        time.sleep(1)
        images_to_analyze = {}
        for file in files:
            if file not in analyzed:
                IsMatch = MatchFilename.match(file)
                IsEmpty = MatchEmpty.match(file)
                previous = [x for x in images.find( {"filename" : file} )]

                if (len(previous) == 0) and IsMatch and not IsEmpty:
                    print('Selecting {}'.format(file))
                    target = IsMatch.group(1)
                    filetime = IsMatch.group(3)
                    images_to_analyze[filetime] = file
                else:
                    analyzed.append(file)

        for filetime in sorted(images_to_analyze.keys()):
            file = images_to_analyze[filetime]
            print('Analyzing {}'.format(file))
            try:
                measure_image.MeasureImage(os.path.join(DataPath, file),\
                                          clobber_logs=True,\
                                          zero_point=zp, analyze_image=True)
            except:
                print('WARNING:  MeasureImage failed on {}'.format(file))
                measure_image.MeasureImage(os.path.join(DataPath, file),\
                                          clobber_logs=True,\
                                          zero_point=zp, analyze_image=False)
            analyzed.append(file)

        time.sleep(30)
        if now.hour >= 17:
            Operate = False


if __name__ == "__main__":
    main()
