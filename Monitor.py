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
import subprocess


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
    if telescope == "V20":
        DataPath = os.path.join("/Volumes", "Data_V20", "Images", DateString)


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
    MeasureImageString = os.path.join(homePath, "git", "VYSOS", "MeasureImage.py")
    Operate = True
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
                        print("New fits File Found:  %s" % File)
                        Focus = False
                        ProcessCall = [PythonString, MeasureImageString, os.path.join(DataPath, File)]
                        print("  %s Calling MeasureImage.py with %s" % (TimeString, ProcessCall[2:]))
                        try:
                            MIoutput = subprocess.check_output(ProcessCall, stderr=subprocess.STDOUT)
                            print("Call to MeasureImage.py Succeeded")
                        except subprocess.CalledProcessError as e:
                            print("Call to MeasureImage.py Failed.  Returncode: {}".format(e.returncode))
                            print("Call to MeasureImage.py Failed.  Command: {}".format(e.cmd))
                            print("Call to MeasureImage.py Failed.  Output: {}".format(e.output))
                        except:
                            print("Call to MeasureImage.py Failed")
        PreviousFiles = Files
        PreviousFilesTime = now
        time.sleep(5)
        if nowDecimalHours > 18.0:
            Operate = False


if __name__ == "__main__":
    sys.exit(main())
