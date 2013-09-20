#!/usr/bin/env python
# encoding: utf-8
"""
MeasureImage.py

Created by Josh Walawender on 2013-07-25.
Copyright (c) 2013 __MyCompanyName__. All rights reserved.
"""

from __future__ import division, print_function

import sys
import os
from argparse import ArgumentParser
import re
import datetime
import math
import time

import ephem
import astropy.units as u

import IQMon


class ParseError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


##############################################################
## Obtain Master Dark Frame
## - look for raw dark frames from previous night
## - if not found, look back in time for MaxNights
## - once a qualifying set of darks is found (same telescope, same exptime)
## - check that CCD temp is within tolerance for darks and image
## - if not same temp, then continue going back in time
## - once a set of dark frames which satify the criterion is found, combine all via a median combine
## - write that combined dark to a file named for the DataNight (not the night it was taken)
##############################################################
def ListDarks(image):
    nDarksMin = 5  ## Minimum number of dark files to return for combination
    SearchNDays = 10 ## Number of days back in time to look for dark frames
    image.logger.info("Looking for master dark frame or darks to combine.")
    ## Extract night data was taken from path
    DataPath = os.path.split(image.rawFile)[0]
    BaseDirectory, DataNightString = os.path.split(DataPath)
    DataNight = datetime.datetime.strptime(DataNightString, "%Y%m%dUT")

    OneDay = datetime.timedelta(days=1)
    NewDate = DataNight
    NewDateString = datetime.datetime.strftime(NewDate, "%Y%m%dUT")
    DateLimit = DataNight - datetime.timedelta(days=SearchNDays)
    
    ## Check to see if MasterDark Exists for this Observation Date
    MasterDarkFilename = "MasterDark_"+image.tel.name+"_"+DataNightString+"_"+str(int(math.floor(image.exptime.to(u.s).value)))+".fits"
    MasterDarkFile  = os.path.join(image.config.pathTemp, MasterDarkFilename)    
    ## Is that Master Dark File does not exist, see if the raw files exit to build one.
    if os.path.exists(MasterDarkFile):
        image.logger.info("Found Master Dark: %s" % MasterDarkFilename)
        return [MasterDarkFile]
    else:
        image.logger.info("Could Not Find Master Dark.  Looking for raw frames.")
        Darks = []
        while NewDate > DateLimit:
            ## Look for this directory
            SearchPath = os.path.join(BaseDirectory, NewDateString, "Calibration")
            if os.path.exists(SearchPath):
                ## Now look for darks in that directory
                image.logger.debug("Looking for darks in {0}".format(SearchPath))
                Files = os.listdir(SearchPath)
                for File in Files:
                    IsDark = re.match("Dark\-([0-9]{3})\-([0-9]{8})at([0-9]{6})\.fi?ts", File)
                    if IsDark:
                        DarkExp = float(IsDark.group(1))
                        if DarkExp == image.exptime.value:
                            Darks.append(os.path.join(SearchPath, File))
                if len(Darks) >= nDarksMin:
                    ## Once we have found enough dark files, return the list of dark files
                    image.logger.info("Found %d dark files in %s" % (len(Darks), SearchPath))
                    for Dark in Darks:
                        image.logger.debug("Found Dark File: {0}".format(Dark))
                    return Darks
            NewDate = NewDate - OneDay
            NewDateString = datetime.datetime.strftime(NewDate, "%Y%m%dUT")
        if len(Darks) == 0:
            image.logger.warning("No darks found to combine.")


