#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Josh Walawender on 2012-10-29.
Copyright (c) 2012 . All rights reserved.
"""

import sys
import os
import subprocess32
import re
import fnmatch
import numpy
import time
from argparse import ArgumentParser

import IQMon

help_message = '''
The help message goes here.
'''


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
    ## Establish IQMon Configuration
    ##-------------------------------------------------------------------------
    config = IQMon.Config()

    ##-------------------------------------------------------------------------
    ## Set date to tonight if not specified
    ##-------------------------------------------------------------------------
    now = time.gmtime()
    DateString = time.strftime("%Y%m%dUT", now)
    if not args.date:
        args.date = DateString
    
    ## Set Path to Data for this night
    if re.match("V5", args.telescope):
        VYSOSDATAPath = os.path.join("/Volumes", "Data_V5")
    elif re.match("V20", args.telescope):
        VYSOSDATAPath = os.path.join("/Volumes", "Data_V20")
    else:
        print("Telescope {0} does not match 'V5' or 'V20'".format(args.telescope))
        sys.exit()
    ImagesDirectory = os.path.join(VYSOSDATAPath, "Images", args.date)
    LogsDirectory = os.path.join(VYSOSDATAPath, "Logs", args.date)
    
    print "Analyzing data for night of "+args.date
    if os.path.exists(ImagesDirectory) and os.path.exists(LogsDirectory):
        print "  Found "+ImagesDirectory+" and "+LogsDirectory
        ##
        ## Loop Through All Images in Images Directory
        ##
        Files = os.listdir(ImagesDirectory)
        print "Found %d files in images directory" % len(Files)
        if len(Files) >= 1:
            ## Parse filename for date and time
            MatchFilename = re.compile("(.*)\-([0-9]{8})at([0-9]{6})\.fts")
            MatchEmpty = re.compile(".*\-Empty\-.*\.fts")
            Properties = []
            for File in Files:
                IsMatch = MatchFilename.match(File)
                IsEmpty = MatchEmpty.match(File)
                if IsMatch and not IsEmpty:
                    target = IsMatch.group(1)
                    FNdate = IsMatch.group(2)
                    FNtime = IsMatch.group(3)
                    Properties.append([FNtime, FNdate, target, File])
                else:
                    print "  File Rejected: %s" % File
        
            SortedImageTimes   = numpy.array([row[0] for row in sorted(Properties)])
            SortedImageDates   = numpy.array([row[1] for row in sorted(Properties)])
            SortedImageTargets = numpy.array([row[2] for row in sorted(Properties)])
            SortedImageFiles   = numpy.array([row[3] for row in sorted(Properties)])
        
            print "%d out of %d files meet selection criteria." % (len(SortedImageFiles), len(Files))
            for Image in SortedImageFiles:
                if fnmatch.fnmatch(Image, "*.fts"):
                    now = time.gmtime()
                    TimeString = time.strftime("%Y/%m/%d %H:%M:%S UT -", now)
                    DateString = time.strftime("%Y%m%dUT", now)

                    ProcessCall = ["/Users/vysosuser/bin/VYSOS/MeasureImage.py"]
                    if args.clobber and Image == SortedImageFiles[0]:
                        ProcessCall.append("--clobber")
                    ProcessCall.append(os.path.join(ImagesDirectory, Image))
                    print "%s Calling MeasureImage.py with %s" % (TimeString, ProcessCall)
                    try:
                        MIoutput = subprocess32.check_output(ProcessCall, stderr=subprocess32.STDOUT, timeout=150)
                        for line in MIoutput.split("\n"):
                            print line
                    except:
                        print "Call to MeasureImage.py Failed"
        else:
            print "No image files found in directory: "+ImagesDirectory
    else:
        print "No Images or Logs directory for this night"

if __name__ == "__main__":
    sys.exit(main())
