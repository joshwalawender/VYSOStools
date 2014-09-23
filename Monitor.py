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
import numpy

import MeasureImage

help_message = '''
The help message goes here.
'''


def main(argv=None):  
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
    now = time.gmtime()
    DateString = time.strftime("%Y%m%dUT", now)

    ##-------------------------------------------------------------------------
    ## Set data path
    ##-------------------------------------------------------------------------
    if telescope == "V5":
        DataPath = os.path.join("/Volumes", "Data_V5", "Images", DateString)
        zp = False
    if telescope == "V20":
        DataPath = os.path.join("/Volumes", "Data_V20", "Images", DateString)
        zp = True


    ##-------------------------------------------------------------------------
    ## Look for Pre-existing Files
    ##-------------------------------------------------------------------------
    if not os.path.exists(DataPath): os.mkdir(DataPath)
    PreviousFiles = os.listdir(DataPath)
    PreviousFilesTime = time.gmtime()

    ##-------------------------------------------------------------------------
    ## Operation Loop
    ##-------------------------------------------------------------------------
    Operate = True
    MatchFilename = re.compile("(.*)\-([0-9]{8})at([0-9]{6})\.fts")
    MatchEmpty = re.compile(".*\-Empty\-.*\.fts")
    PreviousFiles = []
    while Operate:
        ## Set date to tonight
        now = time.gmtime()
        nowDecimalHours = now.tm_hour + now.tm_min/60. + now.tm_sec/3600.
        Files = os.listdir(DataPath)
        time.sleep(1)

        if len(Files) > len(PreviousFiles):
            NewFiles = []
            Properties = []
            for File in Files:
                IsMatch = MatchFilename.match(File)
                IsEmpty = MatchEmpty.match(File)
                if not (File in PreviousFiles) and IsMatch and not IsEmpty:
                    print('Selecting {}'.format(File))
                    target = IsMatch.group(1)
                    FNdate = IsMatch.group(2)
                    FNtime = IsMatch.group(3)
                    Properties.append([FNtime, FNdate, target, File])

            SortedImageFiles   = numpy.array([row[3] for row in sorted(Properties)])
            for Image in SortedImageFiles:
                print('Analyzing {}'.format(Image))
                if len(PreviousFiles) == 0:
                    clobber = True
                else:
                    clobber = False
                try:
                    MeasureImage.MeasureImage(os.path.join(DataPath, Image), clobber=clobber, zero_point=zp)
                except:
                    print('WARNING:  MeasureImage failed on {}'.format(Image))
                PreviousFiles.append(File)

        time.sleep(5)
        if nowDecimalHours > 18.0:
            Operate = False


if __name__ == "__main__":
    main()
