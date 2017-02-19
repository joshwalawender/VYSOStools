import sys
import os
from argparse import ArgumentParser
import datetime
from datetime import datetime as dt
from datetime import timedelta as tdelta
import logging

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import HourLocator, MinuteLocator, DateFormatter

import mongoengine as me
from VYSOS.schema import weather

import astropy.units as u
from astropy.table import Table, Column
from astropy.time import Time
from astropy.coordinates import EarthLocation
from astroplan import Observer




def get_twilights(start, end):
    """ Determine sunrise and sunset times """
    location = EarthLocation(
        lat=+19.53602,
        lon=-155.57608,
        height=3400,
    )
    obs = Observer(location=location, name='VYSOS',
                   timezone='US/Hawaii')

    sunset = obs.sun_set_time(Time(start), which='next').datetime
    sunrise = obs.sun_rise_time(Time(start), which='next').datetime

    # Calculate and order twilights and set plotting alpha for each
    twilights = [(start, 'start', 0.0),
                 (sunset, 'sunset', 0.0),
                 (obs.twilight_evening_civil(Time(start),
                                             which='next').datetime, 'ec', 0.1),
                 (obs.twilight_evening_nautical(Time(start),
                                                which='next').datetime, 'en', 0.2),
                 (obs.twilight_evening_astronomical(Time(start),
                                                    which='next').datetime, 'ea', 0.3),
                 (obs.twilight_morning_astronomical(Time(start),
                                                    which='next').datetime, 'ma', 0.5),
                 (obs.twilight_morning_nautical(Time(start),
                                                which='next').datetime, 'mn', 0.3),
                 (obs.twilight_morning_civil(Time(start),
                                             which='next').datetime, 'mc', 0.2),
                 (sunrise, 'sunrise', 0.1),
                 ]

    twilights.sort(key=lambda x: x[0])
    final = {'sunset': 0.1, 'ec': 0.2, 'en': 0.3, 'ea': 0.5,
             'ma': 0.3, 'mn': 0.2, 'mc': 0.1, 'sunrise': 0.0}
    twilights.append((end, 'end', final[twilights[-1][1]]))

    return twilights





def plot_weather(date=None):
    '''
    Make plot of the last 24 hours of weather or, if keyword date is set, make
    plot of that UT day's weather.
    '''
    if not date:
        end = dt.utcnow()
    else:
        raise NotImplementedError

    start = end - tdelta(1,0)
    me.connect('vysos', host='192.168.1.101')
    data = weather.objects(__raw__={'date': {'$gt': start, '$lt': end}})
    time = [x.date for x in data]

    dpi=72
    fig = plt.figure(figsize=(14,6), dpi=dpi)
    night_plot_file_name = 'weather.png'
    destination_path = os.path.abspath('/var/www/')
    night_plot_file = os.path.join(destination_path, night_plot_file_name)
    plot_positions = [ [ [0.060, 0.700, 0.600, 0.220], [0.670, 0.700, 0.320, 0.220] ],
                       [ [0.060, 0.470, 0.600, 0.220], [0.670, 0.470, 0.320, 0.220] ],
                       [ [0.060, 0.240, 0.600, 0.220], [0.670, 0.240, 0.320, 0.220] ],
                       [ [0.060, 0.090, 0.600, 0.140], [0.670, 0.090, 0.320, 0.140] ],
                       [ [0.060, 0.020, 0.600, 0.060], [0.670, 0.020, 0.320, 0.060] ],
                     ]
    labels = ['Outside Temp', 'Cloudiness', 'Wind Speed (kph)', 'Rain', 'Safe']
    data = [ [(float(x.temp)*1.8+32.) for x in data],
             [float(x.clouds) for x in data],
             [float(x.wind) for x in data],
             [float(x.rain) for x in data],
             [float(x.safe) for x in data],
           ]
    ylims = [ (28,87),
              (-50,0),
              (0,170),
              (3000,0),
              (-0.25, 1.25),
            ]

    ##-------------------------------------------------------------------------
    ## Temperature
    ##-------------------------------------------------------------------------
    for i,label in enumerate(labels):
        print(label)
        for lr in range(2):
            t_axes = plt.axes(plot_positions[i][lr])
            t_axes.plot_date(time, data[i], 'ko', \
                             markersize=2, markeredgewidth=0, drawstyle="default", \
                             label=label)
            if label == 'Safe':
                plt.bar(time, data[i], color='g', edgecolor='g', linewidth=0, alpha=0.6)
            ## Overplot Twilights
            twilights = get_twilights(start, end)
            for j in range(len(twilights)-1):
                plt.axvspan(twilights[j][0], twilights[j+1][0], ymin=0, ymax=1,
                            color='blue', alpha=twilights[j+1][2])
            if lr==0:
                if i==0:
                    plt.title('Weather (at {})'.format(end.strftime('%Y/%m/%d %H:%M:%S UT')))
                plt.ylabel(label)
                plt.xlim(start, end)
                t_axes.xaxis.set_major_locator(HourLocator(byhour=range(24)))
                if label == 'Rain':
                    t_axes.get_yaxis().set_ticklabels([])
                if i == len(labels)-1:
                    t_axes.set_yticks([])
                    t_axes.get_yaxis().set_ticklabels([])
                    t_axes.xaxis.set_major_formatter(DateFormatter('%H'))
                else:
                    plt.legend(loc='best')
                    plt.grid(which='major', color='k')
                    plt.grid(which='minor', color='k', alpha=0.8)
                    t_axes.xaxis.set_major_formatter(plt.NullFormatter())
            elif lr==1:
                plt.xlim(end - tdelta(0,1.25*60*60), end)
                t_axes.get_xaxis().set_ticklabels([])
                t_axes.get_yaxis().set_ticklabels([])
                t_axes.xaxis.set_major_locator(HourLocator(byhour=range(24)))
                t_axes.xaxis.set_minor_locator(MinuteLocator(range(0,60,15)))
                if i == len(labels)-1:
                    t_axes.set_yticks([])
                    t_axes.xaxis.set_major_formatter(DateFormatter('%H:%M'))
                else:
                    plt.grid(which='major', color='k')
                    plt.grid(which='minor', color='k', alpha=0.8)
                    t_axes.xaxis.set_major_formatter(plt.NullFormatter())
            plt.ylim(ylims[i])
            if i == len(labels)-1:
                plt.xlabel("UT Time")

    plt.savefig(night_plot_file, dpi=dpi, bbox_inches='tight')


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
    parser.add_argument("-d", dest="date",
        required=False, type=str,
        help="Date of night to plot in YYYYMMDDUT format")
    args = parser.parse_args()

    if not args.date:
        args.date = dt.utcnow().strftime("%Y%m%dUT")

    if args.loop:
        while True:
            ## Set date to tonight
            now = dt.utcnow()
            date_string = now.strftime("%Y%m%dUT")
            plot_weather()
            time.sleep(120)
    else:
        plot_weather()


if __name__ == '__main__':
    main()