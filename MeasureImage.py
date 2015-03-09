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
import astropy.io.fits as fits

import IQMon


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
    try:
        DataNight = datetime.datetime.strptime(DataNightString, "%Y%m%dUT")
    except:
        return []

    OneDay = datetime.timedelta(days=1)
    NewDate = DataNight
    NewDateString = datetime.datetime.strftime(NewDate, "%Y%m%dUT")
    DateLimit = DataNight - datetime.timedelta(days=SearchNDays)
    
    ## Check to see if MasterDark Exists for this Observation Date
    MasterDarkFilename = 'MasterDark_{}_{}_{}.fits'.format(\
                         image.tel.name,\
                         DataNightString,\
                         int(math.floor(image.exptime.to(u.s).value)),\
                         )
    MasterDarkFile  = os.path.join(image.tel.temp_file_path, MasterDarkFilename)    
    ## Is that Master Dark File does not exist, see if the raw files exit to build one.
    if os.path.exists(MasterDarkFile):
        image.logger.info("  Found Master Dark: %s" % MasterDarkFilename)
        return [MasterDarkFile]
    else:
        image.logger.info("  Could Not Find Master Dark.  Looking for raw frames.")
        Darks = []
        while NewDate > DateLimit:
            ## Look for this directory
            SearchPath = os.path.join(BaseDirectory, NewDateString, "Calibration")
            if os.path.exists(SearchPath):
                ## Now look for darks in that directory
                image.logger.debug("  Looking for darks in {0}".format(SearchPath))
                Files = os.listdir(SearchPath)
                for File in Files:
                    IsDark = re.match("Dark\-([0-9]{3})\-([0-9]{8})at([0-9]{6})\.fi?ts", File)
                    if IsDark:
                        DarkExp = float(IsDark.group(1))
                        if DarkExp == image.exptime.value:
                            Darks.append(os.path.join(SearchPath, File))
                if len(Darks) >= nDarksMin:
                    ## Once we have found enough dark files, return the list of dark files
                    image.logger.info("  Found %d dark files in %s" % (len(Darks), SearchPath))
                    for Dark in Darks:
                        image.logger.debug("  Found Dark File: {0}".format(Dark))
                    return Darks
            NewDate = NewDate - OneDay
            NewDateString = datetime.datetime.strftime(NewDate, "%Y%m%dUT")
        if len(Darks) == 0:
            image.logger.warning("  No darks found to combine.")


##-------------------------------------------------------------------------
## Measure Image
##-------------------------------------------------------------------------
def MeasureImage(filename,\
                 telescope=None,\
                 clobber_summary=False,\
                 clobber_logs=False,\
                 verbose=False,\
                 nographics=False,\
                 analyze_image=True,\
                 record=True,\
                 zero_point=False,\
                 ):

    ##-------------------------------------------------------------------------
    ## Deconstruct input filename in to path, filename and extension
    ##-------------------------------------------------------------------------
    FitsFile = os.path.abspath(filename)
    if not os.path.exists(FitsFile):
        raise IOError("Unable to find input file: %s" % FitsFile)
    FitsFileDirectory, FitsFilename = os.path.split(FitsFile)
    DataNightString = os.path.split(FitsFileDirectory)[1]
    FitsBasename, FitsExt = os.path.splitext(FitsFilename)


    ##-------------------------------------------------------------------------
    ## Determine which VYSOS Telescope Image is from
    ##-------------------------------------------------------------------------
    if telescope == 'V5' or telescope == 'V20':
        pass
    else:
        V5match = re.match("V5.*\.fi?ts", FitsFilename)
        V20match = re.match("V20.*\.fi?ts", FitsFilename)
        NoTelMatch = re.match(".*\d{8}at\d{6}\.fts", FitsFilename)
        if V5match and not V20match:
            telescope = "V5"
        elif V20match and not V5match:
            telescope = "V20"
        else:
            with fits.open(FitsFile) as hdulist:
                if hdulist[0].header['OBSERVAT']:
                    if re.search('VYSOS-?20', hdulist[0].header['OBSERVAT']):
                        telescope = "V20"
                    elif re.search('VYSOS-?5', hdulist[0].header['OBSERVAT']):
                        telescope = "V5"
                    else:
                        print("Can not determine valid telescope from arguments or filename or header.")
                        sys.exit(0)
                else:
                    print("Can not determine valid telescope from arguments or filename or header.")
                    sys.exit(0)


    ##-------------------------------------------------------------------------
    ## Create Telescope Object
    ##-------------------------------------------------------------------------
    if telescope == 'V5':
        config_file = os.path.join(os.path.expanduser('~'), 'IQMon', 'config_VYSOS-5.yaml')
    if telescope == 'V20':
        config_file = os.path.join(os.path.expanduser('~'), 'IQMon', 'config_VYSOS-20.yaml')
    tel = IQMon.Telescope(config_file)


    ##-------------------------------------------------------------------------
    ## Create Filenames
    ##-------------------------------------------------------------------------
    image = IQMon.Image(FitsFile, tel)
    image.make_logger(verbose=verbose, clobber=clobber_logs)
    print('Logging to {}'.format(image.logfile))
    image.read_image()
    if telescope == 'V5':
        image.edit_header('FILTER', 'PSr')
    image.read_header()

    if image.object_name:
        target_name = image.object_name
        image.logger.info('Target name from header: {}'.format(target_name))
    else:
        TargetFileNameMatch = re.match('V\d{1,2}_(\w+)\-(\w+)\-\d{8}at\d{6}', FitsBasename)
        if TargetFileNameMatch:
            target_name = TargetFileNameMatch.group(1)
            image.logger.info('Target name from filename: {}'.format(target_name))
        else:
            image.logger.error('Could not determine target name.  Exiting.')
            sys.exit(0)

    if not os.path.exists(os.path.join(tel.logs_file_path, 'targets')):
        os.mkdir(os.path.join(tel.logs_file_path, 'targets'))
    target_file = os.path.join(tel.logs_file_path, 'targets', '{}.yaml'.format(target_name))

    html_file = os.path.join(tel.logs_file_path, DataNightString+"_"+telescope+".html")
    yaml_file = os.path.join(tel.logs_file_path, DataNightString+"_"+telescope+"_Summary.txt")
    if clobber_summary:
        if os.path.exists(html_file): os.remove(html_file)
        if os.path.exists(yaml_file): os.remove(yaml_file)


    ##-------------------------------------------------------------------------
    ## Perform Actual Image Analysis
    ##-------------------------------------------------------------------------
    if analyze_image:
        darks = ListDarks(image)
        if darks and len(darks) > 0:
            image.dark_subtract(darks)

        image.run_SExtractor()
        image.determine_FWHM()

        is_blank = (image.n_stars_SExtracted < 100)
        if is_blank:
            image.logger.warning('Only {} stars found.  Image may be blank.'.format(image.n_stars_SExtracted))

        if not image.image_WCS and not is_blank:
            image.solve_astrometry()
            image.read_header()
            image.run_SExtractor()
        image.determine_pointing_error()


        if zero_point and not is_blank:
            image.run_SCAMP()
            if image.SCAMP_successful:
                image.run_SWarp()
                image.read_header()

                if telescope == 'V20':
