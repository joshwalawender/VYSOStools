import sys
import os
from argparse import ArgumentParser
import time
from datetime import datetime as dt
from datetime import timedelta as tdelta
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, MinuteLocator, DateFormatter
plt.style.use('classic')
import pymongo

import ephem
from astropy.io import ascii
import astropy.units as u
from astropy.table import Table, Column, Row

from VYSOS import Telescope, weather_limits


def query_mongo(db, collection, query):
    if collection == 'weather':
        names=('date', 'temp', 'clouds', 'wind', 'gust', 'rain', 'safe')
        dtype=(dt, np.float, np.float, np.float, np.float, np.int, np.bool)
    elif collection == 'V20status':
        names=('date', 'focuser_temperature', 'primary_temperature',
               'secondary_temperature', 'truss_temperature',
               'focuser_position', 'fan_speed',
               'alt', 'az', 'RA', 'DEC', 
              )
        dtype=(dt, np.float, np.float, np.float, np.float, np.int, np.int,
               np.float, np.float, np.float, np.float)
    elif collection == 'images':
        names=('date', 'telescope', 'moon_separation', 'perr_arcmin',
               'airmass', 'FWHM_pix', 'ellipticity')
        dtype=(dt, np.str, np.float, np.float, np.float, np.float, np.float)

    result = Table(names=names, dtype=dtype)
    for entry in db[collection].find(query):
        insert = {}
        for name in names:
            if name in entry.keys():
                insert[name] = entry[name]
        result.add_row(insert)
    return result


