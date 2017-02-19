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


class Image(me.Document):
    # Basics
    filename = me.StringField(max_length=128, required=True)
    analysis_date = me.DateTimeField(default=dt.utcnow(), required=True)
    telescope = me.StringField(max_length=3, choices=['V5', 'V20'])
    compressed = me.BooleanField()
    # Header Info
    target = me.StringField(max_length=128)
    exptime = me.DecimalField(min_value=0, precision=1)
    date = me.DateTimeField()
    filter = me.StringField(max_length=15)
    header_RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    header_DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    alt = me.DecimalField(min_value=0, max_value=90, precision=2)
    az = me.DecimalField(min_value=0, max_value=360, precision=2)
    airmass = me.DecimalField(min_value=1, precision=3)
    moon_illumination = me.DecimalField(min_value=0, max_value=100, precision=1)
    moon_separation = me.DecimalField(min_value=0, max_value=180, precision=1)
    # Analysis Results
    analyzed = me.BooleanField()
    SIDREversion = me.StringField(max_length=12)
    FWHM_pix = me.DecimalField(min_value=0, precision=1)
    ellipticity = me.DecimalField(min_value=0, precision=2)
    RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    perr_arcmin = me.DecimalField(min_value=0, precision=2)
    # JPEGs
    full_field_jpeg = me.ImageField(thumbnail_size=(128,128,True))
    cropped_jpeg = me.ImageField(thumbnail_size=(128,128,True))
    
    meta = {'collection': 'images',
            'indexes': ['telescope', 'date', 'filename']}

    def __str__(self):
        output = 'MongoEngine Document for: {}\n'.format(self.filename)
        output += '  Analysis Date: {}\n'.format(self.analysis_date.isoformat())
        if self.telescope: output += '  Telescope: {}\n'.format(self.telescope)
        if self.target: output += '  Target Field: {}\n'.format(self.target)
        if self.date: output += '  Image Date: {}\n'.format(self.date.isoformat())
        if self.exptime: output += '  Exposure Time: {:.1f}\n'.format(self.exptime)
        if self.filter: output += '  Filter: {}\n'.format(self.filter)
        if self.header_RA: output += '  Header RA: {:.4f}\n'.format(self.header_RA)
        if self.header_DEC: output += '  Header Dec: {:.4f}\n'.format(self.header_DEC)
        if self.alt: output += '  Altitude: {:.4f}\n'.format(self.alt)
        if self.az: output += '  Azimuth: {:.4f}\n'.format(self.az)
        if self.airmass: output += '  Airmass: {:.3f}\n'.format(self.airmass)
        if self.moon_illumination: output += '  moon_illumination: {:.2f}\n'.format(self.moon_illumination)
        if self.moon_separation: output += '  moon_separation: {:.0f}\n'.format(self.moon_separation)
        if self.SIDREversion: output += '  SIDREversion: {}\n'.format(self.SIDREversion)
        if self.FWHM_pix: output += '  FWHM_pix: {:.1f}\n'.format(self.FWHM_pix)
        if self.ellipticity: output += '  ellipticity: {:.2f}\n'.format(self.ellipticity)
        if self.RA: output += '  WCS RA: {:.4f}\n'.format(self.RA)
        if self.DEC: output += '  WCS DEC: {:.4f}\n'.format(self.DEC)
        if self.perr_arcmin: output += '  Pointing Error: {:.1f} arcmin\n'.format(self.perr_arcmin)
        return output

    def __repr__(self):
        return self.__str__()


##-------------------------------------------------------------------------
## Measure Image
##-------------------------------------------------------------------------
def measure_image(file,\
                 verbose=False,\
                 nographics=False,\
                 record=False,\
                 ):

    file = os.path.expanduser(file)
    file = os.path.abspath(file)
    ## Try to determine which telescope
    image_info = Image(filename=os.path.basename(file))
    try:
        image_info.telescope = re.match('(V[25]0?)_.+', image_info.filename).group(1)
    except:
        pass
    image_info.compressed = (os.path.splitext(image_info.filename)[1] == '.fz')

    im = SIDRE.ScienceImage(file, verbose=False)
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
            image_info.filter = float(im.ccd.header.get('EXPTIME'))
        except:
            pass

    print(image_info)

    if not SIDRE.utils.get_master(im.date, type='Bias'):
        SIDRE.calibration.make_master_bias(im.date)
    im.bias_correct()
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
    image_info.target = im.ccd.header.get('OBJECT')
    vprc_path = '/Users/jwalawender/Dropbox/SIDREtest/'
    vprc_file = os.path.join(vprc_path, 'VPRC_{}.fit'.format(image_info.target))
    if os.path.exists(vprc_file):
        im.log.info('Reading VPRC catalog file')
        cathdul = fits.open(vprc_file, 'readonly')
        vprc = Table(cathdul[1].data)
        vprc.add_column(Column(vprc['raMean'], name='RA'))
        vprc.add_column(Column(vprc['decMean'], name='DEC'))
        vprc = vprc[vprc['rMeanPSFMag'] != -999.] # Remove entries with invalid r magnitude
        vprc = vprc[vprc['rMeanPSFMagErr'] != -999.] # Remove entries with invalid r magnitude error
        vprc = vprc[vprc['rMeanPSFMagErr'] < 0.1] # Remove entries with r magnitude error > 0.1
        vprc = vprc[vprc['rMeanPSFMag'] < 16.0] # Remove entries r magnitude > 16
        vprc = vprc[vprc['nDetections'] >= 6] # Remove entried with fewer than 6 detections
        vprc.keep_columns(['objID', 'RA', 'DEC', 'rMeanPSFMag', 'rMeanPSFMagErr', 'nDetections'])
        coords = c.SkyCoord(vprc['RA'], vprc['DEC'], unit=u.deg)

        im.extract()
        im.associate(vprc, magkey='rMeanPSFMag')
        im.calculate_zero_point(plot='ZP_PanSTARRS.png')

    image_info.analyzed=True
    image_info.SIDREversion=SIDRE.version.version

    if not nographics:
        jpegfilename='test_PS.jpg'
        im.render_jpeg(jpegfilename=jpegfilename, overplot_catalog=vprc,
                       overplot_assoc=True, overplot_pointing=True)
        # image_info.full_field_jpeg = open(jpegfilename, 'rb')
    
    if record:
        logger.info('Connecting to mongo db at 192.168.1.101')
        try:
            me.connect('vysos', host='192.168.1.101')
        except:
            logger.error('Could not connect to mongo db')
            raise Error('Failed to connect to mongo')
        else:
            image_info.save()
    else:
        print(image_info)


def main():
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    parser = ArgumentParser(description="Script to analyze a simgle FITS image")
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