#                    image.get_catalog()
                    local_UCAC = os.path.join(os.path.expanduser('~'), 'UCAC4')
                    image.get_local_UCAC4(local_UCAC_command=os.path.join(local_UCAC, 'access', 'u4test'),\
                                          local_UCAC_data=os.path.join(local_UCAC, 'u4b'))
                if telescope == 'V5':
#                     image.get_catalog()
                    local_UCAC = os.path.join(os.path.expanduser('~'), 'UCAC4')
                    image.get_local_UCAC4(local_UCAC_command=os.path.join(local_UCAC, 'access', 'u4test'),\
                                          local_UCAC_data=os.path.join(local_UCAC, 'u4b'))

                image.tel.SExtractor_params['ANALYSIS_THRESH'] = 1.5
                image.tel.SExtractor_params['DETECT_THRESH'] = 1.5
                image.run_SExtractor(assoc=True)
                image.determine_FWHM()
                image.measure_zero_point(plot=True)
                mark_catalog = True
            else:
                image.logger.info('  SCAMP failed.  Skipping photometric calculations.')

        if not nographics and image.FWHM:
            image.make_PSF_plot()

    if record and not nographics:
        if tel.name == 'VYSOS-5':
            p1, p2 = (0.15, 0.50)
        if tel.name == 'VYSOS-20':
            p1, p2 = (3.0, 0.50)
        small_JPEG = image.raw_file_basename+"_fullframe.jpg"
        image.make_JPEG(small_JPEG, binning=3,\
                        p1=p1, p2=p2,\
                        make_hist=False,\
                        mark_pointing=True,\
                        mark_detected_stars=True,\
                        mark_catalog_stars=False,\
                        mark_saturated=False,\
                        )
        cropped_JPEG = image.raw_file_basename+"_crop.jpg"
        image.make_JPEG(cropped_JPEG,\
                        p1=p1, p2=p2,\
                        make_hist=False,\
                        mark_pointing=True,\
                        mark_detected_stars=True,\
                        mark_catalog_stars=False,\
                        mark_saturated=False,\
                        crop=(1024, 1024, 3072, 3072),\
                        )

    image.clean_up()
    image.calculate_process_time()

    if record:
        fields=["Date and Time", "Filename", "Alt", "Az", "Airmass", "MoonSep", "MoonIllum", "FWHM", "ellipticity", "PErr", "ZeroPoint", "nStars", "ProcessTime"]
        image.add_web_log_entry(html_file, fields=fields)
        image.add_yaml_entry(yaml_file)
        image.add_yaml_entry(target_file)

    image.logger.info('Done.')


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
    parser.add_argument("--no-graphics",
        action="store_true", dest="nographics",
        default=False, help="Turn off generation of graphics")
    parser.add_argument("-z", "--zp",
        action="store_true", dest="zero_point",
        default=False, help="Calculate zero point")
    parser.add_argument("-n", "--norecord",
        action="store_true", dest="no_record",
        default=False, help="Do not record results in HTML or YAML")
    ## add arguments
    parser.add_argument("filename",
        type=str,
        help="File Name of Input Image File")
    parser.add_argument("-t", dest="telescope",
        required=False, type=str,
        help="Telescope which took the data ('V5' or 'V20')")
    args = parser.parse_args()

    record = not args.no_record

    MeasureImage(args.filename,\
                 telescope=args.telescope,\
                 nographics=args.nographics,\
                 zero_point=args.zero_point,\
                 record=record,\
                 verbose=args.verbose)


if __name__ == '__main__':
    main()