def make_plots(date_string, telescope, l):
    l.info(f"Making Nightly Plots for {telescope} on {date_string}")
    telname = {'V20':'VYSOS-20', 'V5':'VYSOS-5'}

    hours = HourLocator(byhour=range(24), interval=1)
    mins = MinuteLocator(range(0,60,15))

    start = dt.strptime(date_string, '%Y%m%dUT')
    end = start + tdelta(1)
    night_plot_file_name = '{}_{}.png'.format(date_string, telescope)
    hours_fmt = DateFormatter('%H')

    if end > dt.utcnow():
        end = dt.utcnow()

    ##------------------------------------------------------------------------
    ## Set up pathnames and filenames
    ##------------------------------------------------------------------------
    tel = Telescope(telescope)
    destination_path = os.path.abspath('/var/www/nights/')
    night_plot_file = os.path.join(destination_path, night_plot_file_name)

    ##------------------------------------------------------------------------
    ## Use pyephem determine sunrise and sunset times
    ##------------------------------------------------------------------------
    Observatory = ephem.Observer()
    Observatory.lon = "-155:34:33.9"
    Observatory.lat = "+19:32:09.66"
    Observatory.elevation = 3400.0
    Observatory.temp = 10.0
    Observatory.pressure = 680.0
    Observatory.date = start.strftime('%Y/%m/%d 10:00:00')

    Observatory.horizon = '0.0'
    sunset  = Observatory.previous_setting(ephem.Sun()).datetime()
    sunrise = Observatory.next_rising(ephem.Sun()).datetime()
    Observatory.horizon = '-6.0'
    evening_civil_twilight = Observatory.previous_setting(ephem.Sun(),
                             use_center=True).datetime()
    morning_civil_twilight = Observatory.next_rising(ephem.Sun(),
                             use_center=True).datetime()
    Observatory.horizon = '-12.0'
    evening_nautical_twilight = Observatory.previous_setting(ephem.Sun(),
                                use_center=True).datetime()
    morning_nautical_twilight = Observatory.next_rising(ephem.Sun(),
                                use_center=True).datetime()
    Observatory.horizon = '-18.0'
    evening_astronomical_twilight = Observatory.previous_setting(ephem.Sun(),
                                    use_center=True).datetime()
    morning_astronomical_twilight = Observatory.next_rising(ephem.Sun(),
                                    use_center=True).datetime()

    plot_start = sunset - tdelta(0, 1800)
    plot_end = sunrise + tdelta(0, 1800)

    ##------------------------------------------------------------------------
    ## Get weather, telescope status, and image data from database
    ##------------------------------------------------------------------------
    client = pymongo.MongoClient(tel.mongo_address, tel.mongo_port)
    db = client[tel.mongo_db]
    
    l.info(f"Querying database for images")
    images = query_mongo(db, 'images', {'date': {'$gt':start, '$lt':end}, 'telescope':telescope } )
    l.info(f"  Found {len(images)} image entries")
    
    l.info(f"Querying database for V20status")
    status = query_mongo(db, 'V20status', {'date': {'$gt':start, '$lt':end} } )
    l.info(f"  Found {len(status)} status entries")
    
    l.info(f"Querying database for weather")
    weather = query_mongo(db, 'weather', {'date': {'$gt':start, '$lt':end} } )
    l.info(f"  Found {len(weather)} weather entries")


    ##------------------------------------------------------------------------
    ## Make Nightly Sumamry Plot (show only night time)
    ##------------------------------------------------------------------------
    time_ticks_values = np.arange(sunset.hour,sunrise.hour+1)
    
    if telescope == "V20":
        plot_positions = [ ( [0.000, 0.755, 0.465, 0.245], [0.535, 0.760, 0.465, 0.240] ),
                           ( [0.000, 0.550, 0.465, 0.180], [0.535, 0.495, 0.465, 0.240] ),
                           ( [0.000, 0.490, 0.465, 0.050], [0.535, 0.245, 0.465, 0.240] ),
                           ( [0.000, 0.210, 0.465, 0.250], [0.535, 0.000, 0.465, 0.235] ),
                           ( [0.000, 0.000, 0.465, 0.200], None                         ) ]


    l.info("Writing Output File: {}".format(night_plot_file_name))
    dpi=100
    Figure = plt.figure(figsize=(13,9.5), dpi=dpi)

    ##------------------------------------------------------------------------
    ## Temperatures
    ##------------------------------------------------------------------------
    t = plt.axes(plot_positions[0][0])
    plt.title(f"Temperatures for {telescope} on the Night of {date_string}")
    l.info('Adding temperature plot')

    l.debug('  Adding ambient temp to plot')
    t.plot_date(weather['date'], weather['temp']*9/5+32, 'k-',
                     markersize=2, markeredgewidth=0, drawstyle="default",
                     label="Outside Temp")

    l.debug('  Adding focuser temp to plot')
    t.plot_date(status['date'], status['focuser_temperature']*9/5+32, 'r-',
                     markersize=2, markeredgewidth=0,
                     label="Focuser Temp")

    l.debug('  Adding primary temp to plot')
    t.plot_date(status['date'], status['primary_temperature']*9/5+32, 'b-',
                     markersize=2, markeredgewidth=0,
                     label="Primary Temp")

    l.debug('  Adding secondary temp to plot')
    t.plot_date(status['date'], status['secondary_temperature']*9/5+32, 'g-',
                     markersize=2, markeredgewidth=0,
                     label="Secondary Temp")

    l.debug('  Adding truss temp to plot')
    t.plot_date(status['date'], status['truss_temperature']*9/5+32, 'k-',
                     alpha=0.5,
                     markersize=2, markeredgewidth=0,
                     label="Truss Temp")

    t.xaxis.set_major_locator(hours)
    t.xaxis.set_major_formatter(hours_fmt)

    ## Overplot Twilights
    plt.axvspan(sunset, evening_civil_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.1)
    plt.axvspan(evening_civil_twilight, evening_nautical_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.2)
    plt.axvspan(evening_nautical_twilight, evening_astronomical_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.3)
    plt.axvspan(evening_astronomical_twilight, morning_astronomical_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.5)
    plt.axvspan(morning_astronomical_twilight, morning_nautical_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.3)
    plt.axvspan(morning_nautical_twilight, morning_civil_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.2)
    plt.axvspan(morning_civil_twilight, sunrise,
                ymin=0, ymax=1, color='blue', alpha=0.1)

    plt.legend(loc='best', prop={'size':10})
    plt.ylabel("Temperature (F)")
    plt.xlim(plot_start, plot_end)
    plt.ylim(28,87)
    plt.grid(which='major', color='k')

    ##------------------------------------------------------------------------
    ## Temperature Differences (V20 Only)
    ##------------------------------------------------------------------------
    if telescope == "V20" :
        l.info('Adding temperature difference plot')
        d = plt.axes(plot_positions[1][0])

        from scipy import interpolate
        xw = [(x-weather['date'][0]).total_seconds() for x in weather['date']]
        outside = interpolate.interp1d(xw, weather['temp'],
                                       fill_value='extrapolate')
        xs = [(x-status['date'][0]).total_seconds() for x in status['date']]

        pdiff = status['primary_temperature'] - outside(xs)
        d.plot_date(status['date'], 9/5*pdiff, 'b-',
                         markersize=2, markeredgewidth=0,
                         label="Primary")
        sdiff = status['secondary_temperature'] - outside(xs)
        d.plot_date(status['date'], 9/5*sdiff, 'g-',
                         markersize=2, markeredgewidth=0,
                         label="Secondary")
        fdiff = status['focuser_temperature'] - outside(xs)
        d.plot_date(status['date'], 9/5*fdiff, 'r-',
                         markersize=2, markeredgewidth=0,
                         label="Focuser")
        tdiff = status['truss_temperature'] - outside(xs)
        d.plot_date(status['date'], 9/5*tdiff, 'k-', alpha=0.5,
                         markersize=2, markeredgewidth=0,
                         label="Truss")
        d.plot_date(status['date'], [0]*len(status), 'k-')
        d.xaxis.set_major_locator(hours)
        d.xaxis.set_major_formatter(hours_fmt)
        d.xaxis.set_ticklabels([])
        plt.xlim(plot_start, plot_end)
        plt.ylim(-7,17)
        plt.ylabel("Difference (F)")
        plt.grid(which='major', color='k')
