import sys
import os
from argparse import ArgumentParser
from datetime import datetime as dt
from datetime import timedelta as tdelta
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, DateFormatter
import pymongo
from astropy.modeling import models, fitting
from astropy.table import Table



def correlate_temps():

    if not os.path.exists('tempcompdata.txt'):
        client = pymongo.MongoClient('192.168.1.101', 27017)
        db = client['vysos']
        images = db['V5.images']
        status = db['V5.status']

        results = images.find( {'FWHM pix': {'$lt': 2.0}} )

        tab = Table(names=('time', 'focuspos', 'tubetemp', 'ambtemp'),
                    dtype=('a25', 'i4', 'f4', 'f4'))
        for i,result in enumerate(results):
            when = result['exposure start']
            exptime = result['exposure time']
            telemetry = status.find( {'UT timestamp': {'$gte': when,
                                                       '$lte': when+tdelta(0,exptime)} } )
            if i in np.arange(0,results.count(),100):
                print('{:4d} {} {:d}'.format(i, when.isoformat(), telemetry.count()))
            try:
                assert 'FocusMax temperature (tube)' in telemetry[0].keys()
                assert 'boltwood ambient temp' in telemetry[0].keys()
                assert 'FocusMax focuser position' in telemetry[0].keys()
                row = {'time': when.isoformat(),
                       'focuspos': int(telemetry[0]['FocusMax focuser position']),
                       'tubetemp': float(telemetry[0]['FocusMax temperature (tube)']),
                       'ambtemp': float(telemetry[0]['boltwood ambient temp'])}
                tab.add_row(row)
            except:
                print('Failed on data at {}'.format(when.isoformat()))
        tab.write('tempcompdata.txt', format='ascii.csv')
    else:
        tab = Table.read('tempcompdata.txt', format='ascii.csv')

    time = [ dt.strptime(t, '%Y-%m-%dT%H:%M:%S') for t in tab['time'] ]


    # -------------------------------------------------------------------------
    # Plot correlation between tube and ambient temperature
    # -------------------------------------------------------------------------
    diff = tab['ambtemp'] - tab['tubetemp']
    line0 = models.Linear1D(slope=1, intercept=np.median(diff))
    line0.slope.fixed = True

#     fitter = fitting.LinearLSQFitter()
#     line = fitter(line0, tab['tubetemp'], tab['ambtemp'])
    line = line0


    plt.figure()
    plt.plot(tab['tubetemp'], tab['ambtemp'], 'bo', markersize=3, markeredgewidth=0)
    plt.plot(tab['tubetemp'], tab['ambtemp'], 'k-', alpha=0.3)
    plt.plot(tab['tubetemp'], line(tab['tubetemp']), 'g-',
             label='slope={:.1f}, intercept={:.1f}'.format(
                    line.slope.value, line.intercept.value) )
    plt.xlabel('FocusMax Temperature')
    plt.ylabel('Ambient Temperature')
    plt.grid()
    plt.legend(loc='best')
    plt.savefig('temperature_correlation_V5.png')


    # -------------------------------------------------------------------------
    # Plot focus position over time to check for discontinuities
    # -------------------------------------------------------------------------
    plt.figure()
    ax = plt.gca()
    plt.plot_date(time, tab['focuspos'], 'bo', markersize=3, markeredgewidth=0)
    plt.xlabel('Time')
    plt.ylabel('Focuser Position')
    days = DayLocator(interval=2)
    fmt = DateFormatter('%Y/%m/%d')
    ax.xaxis.set_major_locator(days)
    ax.xaxis.set_major_formatter(fmt)
    plt.grid()
    plt.savefig('focus_vs_time.png')


    # -------------------------------------------------------------------------
    # Plot focus position vs. tube temperature to determine compensation
    # -------------------------------------------------------------------------
    line0 = models.Linear1D()
    fitter = fitting.LinearLSQFitter()
    line = fitter(line0, tab['tubetemp'], tab['focuspos'])
    plt.figure()
    plt.scatter(tab['tubetemp'], tab['focuspos'], c=range(len(time)), norm=None, cmap='Blues')
    plt.plot(tab['tubetemp'], tab['focuspos'], 'k-', alpha=0.3)
    plt.plot(tab['tubetemp'], line(tab['tubetemp']), 'g-',
             label='slope={:.1f}, intercept={:.1f}'.format(
                    line.slope.value, line.intercept.value) )
    plt.xlabel('FocusMax Temperature')
    plt.ylabel('FocusMax Position')
    plt.grid()
    plt.legend(loc='best')
    plt.savefig('temperature_compensation_V5.png')



if __name__ == '__main__':
    correlate_temps()