#!/usr/bin/env python
# encoding: utf-8
"""
This is the basic tool for analyzing an image using the IQMon toolkit.  This
script has been customized to the VYSOS telescopes.
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
    DataPath = os.path.split(image.raw_file)[0]
    BaseDirectory, DataNightString = os.path.split(DataPath)
    DataNight = datetime.datetime.strptime(DataNightString, "%Y%m%dUT")

    OneDay = datetime.timedelta(days=1)
    NewDate = DataNight
    NewDateString = datetime.datetime.strftime(NewDate, "%Y%m%dUT")
    DateLimit = DataNight - datetime.timedelta(days=SearchNDays)
    
    ## Check to see if MasterDark Exists for this Observation Date
    MasterDarkFilename = "MasterDark_"+image.tel.name+"_"+DataNightString+"_"+str(int(math.floor(image.exptime.to(u.s).value)))+".fits"
    MasterDarkFile  = os.path.join(image.tel.temp_file_path, MasterDarkFilename)    
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
    ## Determine which VYSOS Telescope Image is from
    ##-------------------------------------------------------------------------
    if args.telescope == 'V5' or args.telescope == 'V20':
        telescope = args.telescope
    else:
        V5match = re.match("V5.*\.fi?ts", FitsFilename)
        V20match = re.match("V20.*\.fi?ts", FitsFilename)
        NoTelMatch = re.match(".*\d{8}at\d{6}\.fts", FitsFilename)
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
    path_temp = os.path.join(os.path.expanduser('~'), 'IQMon', 'tmp')
    path_plots = os.path.join(os.path.expanduser('~'), 'IQMon', 'Plots')
    tel = IQMon.Telescope(path_temp, path_plots)
    tel.name = telescope
    if tel.name == "V5":
        tel.long_name = "VYSOS-5"
#         tel.SCAMP_aheader = os.path.join(config.pathConfig, 'VYSOS5.ahead')
        tel.focal_length = 735.*u.mm
        tel.pixel_size = 9.0*u.micron
        tel.aperture = 135.*u.mm
        tel.gain = 1.6 / u.adu
        tel.units_for_FWHM = 1.*u.pix
        tel.ROI = "[1024:3072,1024:3072]"
        tel.threshold_FWHM = 2.5*u.pix
        tel.threshold_pointing_err = 5.0*u.arcmin
        tel.threshold_ellipticity = 0.30*u.dimensionless_unscaled
        tel.pixel_scale = tel.pixel_size.to(u.mm)/tel.focal_length.to(u.mm)*u.radian.to(u.arcsec)*u.arcsec/u.pix
        tel.fRatio = tel.focal_length.to(u.mm)/tel.aperture.to(u.mm)
        tel.SExtractor_params = {'PHOT_APERTURES': '6.0',
                                'BACK_SIZE': '16',
                                'SEEING_FWHM': '2.5',
                                'SATUR_LEVEL': '50000',
                                'DETECT_MINAREA': '5',
                                'DETECT_THRESH': '5.0',
                                'ANALYSIS_THRESH': '5.0',
                                'FILTER': 'N',
                                }
        tel.distortionOrder = 5
        tel.pointing_marker_size = 4*u.arcmin
    if tel.name == "V20":
        tel.long_name = "VYSOS-20"
#         tel.SCAMP_aheader = os.path.join(config.pathConfig, 'VYSOS20.ahead')
        tel.focal_length = 4175.*u.mm
        tel.pixel_size = 9.0*u.micron
        tel.aperture = 508.*u.mm
        tel.gain = 1.6 / u.adu
        tel.units_for_FWHM = 1.*u.arcsec
        tel.ROI = "[1024:3072,1024:3072]"
        tel.threshold_FWHM = 2.5*u.arcsec
        tel.threshold_pointing_err = 5.0*u.arcmin
        tel.threshold_ellipticity = 0.30*u.dimensionless_unscaled
        tel.pixel_scale = tel.pixel_size.to(u.mm)/tel.focal_length.to(u.mm)*u.radian.to(u.arcsec)*u.arcsec/u.pix
        tel.fRatio = tel.focal_length.to(u.mm)/tel.aperture.to(u.mm)
        tel.SExtractor_params = {'PHOT_APERTURES': '16.0',
                                'BACK_SIZE': '16',
                                'SEEING_FWHM': '2.5',
                                'SATUR_LEVEL': '50000',
                                'DETECT_MINAREA': '5',
                                'DETECT_THRESH': '5.0',
                                'ANALYSIS_THRESH': '5.0',
                                'FILTER': 'N',
                                }
        tel.distortionOrder = 1
        tel.pointing_marker_size = 1*u.arcmin
    ## Define Site (ephem site object)
    tel.site = ephem.Observer()
    tel.check_units()
    tel.define_pixel_scale()

    ##-------------------------------------------------------------------------
    ## Create IQMon.Image Object
    ##-------------------------------------------------------------------------
    image = IQMon.Image(FitsFile, tel=tel)  ## Create image object

    ##-------------------------------------------------------------------------
    ## Create Filenames
    ##-------------------------------------------------------------------------
    path_log = os.path.join(os.path.expanduser('~'), 'IQMon', 'Logs')
    IQMonLogFileName = os.path.join(path_log, tel.long_name, DataNightString+"_"+tel.name+"_IQMonLog.txt")
    htmlImageList = os.path.join(path_log, tel.long_name, DataNightString+"_"+tel.name+".html")
    summaryFile = os.path.join(path_log, tel.long_name, DataNightString+"_"+tel.name+"_Summary.txt")
    if args.clobber:
        if os.path.exists(IQMonLogFileName): os.remove(IQMonLogFileName)
        if os.path.exists(htmlImageList): os.remove(htmlImageList)
        if os.path.exists(summaryFile): os.remove(summaryFile)

    ##-------------------------------------------------------------------------
    ## Perform Actual Image Analysis
    ##-------------------------------------------------------------------------
    image.make_logger(IQMonLogFileName, args.verbose)
    image.logger.info("###### Processing Image:  %s ######", FitsFilename)
    image.logger.info("Setting telescope variable to %s", telescope)
    image.read_image()           ## Create working copy of image (don't edit raw file!)
    image.read_header()           ## Extract values from header

    if not image.image_WCS:      ## If no WCS found in header ...
        image.solve_astrometry() ## Solve Astrometry
        image.read_header()       ## Refresh Header
    image.determine_pointing_error()            ## Calculate Pointing Error

    SmallJPEG = image.raw_file_basename+"_small.jpg"
    image.new_make_JPEG(SmallJPEG, binning=1, p1=0.15, p2=0.5,\
                        mark_pointing=True,\
                        mark_detected_stars=False,\
                        mark_catalog_stars=False,\
                        transform=None)

    sys.exit(0)



    darks = ListDarks(image)    ## List dark files
    if darks and len(darks) > 0:
        image.dark_subtract(darks)   ## Dark Subtract Image
    image.run_SExtractor()       ## Run SExtractor
    image.determine_FWHM()       ## Determine FWHM from SExtractor results
    FullJPEG = image.raw_file_basename+"_fullframe.jpg"
    image.make_JPEG(FullJPEG, markDetectedStars=False, markPointing=True, binning=3)

#     image.RunSCAMP(catalog='UCAC-3')
#     image.RunSWarp()
#     image.GetHeader()           ## Extract values from header
#     image.GetLocalUCAC4(local_UCAC_command="/Users/joshw/Data/UCAC4/access/u4test", local_UCAC_data="/Users/joshw/Data/UCAC4/u4b")
#     image.RunSExtractor(assoc=True)
#     image.DetermineFWHM()       ## Determine FWHM from SExtractor results
    image.make_PSF_plot()
#     image.MeasureZeroPoint(plot=True)
#     CatalogJPEG = image.rawFileBasename+"_catstars.jpg"
#     image.MakeJPEG(CatalogJPEG, markCatalogStars=True, markPointing=True, binning=2)

    image.crop()
    CropJPEG = image.raw_file_basename+"_crop.jpg"
    image.make_JPEG(CropJPEG, markDetectedStars=False, markPointing=True, binning=1)

    image.clean_up()             ## Cleanup (delete) temporary files.
    image.calculate_process_time()## Calculate how long it took to process this image
    fields=["Date and Time", "Filename", "Alt", "Az", "Airmass", "MoonSep", "MoonIllum", "FWHM", "ellipticity", "ZeroPoint", "PErr", "PosAng", "nStars", "ProcessTime"]
    image.add_web_log_entry(htmlImageList, fields=fields) ## Add line for this image to HTML table
    image.add_summary_entry(summaryFile)  ## Add line for this image to text table
    

if __name__ == '__main__':
    main()