#         plt.legend(loc='best', prop={'size':10})


    ##------------------------------------------------------------------------
    ## Fan State/Power (V20 Only)
    ##------------------------------------------------------------------------
    if telescope == "V20":
        l.info('Adding fan state/power plot')
        f = plt.axes(plot_positions[2][0])
        f.plot_date(status['date'], status['fan_speed'], 'b-', \
                             label="Mirror Fans")
        f.xaxis.set_major_locator(hours)
        f.xaxis.set_major_formatter(hours_fmt)
        f.xaxis.set_ticklabels([])
        plt.xlim(plot_start, plot_end)
        plt.ylim(-10,110)
        plt.yticks(np.linspace(0,100,3,endpoint=True))
        plt.ylabel('Fan (%)')
        plt.grid(which='major', color='k')

    ##------------------------------------------------------------------------
    ## FWHM
    ##------------------------------------------------------------------------
    l.info('Adding FWHM plot')
    f = plt.axes(plot_positions[3][0])
    plt.title(f"Image Quality for {telescope} on the Night of {date_string}")

    fwhm = images['FWHM_pix']*u.pix * tel.pixel_scale
    f.plot_date(images['date'], fwhm, 'ko',
                     markersize=3, markeredgewidth=0,
                     label="FWHM")
    f.xaxis.set_major_locator(hours)
    f.xaxis.set_major_formatter(hours_fmt)
    f.xaxis.set_ticklabels([])
    plt.ylabel(f"FWHM (arcsec)")
    plt.xlim(plot_start, plot_end)
    plt.ylim(0,10)
    plt.grid(which='major', color='k')

    ##------------------------------------------------------------------------
    ## ellipticity
    ##------------------------------------------------------------------------
    l.info('Adding ellipticity plot')
    e = plt.axes(plot_positions[4][0])
    e.plot_date(images['date'], images['ellipticity'], 'ko',
                     markersize=3, markeredgewidth=0,
                     label="ellipticity")
    e.xaxis.set_major_locator(hours)
    e.xaxis.set_major_formatter(hours_fmt)
    plt.ylabel(f"ellipticity")
    plt.xlim(plot_start, plot_end)
    plt.ylim(0.95,1.75)
    plt.grid(which='major', color='k')

    ##------------------------------------------------------------------------
    ## Cloudiness
    ##------------------------------------------------------------------------
    l.info('Adding cloudiness plot')
    c = plt.axes(plot_positions[0][1])
    plt.title(f"Cloudiness")
    l.debug('  Adding sky temp to plot')
    c.plot_date(weather['date'], weather['clouds']*9/5+32, 'k-',
                     markersize=2, markeredgewidth=0,
                     label="Sky Temp")
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']<weather_limits['Cloudiness (C)'][0],
#                      color='green', alpha=0.5)
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']<weather_limits['Cloudiness (C)'][1],
#                      color='yellow', alpha=0.8)
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']>weather_limits['Cloudiness (C)'][1],
#                      color='red', alpha=0.8)
    c.xaxis.set_major_locator(hours)
    c.xaxis.set_major_formatter(hours_fmt)

    ## Overplot Twilights
    plt.axvspan(sunset, evening_civil_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.1)
    plt.axvspan(evening_civil_twilight, evening_nautical_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.2)
    plt.axvspan(evening_nautical_twilight, evening_astronomical_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.3)
    plt.axvspan(evening_astronomical_twilight, morning_astronomical_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.5)
    plt.axvspan(morning_astronomical_twilight, morning_nautical_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.3)
    plt.axvspan(morning_nautical_twilight, morning_civil_twilight,
                ymin=0, ymax=1, color='blue', alpha=0.2)
    plt.axvspan(morning_civil_twilight, sunrise,
                ymin=0, ymax=1, color='blue', alpha=0.1)

    plt.ylabel("Cloudiness (F)")
    plt.xlim(plot_start, plot_end)
    plt.ylim(-130,10)
    plt.grid(which='major', color='k')

    ## Overplot Moon Up Time
    TheMoon = ephem.Moon()
    moon_alts = []
    moon_phases = []
    moon_time_list = []
    moon_time = plot_start
    while moon_time <= plot_end:
        Observatory.date = moon_time
        TheMoon.compute(Observatory)
        moon_time_list.append(moon_time)
        moon_alts.append(TheMoon.alt * 180. / ephem.pi)
        moon_phases.append(TheMoon.phase)
        moon_time += tdelta(0, 60*5)
    moon_phase = max(moon_phases)
    moon_fill = moon_phase/100.*0.4+0.05

    mc_axes = c.twinx()
    mc_axes.set_ylabel('Moon Alt (%.0f%% full)' % moon_phase, color='y')
    mc_axes.plot_date(moon_time_list, moon_alts, 'y-')
    mc_axes.xaxis.set_major_locator(hours)
    mc_axes.xaxis.set_major_formatter(hours_fmt)
    plt.ylim(0,100)
    plt.yticks([10,30,50,70,90], color='y')
    plt.xlim(plot_start, plot_end)
    plt.fill_between(moon_time_list, 0, moon_alts, where=np.array(moon_alts)>0,
                     color='yellow', alpha=moon_fill)        
    plt.ylabel('')





    ##------------------------------------------------------------------------
    ## Humidity, Wetness, Rain
    ##------------------------------------------------------------------------
    l.info('Adding rain plot')
    r = plt.axes(plot_positions[1][1])
    r.plot_date(weather['date'], weather['rain'], 'k-',
                     markersize=2, markeredgewidth=0,
                     label="Rain")
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']<weather_limits['Cloudiness (C)'][0],
#                      color='green', alpha=0.5)
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']<weather_limits['Cloudiness (C)'][1],
#                      color='yellow', alpha=0.8)
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']>weather_limits['Cloudiness (C)'][1],
#                      color='red', alpha=0.8)
    r.xaxis.set_major_locator(hours)
    r.xaxis.set_major_formatter(hours_fmt)
    r.xaxis.set_ticklabels([])
    plt.ylabel("Rain")
    plt.xlim(plot_start, plot_end)
    plt.ylim(-100,3000)
    plt.grid(which='major', color='k')

    ##------------------------------------------------------------------------
    ## Wind Speed
    ##------------------------------------------------------------------------
    l.info('Adding wind speed plot')
    w = plt.axes(plot_positions[2][1])

    w.plot_date(weather['date'], weather['wind'], 'k-',
                     markersize=2, markeredgewidth=0,
                     label="Wind")
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']<weather_limits['Cloudiness (C)'][0],
#                      color='green', alpha=0.5)
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']<weather_limits['Cloudiness (C)'][1],
#                      color='yellow', alpha=0.8)
#     plt.fill_between(weather['date'], -140, weather['clouds'],
#                      where=weather['clouds']>weather_limits['Cloudiness (C)'][1],
#                      color='red', alpha=0.8)
    w.xaxis.set_major_locator(hours)
    w.xaxis.set_major_formatter(hours_fmt)
    w.xaxis.set_ticklabels([])
    plt.ylabel("Wind (kph)")
    plt.xlim(plot_start, plot_end)
    plt.ylim(-5,150)
    plt.grid(which='major', color='k')



    l.info('Saving figure: {}'.format(night_plot_file))
    plt.savefig(night_plot_file, dpi=dpi, bbox_inches='tight', pad_inches=0.10)
    l.info('Done.')




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
    parser.add_argument("-l", "--loop",
        action="store_true", dest="loop",
        default=False, help="Make plots in continuous loop")
    ## add arguments
    parser.add_argument("-t", dest="telescope",
        required=False, type=str,
        help="Telescope which took the data ('V5' or 'V20')")
    parser.add_argument("-d", dest="date",
        required=False, type=str,
        help="Date of night to plot")
    args = parser.parse_args()

    if args.date is None:
        args.date = dt.utcnow().strftime("%Y%m%dUT")

    ##-------------------------------------------------------------------------
    ## Create Logger Object
    ##-------------------------------------------------------------------------
    l = logging.getLogger('make_nightly_plots')
    l.setLevel(logging.DEBUG)
    ## Set up console output
    LogConsoleHandler = logging.StreamHandler()
    if args.verbose:
        LogConsoleHandler.setLevel(logging.DEBUG)
    else:
        LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
    LogConsoleHandler.setFormatter(LogFormat)
    l.addHandler(LogConsoleHandler)
    ## Set up file output
