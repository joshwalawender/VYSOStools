import sys
import os
from argparse import ArgumentParser
import re
import string
from datetime import datetime as dt
from datetime import timedelta as tdelta
import logging
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, DateFormatter
import pymongo
from pymongo import MongoClient

import ephem
from astropy.io import ascii
from astropy import table
import IQMon

def make_plots(date_string, telescope, logger):
    logger.info("#### Making Nightly Plots for "+telescope+" on the Night of "+date_string+" ####")
    telname = {'V20':'VYSOS-20', 'V5':'VYSOS-5'}
    y = date_string[0:4]
    m = date_string[4:6]
    d = date_string[6:8]

    ##------------------------------------------------------------------------
    ## Set up pathnames and filenames
    ##------------------------------------------------------------------------
    config_file = os.path.join(os.path.expanduser('~'), 'IQMon', 'VYSOS{}.yaml'.format(telescope[1:]))
    tel = IQMon.Telescope(config_file)
    destination_path = os.path.abspath('/var/www/')

    ##------------------------------------------------------------------------
    ## Use pyephem determine sunrise and sunset times
    ##------------------------------------------------------------------------
    Observatory = ephem.Observer()
    Observatory.lon = "-155:34:33.9"
    Observatory.lat = "+19:32:09.66"
    Observatory.elevation = 3400.0
    Observatory.temp = 10.0
    Observatory.pressure = 680.0
    Observatory.date = '{}/{}/{} 10:00:00'.format(y, m, d)

    Observatory.horizon = '0.0'
    sunset  = Observatory.previous_setting(ephem.Sun()).datetime()
    sunrise = Observatory.next_rising(ephem.Sun()).datetime()
    Observatory.horizon = '-6.0'
    evening_civil_twilight = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    morning_civil_twilight = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
    Observatory.horizon = '-12.0'
    evening_nautical_twilight = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    morning_nautical_twilight = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()
    Observatory.horizon = '-18.0'
    evening_astronomical_twilight = Observatory.previous_setting(ephem.Sun(), use_center=True).datetime()
    morning_astronomical_twilight = Observatory.next_rising(ephem.Sun(), use_center=True).datetime()

    Observatory.date = '{}/{}/{} 0:00:01.0'.format(y, m, d)
    TheMoon = ephem.Moon()
    TheMoon.compute(Observatory)
    moonset  = Observatory.next_setting(ephem.Moon()).datetime()
    moonrise = Observatory.next_rising(ephem.Moon()).datetime()
    
    moon_time_list = [dt(int(y), int(m), int(d), int(math.floor(min/60)), int(min)%60, 0)\
                      for min in np.arange(0,24*60,6)]
    moon_alts = []
    for moon_time in moon_time_list:
        Observatory.date = moon_time.strftime('%Y/%m/%d %H:%M:%S')
        TheMoon.compute(Observatory)
        moon_alts.append(TheMoon.alt * 180. / ephem.pi)
    ## Determine time of max alt for moon
    moon_peak_alt = max(moon_alts)
    moon_peak_time = moon_time_list[moon_alts.index(moon_peak_alt)]
    Observatory.date = moon_peak_time.strftime('%Y/%m/%d %H:%M:%S')
    TheMoon.compute(Observatory)
    moon_phase = TheMoon.phase
    moon_fill = moon_phase/100.*0.5+0.05

    ##------------------------------------------------------------------------
    ## Get status and IQMon results
    ##------------------------------------------------------------------------
    client = MongoClient('192.168.1.101', 27017)
    status = client.vysos['{}status'.format(telescope)]
    images = client.vysos['{}images'.format(telescope)]

    ##------------------------------------------------------------------------
    ## Make Nightly Sumamry Plot (show only night time)
    ##------------------------------------------------------------------------
    night_plot_file_name = '{}_{}.png'.format(date_string, telescope)
    night_plot_file = os.path.join(destination_path, night_plot_file_name)
    UTstart = 0
    UTend = 24
    hours = HourLocator(byhour=range(24), interval=2)
    hours_fmt = DateFormatter('%H')

    now = dt.utcnow()
    now_string = now.strftime("%Y%m%dUT")

    if (date_string != now_string) or (now > sunset):
        time_ticks_values = np.arange(sunset.hour,sunrise.hour+1)
        
        if telescope == "V20":
            plot_positions = [ ( [0.000, 0.760, 0.465, 0.240], [0.535, 0.760, 0.465, 0.240] ),
                               ( [0.000, 0.580, 0.465, 0.155], [0.535, 0.495, 0.465, 0.240] ),
                               ( [0.000, 0.495, 0.465, 0.075], [0.535, 0.245, 0.465, 0.240] ),
                               ( [0.000, 0.330, 0.465, 0.155], [0.535, 0.000, 0.465, 0.235] ),
                               ( [0.000, 0.165, 0.465, 0.155], None                         ),
                               ( [0.000, 0.000, 0.465, 0.155], None                         ) ]
        if telescope == "V5":
            plot_positions = [ ( [0.000, 0.760, 0.465, 0.240], [0.535, 0.760, 0.465, 0.240] ),
                               ( None                        , [0.535, 0.495, 0.465, 0.240] ),
                               ( None                        , [0.535, 0.245, 0.465, 0.240] ),
                               ( [0.000, 0.495, 0.465, 0.240], [0.535, 0.000, 0.465, 0.235] ),
                               ( [0.000, 0.245, 0.465, 0.240], None                         ),
                               ( [0.000, 0.000, 0.465, 0.235], None                         ) ]

        logger.info("Writing Output File: {}".format(night_plot_file_name))
        dpi=100
        Figure = plt.figure(figsize=(13,9.5), dpi=dpi)

        ##------------------------------------------------------------------------
        ## Temperatures
        ##------------------------------------------------------------------------
        t_axes = plt.axes(plot_positions[0][0])
        plt.title("Weather and Results for {} on the Night of {}".format(telescope, date_string))

        ##------------------------------------------------------------------------
        ## Boltwood Temperature
        status_list = [entry for entry in\
                       status.find({'UT date':date_string,\
                                    'boltwood time':{'$exists':True},\
                                    'boltwood date':{'$exists':True},\
                                    'boltwood ambient temp':{'$exists':True},\
                                   }) ]
        logger.debug("  Found {} lines for boltwood temperature".format(len(status_list)))
        if len(status_list) > 1:
            time = [dt.strptime('{} {}'.format(entry['boltwood date'],\
                                               entry['boltwood time'][:-3]),\
                                               '%Y-%m-%d %H:%M:%S') + \
                    + tdelta(0, 10*60*60)\
                    for entry in status_list]
            ambient_temp = [x['boltwood ambient temp'] for x in status_list]
            logger.debug('  Adding Boltwood ambient temp to plot')
            t_axes.plot_date(time, ambient_temp, 'ko', \
                             markersize=2, markeredgewidth=0, drawstyle="default", \
                             label="Outside Temp")

        ##------------------------------------------------------------------------
        ## RCOS Temperature
        status_list = [entry for entry in\
                       status.find({'UT date':date_string,\
                                    'UT time':{'$exists':True},\
                                    'RCOS temperature (primary)':{'$exists':True},\
                                    'RCOS temperature (truss)':{'$exists':True},\
                                   }) ]
        logger.debug("  Found {} lines for RCOS temperatures".format(len(status_list)))
        if len(status_list) > 1:
            time = [dt.strptime('{} {}'.format(entry['UT date'],\
                                               entry['UT time']),\
                                               '%Y%m%dUT %H:%M:%S')
                    for entry in status_list]
            primary_temp = [x['RCOS temperature (primary)'] for x in status_list]
            truss_temp = [x['RCOS temperature (truss)'] for x in status_list]
            logger.debug('  Adding priamry mirror temp to plot')
            t_axes.plot_date(time, primary_temp, 'ro', \
                             markersize=2, markeredgewidth=0, drawstyle="default", \
                             label="Mirror Temp")
            logger.debug('  Adding truss temp to plot')
            t_axes.plot_date(time, truss_temp, 'go', \
                             markersize=2, markeredgewidth=0, drawstyle="default", \
                             label="Truss Temp")

        ##------------------------------------------------------------------------
        ## FocusMax Temperature
        status_list = [entry for entry in\
                       status.find({'UT date':date_string,\
                                    'UT time':{'$exists':True},\
                                    'FocusMax temperature (tube)':{'$exists':True},\
                                   }) ]
        logger.debug("  Found {} lines for FocusMax temperatures".format(len(status_list)))
        if len(status_list) > 1:
            time = [dt.strptime('{} {}'.format(entry['UT date'],\
                                               entry['UT time']),\
                                               '%Y%m%dUT %H:%M:%S')
                    for entry in status_list]
            FM_temp = [x['FocusMax temperature (tube)'] for x in status_list]
            logger.debug('  Adding FocusMax tube temp to plot')
            t_axes.plot_date(time, primary_temp, 'ro', \
                             markersize=2, markeredgewidth=0, drawstyle="default", \
                             label="Tube Temp")

            t_axes.xaxis.set_major_locator(hours)
            t_axes.xaxis.set_major_formatter(hours_fmt)

        ## Overplot Twilights
