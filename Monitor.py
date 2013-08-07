#!/usr/bin/env python
# encoding: utf-8
"""
Monitor.py

Created by Josh Walawender on 2013-07-25.
Copyright (c) 2013 __MyCompanyName__. All rights reserved.
"""

from __future__ import division, print_function

import sys
import os
from argparse import ArgumentParser
import time
import subprocess32


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
        DataPath = os.path.join(V5DataPath, "Images", DateString)
    if telescope == "V20":
        DataPath = os.path.join(V20DataPath, "Images", DateString)


    ##-------------------------------------------------------------------------
    ## Look for Pre-existing Files
    ##-------------------------------------------------------------------------
    if not os.path.exists(DataPath): os.mkdir(DataPath)
    PreviousFiles = os.listdir(DataPath)
    PreviousFilesTime = time.gmtime()

    ##-------------------------------------------------------------------------
    ## Operation Loop
    ##-------------------------------------------------------------------------
    PythonString = os.path.join("/sw", "bin", "python")
    homePath = os.path.expandvars("$HOME")
    MeasureImageString = os.path.join(homePath, "bin", "VYSOS", "MeasureImage.py")
    while Operate:
        ## Set date to tonight
        now = time.gmtime()
        nowDecimalHours = now.tm_hour + now.tm_min/60. + now.tm_sec/3600.
        DateString = time.strftime("%Y%m%dUT", now)
        TimeString = time.strftime("%Y/%m/%d %H:%M:%S UT -", now)
        
        Files = os.listdir(DataPath)
        FilesTime = now
        
        time.sleep(1)
                
        if len(Files) > len(PreviousFiles):
            for File in Files:
                FileFound = False
                for PreviousFile in PreviousFiles:
                    if File == PreviousFile:
                        FileFound = True
                if not FileFound:
                    if re.match(".*\.fi?ts", File) and not re.match(".*\-Empty\-.*\.fts", File):
                        print "New fits File Found:  %s" % File
                        Focus = False
                        ProcessCall = [PythonString, MeasureImageString, os.path.join(DataPath, File)]
                        print "  %s Calling MeasureImage.py with %s" % (TimeString, ProcessCall[2:])
                        try:
                            MIoutput = subprocess32.check_output(ProcessCall, stderr=subprocess32.STDOUT, timeout=150)
                            print "Call to MeasureImage.py Succeeded"
                        except:
                            print "Call to MeasureImage.py Failed"
        PreviousFiles = Files
        PreviousFilesTime = now
        time.sleep(5)
        if nowDecimalHours > 18.0:
            Operate = False


if __name__ == "__main__":
    sys.exit(main())