#     LogFilePath = os.path.join()
#     if not os.path.exists(LogFilePath):
#         os.mkdir(LogFilePath)
#     LogFile = os.path.join(LogFilePath, 'get_status.log')
#     LogFileHandler = logging.FileHandler(LogFile)
#     LogFileHandler.setLevel(logging.DEBUG)
#     LogFileHandler.setFormatter(LogFormat)
#     l.addHandler(LogFileHandler)

    make_plots(args.date, args.telescope, l)

#     if args.loop is True:
#         while True:
#             ## Set date to tonight
#             now = dt.utcnow()
#             date_string = now.strftime("%Y%m%dUT")
#             make_plots(date_string, 'V5', logger)
#             make_plots(date_string, 'V5', logger, recent=True)
#             make_plots(date_string, 'V20', logger)
#             make_plots(date_string, 'V20', logger, recent=True)
#             time.sleep(120)
#     else:
#         if args.telescope:
#             make_plots(args.date, args.telescope, logger, recent=recent)
#         else:
#             make_plots(args.date, 'V5', logger)
#             if recent:
#                 make_plots(args.date, 'V5', logger, recent=True)
#             make_plots(args.date, 'V20', logger)
#             if recent:
#                 make_plots(args.date, 'V20', logger, recent=True)


if __name__ == '__main__':
    main()