#         plt.axvspan(SunsetDecimal, EveningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)
#         plt.axvspan(EveningCivilTwilightDecimal, EveningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
#         plt.axvspan(EveningNauticalTwilightDecimal, EveningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
#         plt.axvspan(EveningAstronomicalTwilightDecimal, MorningAstronomicalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.5)
#         plt.axvspan(MorningAstronomicalTwilightDecimal, MorningNauticalTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.3)
#         plt.axvspan(MorningNauticalTwilightDecimal, MorningCivilTwilightDecimal, ymin=0, ymax=1, color='blue', alpha=0.2)
#         plt.axvspan(MorningCivilTwilightDecimal, SunriseDecimal, ymin=0, ymax=1, color='blue', alpha=0.1)


        plt.legend(loc='best', prop={'size':10})
        plt.ylabel("Temperature (F)")
        plt.xlabel("UT Time")
        logger.info('Saving figure: {}'.format(night_plot_file))
        plt.savefig(night_plot_file, dpi=dpi, bbox_inches='tight', pad_inches=0.10)







if __name__ == '__main__':
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
    parser.add_argument("-t", dest="telescope",
        required=True, type=str,
        help="Telescope which took the data ('V5' or 'V20')")
    parser.add_argument("-d", dest="date",
        required=True, type=str,
        help="Date of night to plot")
    args = parser.parse_args()

    ##-------------------------------------------------------------------------
    ## Create Logger Object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('make_nightly_plots')
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
#     LogFilePath = os.path.join()
#     if not os.path.exists(LogFilePath):
#         os.mkdir(LogFilePath)
#     LogFile = os.path.join(LogFilePath, 'get_status.log')
#     LogFileHandler = logging.FileHandler(LogFile)
#     LogFileHandler.setLevel(logging.DEBUG)
#     LogFileHandler.setFormatter(LogFormat)
#     logger.addHandler(LogFileHandler)


    make_plots(args.date, args.telescope, logger)
