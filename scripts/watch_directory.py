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
import yaml

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
    now = time.gmtime()
    DateString = time.strftime("%Y%m%dUT", now)

    ##-------------------------------------------------------------------------
    ## Set data path
    ##-------------------------------------------------------------------------
    if telescope == "V5":
        DataPath = os.path.join("/Volumes", "Data_V5", "Images", DateString)
        summary_file = os.path.join('/Users/vysosuser/IQMon/Logs/VYSOS-5/', '{}_V5_Summary.txt'.format(DateString))
        zp = False
    if telescope == "V20":
        DataPath = os.path.join("/Volumes", "Data_V20", "Images", DateString)
        summary_file = os.path.join('/Users/vysosuser/IQMon/Logs/VYSOS-20/', '{}_V20_Summary.txt'.format(DateString))
        zp = True



    ##-------------------------------------------------------------------------
    ## Operation Loop
    ##-------------------------------------------------------------------------
    Operate = True
    MatchFilename = re.compile("(.*)\-([0-9]{8})at([0-9]{6})\.fts")
    MatchEmpty = re.compile(".*\-Empty\-.*\.fts")
    if not os.path.exists(DataPath): os.mkdir(DataPath)
    PreviousFiles = []
    while Operate:
        ## Set date to tonight
        now = time.gmtime()
        nowDecimalHours = now.tm_hour + now.tm_min/60. + now.tm_sec/3600.
        Files = os.listdir(DataPath)
        time.sleep(1)

        if len(Files) > len(PreviousFiles):
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

            if os.path.exists(summary_file):
                with open(summary_file, 'r') as yaml_string:
                    yaml_list = yaml.load(yaml_string)
                PreviousFiles = [entry['filename'] for entry in yaml_list]
            else:
                PreviousFiles = []
            
            for Image in SortedImageFiles:
                if not Image in PreviousFiles:
                    print('Analyzing {}'.format(Image))
                    clobber_summary = False
                    if len(PreviousFiles) == 0:
                        clobber_summary = True
                    PreviousFiles.append(Image)
                    try:
                        measure_image.MeasureImage(os.path.join(DataPath, Image),\
                                                  clobber_logs=True,\
                                                  clobber_summary=clobber_summary,\
                                                  zero_point=zp, analyze_image=True)
                    except:
                        print('WARNING:  MeasureImage failed on {}'.format(Image))
                        measure_image.MeasureImage(os.path.join(DataPath, Image),\
                                                  clobber_logs=True,\
                                                  clobber_summary=clobber_summary,\
                                                  zero_point=zp, analyze_image=False)

        time.sleep(5)
        if nowDecimalHours > 16.5:
            Operate = False


if __name__ == "__main__":
    main()