##-------------------------------------------------------------------------
## Main Program
##-------------------------------------------------------------------------
def main():
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    parser.add_argument("-c", "--clobber",
        action="store_true", dest="clobber",
        default=False, help="Delete previous logs and summary files for this image. (default = False)")
    ## add arguments
    parser.add_argument("filename",
        type=str,
        help="File Name of Input Image File")
    parser.add_argument("-t", dest="telescope",
        required=False, type=str,
        help="Telescope which tool the data ('V5' or 'V20')")
    args = parser.parse_args()
    
    ##-------------------------------------------------------------------------
    ## Deconstruct input filename in to path, filename and extension
    ##-------------------------------------------------------------------------
    FitsFile = os.path.abspath(args.filename)
    if not os.path.exists(FitsFile):
        raise IOError("Unable to find input file: %s" % FitsFile)
    FitsFileDirectory, FitsFilename = os.path.split(FitsFile)
    DataNightString = os.path.split(FitsFileDirectory)[1]
    FitsBasename, FitsExt = os.path.splitext(FitsFilename)


    ##-------------------------------------------------------------------------
    ## Establish IQMon Configuration
    ##-------------------------------------------------------------------------
    config = IQMon.Config()


    ##-------------------------------------------------------------------------
    ## Determine which VYSOS Telescope Image is from
    ##-------------------------------------------------------------------------
    if args.telescope == 'V5' or args.telescope == 'V20':
        telescope = args.telescope
    else:
        V5match = re.match("V5.*\.fi?ts", FitsFilename)
        V20match = re.match("V20.*\.fi?ts", FitsFilename)
        NoTelMatch = re.match(".*\d{8}at\d{6}\.fts")
        if V5match and not V20match:
            telescope = "V5"
        elif V20match and not V5match:
            telescope = "V20"
        elif NoTelMatch:
            telescope = "V5"  ## Assume telescope is VYSOS-5
        else:
            raise ParseError("Can not determine valid telescope from arguments or filename.")


    ##-------------------------------------------------------------------------
    ## Create Telescope Object
    ##-------------------------------------------------------------------------
    tel = IQMon.Telescope()
    tel.name = telescope
    if tel.name == "V5":
        tel.longName = "VYSOS-5"
        tel.focalLength = 735.*u.mm
        tel.pixelSize = 9.0*u.micron
        tel.aperture = 135.*u.mm
        tel.gain = 1.6 / u.adu
        tel.unitsForFWHM = 1.*u.pix
        tel.ROI = "[1024:3072,1024:3072]"
        tel.thresholdFWHM = 2.5*u.pix
        tel.thresholdPointingErr = 5.0*u.arcmin
        tel.thresholdEllipticity = 0.30*u.dimensionless_unscaled
        tel.pixelScale = tel.pixelSize.to(u.mm)/tel.focalLength.to(u.mm)*u.radian.to(u.arcsec)*u.arcsec/u.pix
        tel.fRatio = tel.focalLength.to(u.mm)/tel.aperture.to(u.mm)
        tel.SExtractorPhotAperture = 6.0*u.pix
        tel.SExtractorSeeing = 2.0*u.arcsec
        tel.SExtractorSaturation = 50000.*u.adu
    if tel.name == "V20":
        tel.longName = "VYSOS-20"
        tel.focalLength = 4175.*u.mm
        tel.pixelSize = 9.0*u.micron
        tel.aperture = 508.*u.mm
        tel.gain = 1.6 / u.adu
        tel.unitsForFWHM = 1.*u.arcsec
        tel.ROI = "[1024:3072,1024:3072]"
        tel.thresholdFWHM = 2.5*u.arcsec
        tel.thresholdPointingErr = 5.0*u.arcmin
        tel.thresholdEllipticity = 0.30*u.dimensionless_unscaled
        tel.pixelScale = tel.pixelSize.to(u.mm)/tel.focalLength.to(u.mm)*u.radian.to(u.arcsec)*u.arcsec/u.pix
        tel.fRatio = tel.focalLength.to(u.mm)/tel.aperture.to(u.mm)
        tel.SExtractorPhotAperture = 16.0*u.pix
        tel.SExtractorSeeing = 2.0*u.arcsec
        tel.SExtractorSaturation = 50000.*u.adu
    ## Define Site (ephem site object)
    tel.site = ephem.Observer()
    tel.CheckUnits()
    tel.DefinePixelScale()

    ##-------------------------------------------------------------------------
    ## Create IQMon.Image Object
    ##-------------------------------------------------------------------------
    image = IQMon.Image(FitsFile, tel, config)  ## Create image object

    ##-------------------------------------------------------------------------
    ## Create Filenames
    ##-------------------------------------------------------------------------
    IQMonLogFileName = os.path.join(config.pathLog, tel.longName, DataNightString+"_"+tel.name+"_IQMonLog.txt")
    htmlImageList = os.path.join(config.pathLog, tel.longName, DataNightString+"_"+tel.name+".html")
    summaryFile = os.path.join(config.pathLog, tel.longName, DataNightString+"_"+tel.name+"_Summary.txt")
    FullFrameJPEG = image.rawFileBasename+"_full.jpg"
    CropFrameJPEG = image.rawFileBasename+"_crop.jpg"
    BackgroundJPEG = image.rawFileBasename+"_bkgnd.jpg"
    if args.clobber:
        if os.path.exists(IQMonLogFileName): os.remove(IQMonLogFileName)
        if os.path.exists(htmlImageList): os.remove(htmlImageList)
        if os.path.exists(summaryFile): os.remove(summaryFile)

    ##-------------------------------------------------------------------------
    ## Perform Actual Image Analysis
    ##-------------------------------------------------------------------------
    image.MakeLogger(IQMonLogFileName, args.verbose)
    image.logger.info("###### Processing Image:  %s ######", FitsFilename)
    image.logger.info("Setting telescope variable to %s", telescope)
    image.ReadImage()           ## Create working copy of image (don't edit raw file!)
    image.GetHeader()           ## Extract values from header
    image.MakeJPEG(FullFrameJPEG, rotate=True, markPointing=True, binning=4)
    if not image.imageWCS:      ## If no WCS found in header ...
        image.SolveAstrometry() ## Solve Astrometry
        image.GetHeader()       ## Refresh Header
    image.DeterminePointingError()            ## Calculate Pointing Error
    darks = ListDarks(image)    ## List dark files
    image.DarkSubtract(darks)   ## Dark Subtract Image
    image.Crop()                ## Crop Image
    image.GetHeader()           ## Refresh Header
    image.RunSExtractor()       ## Run SExtractor
    image.DetermineFWHM()       ## Determine FWHM from SExtractor results
    image.MakeJPEG(CropFrameJPEG, markStars=True, markPointing=True, rotate=True, binning=1, backgroundSubtracted=False)
    image.MakeJPEG(BackgroundJPEG, markStars=True, markPointing=False, rotate=True, binning=1, backgroundSubtracted=True)
    image.CleanUp()             ## Cleanup (delete) temporary files.
    image.CalculateProcessTime()## Calculate how long it took to process this image
    image.AddWebLogEntry(htmlImageList) ## Add line for this image to HTML table
    image.AddSummaryEntry(summaryFile)  ## Add line for this image to text table
    

if __name__ == '__main__':
    main()
