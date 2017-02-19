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

import astropy.units as u
from astropy.table import Table, Column
from astropy.time import Time
from astropy.coordinates import EarthLocation
from astroplan import Observer


class weather(me.Document):
    querydate = me.DateTimeField(default=datetime.datetime.utcnow(), required=True)
    date = me.DateTimeField(required=True)
    current = me.BooleanField(default=True, required=True)
    clouds = me.DecimalField(precision=2)
    temp = me.DecimalField(precision=2)
    wind = me.DecimalField(precision=1)
    gust = me.DecimalField(precision=1)
    rain = me.IntField()
    light = me.IntField()
    switch = me.IntField()
    safe = me.BooleanField()

    meta = {'collection': 'weather',
            'indexes': ['current', 'querydate', 'date']}

    def __str__(self):
        output = 'MongoEngine Document at: {}\n'.format(self.querydate.strftime('%Y%m%d %H:%M:%S'))
        if self.date: output += '  Date: {}\n'.format(self.date.strftime('%Y%m%d %H:%M:%S'))
        if self.current: output += '  Current: {}\n'.format(self.current)
        if self.clouds: output += '  clouds: {:.2f}\n'.format(self.clouds)
        if self.temp: output += '  temp: {:.2f}\n'.format(self.temp)
        if self.wind: output += '  wind: {:.1f}\n'.format(self.wind)
        if self.gust: output += '  gust: {:.1f}\n'.format(self.gust)
        if self.rain: output += '  rain: {:.0f}\n'.format(self.rain)
        if self.light: output += '  light: {:.0f}\n'.format(self.light)
        if self.switch: output += '  switch: {}\n'.format(self.switch)
        if self.safe: output += '  safe: {}\n'.format(self.safe)
        return output

    def __repr__(self):
        return self.__str__()



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
    final = {'sunset': 0.1, 'ec': 0.2, 'en': 0.3, 'ea': 0.5, 'ma': 0.3, 'mn': 0.2, 'mc': 0.1, 'sunrise': 0.0}
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
    fig = plt.figure(figsize=(18,8), dpi=dpi)
    night_plot_file_name = 'weather.png'
    destination_path = os.path.abspath('/var/www/')
    night_plot_file = os.path.join(destination_path, night_plot_file_name)
    plot_positions = [ ( [0.060, 0.730, 0.600, 0.230], [0.700, 0.730, 0.290, 0.230] ),
                       ( [0.060, 0.480, 0.600, 0.230], [0.700, 0.480, 0.290, 0.230] ) ]


    ##-------------------------------------------------------------------------
    ## Temperature
    ##-------------------------------------------------------------------------
    for lr in range(2):
        temps = [(float(x.temp)*1.8+32.) for x in data]
        t_axes = plt.axes(plot_positions[0][lr])
        plt.title("Weather")
        t_axes.plot_date(time, temps, 'ko', \
                         markersize=2, markeredgewidth=0, drawstyle="default", \
                         label="Outside Temp")

        ## Overplot Twilights
        twilights = get_twilights(start, end)
        for i in range(len(twilights)-1):
            plt.axvspan(twilights[i][0], twilights[i+1][0], ymin=0, ymax=1,
                        color='blue', alpha=twilights[i+1][2])

        plt.legend(loc='best')
        plt.ylabel("Temperature (F)")
        if lr==0:
            plt.xlim(start, end)
            t_axes.xaxis.set_major_locator(HourLocator(byhour=range(24)))
            t_axes.xaxis.set_major_formatter(DateFormatter('%H'))
        elif lr==1:
            plt.xlim(end - tdelta(0,2*60*60), end)
            t_axes.xaxis.set_major_locator(HourLocator(byhour=range(24)))
            t_axes.xaxis.set_minor_locator(MinuteLocator(range(0,60,15)))
            t_axes.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        plt.ylim(28,87)
        plt.grid(which='major', color='k')
        plt.grid(which='minor', color='k', alpha=0.8)
        plt.xlabel("UT Time")


    ##-------------------------------------------------------------------------
    ## Cloudiness
    ##-------------------------------------------------------------------------
    for lr in range(2):
        clouds = [float(x.clouds) for x in data]
        t_axes = plt.axes(plot_positions[1][lr])
        t_axes.plot_date(time, clouds, 'ko', \
                         markersize=2, markeredgewidth=0, drawstyle="default", \
                         label="Cloudiness")

        plt.legend(loc='best')
        plt.ylabel("Cloudiness (C)")
        if lr==0:
            plt.xlim(start, end)
            t_axes.xaxis.set_major_locator(HourLocator(byhour=range(24)))
            t_axes.xaxis.set_major_formatter(DateFormatter('%H'))
        elif lr==1:
            plt.xlim(end - tdelta(0,2*60*60), end)
            t_axes.xaxis.set_major_locator(HourLocator(byhour=range(24)))
            t_axes.xaxis.set_minor_locator(MinuteLocator(range(0,60,15)))
            t_axes.xaxis.set_major_formatter(DateFormatter('%H:%M'))
        plt.ylim(-50,0)
        plt.grid(which='major', color='k')
        plt.grid(which='minor', color='k', alpha=0.8)
        plt.xlabel("UT Time")



    plt.savefig(night_plot_file, dpi=dpi)


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