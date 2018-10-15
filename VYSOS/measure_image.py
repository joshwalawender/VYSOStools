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
import tempfile

import matplotlib as mpl
mpl.use('Agg')

import numpy as np
from astropy import units as u
from astropy import coordinates as c
from astropy.io import fits
from astropy.table import Table, Column, vstack

import SIDRE

import pymongo



##-------------------------------------------------------------------------
## Measure Image
##-------------------------------------------------------------------------
def measure_image(file,\
                 verbose=False,\
                 nographics=False,\
                 record=True,\
                 ):
    tick = dt.utcnow()
    file = os.path.abspath(os.path.expanduser(file))

    image_info = {'filename': os.path.basename(file),
                 }

    ## Try to determine which telescope
    try:
        image_info['telescope'] = re.match('(V[25]0?)_.+', image_info['filename']).group(1)
    except:
        pass
    ## Is the image compressed?
    image_info['compressed'] = (os.path.splitext(image_info['filename'])[1] == '.fz')

    ## Set up logfile name and location
    logfilename = os.path.basename(file).replace(".fts", ".log")
    finddate = re.search('(\d{8})at(\d{6})', logfilename)
    if finddate is not None:
        imageUTdate = f"{finddate.group(1)}UT"
    if not os.path.exists(os.path.join('/Users/vysosuser/V20Data/AnalysisLogs', imageUTdate)):
        os.mkdir(os.path.join('/Users/vysosuser/V20Data/AnalysisLogs', imageUTdate))
    logfile = os.path.join('/Users/vysosuser/V20Data/AnalysisLogs', imageUTdate, logfilename)

    im = SIDRE.ScienceImage(file, logfile=logfile, verbose=verbose)
    im.get_header_pointing()

    # Target Name
    image_info['target name'] = im.ccd.header.get('OBJECT', '')
    # Exposure Time
    image_info['exptime'] = float(im.ccd.header.get('EXPTIME', '-1'))
    # Exposure Start Time
    image_info['date'] = dt.strptime(im.ccd.header.get('DATE-OBS', 'unknown'), 
                                            '%Y-%m-%dT%H:%M:%S')
    # Filter
    if image_info['telescope'] == 'V5':
        image_info['filter'] = 'PSr'
    else:
        image_info['filter'] = im.ccd.header.get('FILTER', 'unknown')

    # Moon
    try:
        image_info['moon_alt'] = ((im.moon.transform_to(im.altazframe).alt).to(u.degree)).value
        if im.wcs_pointing is not None:
            image_info['moon_separation'] = (im.moon.separation(im.wcs_pointing).to(u.degree)).value
        else:
            image_info['moon_separation'] = (im.moon.separation(im.header_pointing).to(u.degree)).value
    except:
        pass


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
    im.solve_astrometry(downsample=2, SIPorder=4)
    perr = im.calculate_pointing_error()
    try:
        image_info['perr_arcmin']=perr.to(u.arcmin).value
        image_info['header_RA']=im.header_pointing.ra.deg
        image_info['header_DEC']=im.header_pointing.dec.deg
        image_info['RA']=im.wcs_pointing.ra.deg
        image_info['DEC']=im.wcs_pointing.dec.deg
        image_info['alt'] = im.header_altaz.alt.deg
        image_info['az'] = im.header_altaz.az.deg
        image_info['airmass'] = 1./np.cos( (90.-im.header_altaz.alt.deg)*np.pi/180. )
    except:
        pass


    ## Determine Typical FWHM
    im.extract()
    im.determine_FWHM()
    image_info['FWHM_pix'] = im.FWHM_pix
    image_info['ellipticity'] = im.ellipticity


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


    image_info['analyzed']=True
    image_info['SIDREversion']=SIDRE.version.version

    if nographics is True:
        fulljpeg = None
        cropjpeg = None
    else:
        fulljpeg = 'test_PS.jpg'
        cropjpeg = None
        im.render_jpeg(jpegfilename=fulljpeg,
                       overplot_assoc=False, overplot_pointing=True)
    
    if record:
        im.log.info('Connecting to mongo db at 192.168.1.101')
        try:
            client = pymongo.MongoClient('192.168.1.101', 27017)
            db = client.vysos
            images = db['images']
        except:
            im.log.error('Could not connect to mongo db')
            raise Exception('Failed to connect to mongo')
        else:
            # Remove old entries for this image file
            deletion = images.delete_many( {'filename': os.path.basename(file)} )
            im.log.info(f'  Deleted {deletion.deleted_count} previous entries for {os.path.basename(file)}')
            # Save JPEG to MongoDB
#             if nographics is False:
#                 if fulljpeg is not None:
#                     im.log.info('  Saving full frame JPEG')
#                     with open(fulljpeg, 'rb') as imageData:
#                         image_bytes = imageData.read()
#                         with tempfile.TemporaryFile() as f:
#                             f.write(bytearray(image_bytes))
#                             f.flush()
#                             f.seek(0)
#                             image_info.full_field_jpeg.put(f)
#                 if cropjpeg is not None:
#                     im.log.info('  Saving crop frame JPEG')
#                     with open(cropjpeg, 'rb') as imageData:
#                         image_bytes = imageData.read()
#                         with tempfile.TemporaryFile() as f:
#                             f.write(bytearray(image_bytes))
#                             f.flush()
#                             f.seek(0)
#                             image_info.cropped_jpeg.put(f)

            # Save new entry for this image file
            im.log.debug('Adding image info to mongo database')
            ## Save document
            try:
                inserted_id = images.insert_one(image_info).inserted_id
                im.log.info("  Inserted document id: {}".format(inserted_id))
            except:
                e = sys.exc_info()[0]
                im.log.error('Failed to add new document')
                im.log.error(e)
            client.close()



    else:
        print(image_info)

    tock = dt.utcnow()
    elapsed = (tock-tick).total_seconds()
    im.log.info(f'Processing time = {elapsed:.1f} s')
    im.__del__()


def main():
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    parser = ArgumentParser(description="Script to analyze a single FITS image")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    parser.add_argument("-p", "--print",
        action="store_true", dest="printonly",
        default=False, help="Print results only, do not record to database.")
    parser.add_argument("-n", "--no-graphics",
        action="store_true", dest="nographics",
        default=False, help="Turn off generation of graphics")
    ## add arguments
    parser.add_argument("filename",
        type=str,
        help="File Name of Input Image File")
    args = parser.parse_args()

    measure_image(args.filename,
                  nographics=args.nographics,
                  record=not args.printonly,
                  verbose=args.verbose)


if __name__ == '__main__':
    main()
