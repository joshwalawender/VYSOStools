#!/usr/bin/env python
# encoding: utf-8
"""
This is the basic tool for analyzing an image using the SIDRE toolkit.  This
script has been customized to the VYSOS telescopes.
"""

import sys
import os
from argparse import ArgumentParser
import re
from datetime import datetime as dt
import mongoengine as me

import numpy as np
from astropy import units as u
from astropy import coordinates as c
from astropy.io import fits
from astropy.table import Table, Column, vstack

import SIDRE

from VYSOS.schema import Image as ImageDoc

##-------------------------------------------------------------------------
## Measure Image
##-------------------------------------------------------------------------
def measure_image(file,\
                 verbose=False,\
                 nographics=False,\
                 record=True,\
                 ):

    file = os.path.expanduser(file)
    file = os.path.abspath(file)
    ## Try to determine which telescope
    image_info = ImageDoc(filename=os.path.basename(file))
    try:
        image_info.telescope = re.match('(V[25]0?)_.+', image_info.filename).group(1)
    except:
        pass
    image_info.compressed = (os.path.splitext(image_info.filename)[1] == '.fz')

    logfilename = os.path.basename(file).replace(".fts", ".log")
    finddate = re.search('(\d{8})at(\d{6})', logfilename)
    if finddate is not None:
        imageUTdate = f"{finddate.group(1)}UT"
    if not os.path.exists(os.path.join('/Users/vysosuser/V20Data/AnalysisLogs', imageUTdate)):
        os.mkdir(os.path.join('/Users/vysosuser/V20Data/AnalysisLogs', imageUTdate))
    logfile = os.path.join('/Users/vysosuser/V20Data/AnalysisLogs', imageUTdate, logfilename)

    im = SIDRE.ScienceImage(file, logfile=logfile, verbose=verbose)
    # Exposure Time
    try:
        image_info.exptime = float(im.ccd.header.get('EXPTIME'))
    except:
        pass
    # Exposure Start Time
    try:
        image_info.date = dt.strptime(im.ccd.header.get('DATE-OBS'), 
                                            '%Y-%m-%dT%H:%M:%S')
    except:
        pass
    # Filter
    if image_info.telescope == 'V5':
        image_info.filter = 'PSr'
    else:
        try:
            image_info.filter = im.ccd.header.get('FILTER')
        except:
            pass

    print(image_info)

    try:
        if not SIDRE.utils.get_master(im.date, type='Bias'):
            SIDRE.calibration.make_master_bias(im.date)
        im.bias_correct()
    except:
        pass
    im.gain_correct()
    im.create_deviation()
    im.make_source_mask()
    im.subtract_background()
    wcs = im.solve_astrometry(downsample=2, SIPorder=4)
    perr = im.calculate_pointing_error()
    try:
        image_info.perr_arcmin=perr.to(u.arcmin).value
        image_info.header_RA=im.header_pointing.ra.deg
        image_info.header_DEC=im.header_pointing.dec.deg
        image_info.RA=im.wcs_pointing.ra.deg
        image_info.DEC=im.wcs_pointing.dec.deg
        image_info.alt = im.header_altaz.alt.deg
        image_info.az = im.header_altaz.az.deg
        image_info.airmass = 1./np.cos( (90.-im.header_altaz.alt.deg)*np.pi/180. )
    except:
        pass



    ## Load (local) photometric reference catalog
#     image_info.target = im.ccd.header.get('OBJECT')
#     vprc_path = '/Users/jwalawender/Dropbox/SIDREtest/'
#     vprc_file = os.path.join(vprc_path, 'VPRC_{}.fit'.format(image_info.target))
#     if os.path.exists(vprc_file):
#         im.log.info('Reading VPRC catalog file')
#         cathdul = fits.open(vprc_file, 'readonly')
#         vprc = Table(cathdul[1].data)
#         vprc.add_column(Column(vprc['raMean'], name='RA'))
#         vprc.add_column(Column(vprc['decMean'], name='DEC'))
#         vprc = vprc[vprc['rMeanPSFMag'] != -999.] # Remove entries with invalid r magnitude
#         vprc = vprc[vprc['rMeanPSFMagErr'] != -999.] # Remove entries with invalid r magnitude error
#         vprc = vprc[vprc['rMeanPSFMagErr'] < 0.1] # Remove entries with r magnitude error > 0.1
#         vprc = vprc[vprc['rMeanPSFMag'] < 16.0] # Remove entries r magnitude > 16
#         vprc = vprc[vprc['nDetections'] >= 6] # Remove entried with fewer than 6 detections
#         vprc.keep_columns(['objID', 'RA', 'DEC', 'rMeanPSFMag', 'rMeanPSFMagErr', 'nDetections'])
#         coords = c.SkyCoord(vprc['RA'], vprc['DEC'], unit=u.deg)
# 
#         im.extract()
#         im.associate(vprc, magkey='rMeanPSFMag')
#         im.calculate_zero_point(plot='ZP_PanSTARRS.png')

    ## Get photometric reference catalog from UCAC
    

    image_info.analyzed=True
    image_info.SIDREversion=SIDRE.version.version

    if not nographics:
        jpegfilename='test_PS.jpg'
        im.render_jpeg(jpegfilename=jpegfilename,
                       overplot_assoc=False, overplot_pointing=True)
        # image_info.full_field_jpeg = open(jpegfilename, 'rb')
    
    if record:
        im.log.info('Connecting to mongo db at 192.168.1.101')
        try:
            me.connect('vysos', host='192.168.1.101')
        except:
            im.log.error('Could not connect to mongo db')
            raise Error('Failed to connect to mongo')
        else:
            # Remove old entries for this image file
            for entry in ImageDoc.objects(filename=os.path.basename(file)):
                im.log.debug('Removing old image info entry for this file')
                entry.delete()
            # Save new entry for this image file
            im.log.debug('Adding image info to mongo database')
            image_info.save()
    else:
        print(image_info)


def main():
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    parser = ArgumentParser(description="Script to analyze a single FITS image")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    parser.add_argument("--no-graphics",
        action="store_true", dest="nographics",
        default=False, help="Turn off generation of graphics")
    ## add arguments
    parser.add_argument("filename",
        type=str,
        help="File Name of Input Image File")
    args = parser.parse_args()

    measure_image(args.filename,\
                  nographics=args.nographics,\
                  verbose=args.verbose)


if __name__ == '__main__':
    main()
