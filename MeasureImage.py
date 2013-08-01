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
import logging
import datetime
import math

import astropy.units as u

from IQMon import IQMon


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
def ListDarks(tel, image, config, logger):
	nDarksMin = 5  ## Minimum number of dark files to return for combination
	SearchNDays = 10 ## Number of days back in time to look for dark frames
	logger.info("Looking for master dark frame or darks to combine.")
	## Extract night data was taken from path
	DataPath = os.path.split(image.rawFile)[0]
	BaseDirectory, DataNightString = os.path.split(DataPath)
	DataNight = datetime.datetime.strptime(DataNightString, "%Y%m%dUT")

	OneDay = datetime.timedelta(days=1)
	NewDate = DataNight
	NewDateString = datetime.datetime.strftime(NewDate, "%Y%m%dUT")
	DateLimit = DataNight - datetime.timedelta(days=SearchNDays)
	
	## Check to see if MasterDark Exists for this Observation Date
	MasterDarkFilename = "MasterDark_"+tel.name+"_"+DataNightString+"_"+str(int(math.floor(image.exptime)))+".fits"
	MasterDarkFile  = os.path.join(config.pathTemp, MasterDarkFilename)	
	## Is that Master Dark File does not exist, see if the raw files exit to build one.
	if os.path.exists(MasterDarkFile):
		logger.info("Found Master Dark: %s" % MasterDarkFilename)
		return [MasterDarkFilename]
	else:
		logger.info("Could Not Find Master Dark.  Looking for raw frames.")
		Darks = []
		while NewDate > DateLimit:
			## Look for this directory
			SearchPath = os.path.join(BaseDirectory, NewDateString, "Calibration")
			if os.path.exists(SearchPath):
				## Now look for darks in that directory
				logger.debug("Looking for darks in {0}".format(SearchPath))
				Files = os.listdir(SearchPath)
				for File in Files:
					IsDark = re.match("Dark\-([0-9]{3})\-([0-9]{8})at([0-9]{6})\.fts", File)
					if IsDark:
						DarkExp = float(IsDark.group(1))
						if DarkExp == image.exptime:
							Darks.append(os.path.join(SearchPath, File.replace("fts", "fits")))
				if len(Darks) >= nDarksMin:
					## Once we have found enough dark files, return the list of dark files
					logger.info("Found %d dark files in %s" % (len(Darks), SearchPath))
					for Dark in Darks:
						logger.debug("Found Dark File: {0}".format(Dark))
					return Darks
			NewDate = NewDate - OneDay
			NewDateString = datetime.datetime.strftime(NewDate, "%Y%m%dUT")




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
	## Create Logger Object
	##-------------------------------------------------------------------------
	IQMonLogFileName = "/Users/joshw/IQMon/tmp/templog.txt"
	logger = logging.getLogger('IQMonLogger')
	logger.setLevel(logging.DEBUG)
	LogFileHandler = logging.FileHandler(IQMonLogFileName)
	if args.verbose:
		LogFileHandler.setLevel(logging.DEBUG)
	else:
		LogFileHandler.setLevel(logging.INFO)
	LogConsoleHandler = logging.StreamHandler()
	if args.verbose:
		LogConsoleHandler.setLevel(logging.DEBUG)
	else:
		LogConsoleHandler.setLevel(logging.INFO)
	LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
	LogFileHandler.setFormatter(LogFormat)
	LogConsoleHandler.setFormatter(LogFormat)
	logger.addHandler(LogConsoleHandler)
	logger.addHandler(LogFileHandler)

	##-------------------------------------------------------------------------
	## Establish Configuration
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
		if V5match and not V20match:
			telescope = "V5"
		elif V20match and not V5match:
			telescope = "V20"
		else:
			logger.error("Can not determine telescope from arguments or filename.")
			sys.exit()

	logger.info("###### Processing Image:  %s ######", FitsFilename)
	logger.info("Setting telescope variable to %s", telescope)

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
		tel.pixelScale = tel.pixelSize.to(u.mm)/tel.focalLength.to(u.mm)*u.radian.to(u.arcsec)
		tel.fRatio = tel.focalLength.to(u.mm)/tel.aperture.to(u.mm)
		tel.SExtractorPhotAperture = 6.0*u.pix
		tel.SExtractorSeeing = 2.0*u.arcsec
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
		tel.pixelScale = tel.pixelSize.to(u.mm)/tel.focalLength.to(u.mm)*u.radian.to(u.arcsec)
		tel.fRatio = tel.focalLength.to(u.mm)/tel.aperture.to(u.mm)
		tel.SExtractorPhotAperture = 16.0*u.pix
		tel.SExtractorSeeing = 2.0*u.arcsec

	tel.CheckUnits(logger)

	##-------------------------------------------------------------------------
	## Create Image Object
	##-------------------------------------------------------------------------
	image = IQMon.Image(FitsFile)
	image.ReadImage(config)
	image.GetHeader(logger)
	
	darks = ListDarks(tel, image, config, logger)
	
# 	image.DarkSubtract(darks)
# 	image.SolveAstrometry(tel, config, logger)
	image.DeterminePointingError(logger)
	image.GetHeader(logger)
	image.Crop(tel,logger)
	image.GetHeader(logger)
	image.RunSExtractor(tel, config, logger)
	
	image.CleanUp(logger)
	

if __name__ == '__main__':
	main()
