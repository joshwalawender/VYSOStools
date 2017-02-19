#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging

from astropy.io import fits
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_moon

##-------------------------------------------------------------------------
## check_moon
##-------------------------------------------------------------------------
def check_moon(file, avoid=30.*u.degree):
    if not isinstance(avoid, u.Quantity):
        avoid = float(avoid)*u.degree
    else:
        avoid = avoid.to(u.degree)

    header = fits.getheader(file)

    mlo = EarthLocation.of_site('Keck Observatory') # Update later
    obstime = Time(header['DATE-OBS'], format='isot', scale='utc', location=mlo)
    moon = get_moon(obstime, mlo)

    if 'RA' in header.keys() and 'DEC' in header.keys():
        coord_string = '{} {}'.format(header['RA'], header['DEC'])
        target = SkyCoord(coord_string, unit=(u.hourangle, u.deg))
    else:
        ## Assume zenith
        target = SkyCoord(obstime.sidereal_time('apparent'), mlo.latitude)

    moon_alt = moon.transform_to(AltAz(obstime=obstime, location=mlo)).alt.to(u.deg)
    if moon_alt < 0*u.degree:
        print('Moon is down')
        return True
    else:
        sep = target.separation(moon)
        print('Moon is up. Separation = {:.1f} deg'.format(sep.to(u.degree).value))
        return (sep > avoid)

##-------------------------------------------------------------------------
## Main Program
##-------------------------------------------------------------------------
def main():

    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = argparse.ArgumentParser(
             description="Program description.")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    ## add arguments
    parser.add_argument(
        type=str, dest="file",
        help="The fits file to check")
    parser.add_argument("-a", "--avoid",
        type=float, dest="avoid",
        default=30.,
        help="The avoidance angle in degrees to evaluate")
    args = parser.parse_args()

    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('MyLogger')
    logger.setLevel(logging.DEBUG)
    ## Set up console output
    LogConsoleHandler = logging.StreamHandler()
    if args.verbose:
        LogConsoleHandler.setLevel(logging.DEBUG)
    else:
        LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)
    ## Set up file output
#     LogFileName = None
#     LogFileHandler = logging.FileHandler(LogFileName)
#     LogFileHandler.setLevel(logging.DEBUG)
#     LogFileHandler.setFormatter(LogFormat)
#     logger.addHandler(LogFileHandler)

    check_moon(args.file, avoid=args.avoid)


if __name__ == '__main__':
    main()
