import sys
import os
import logging
import argparse
from datetime import datetime as dt
from datetime import timedelta as tdelta
from time import sleep
import pymongo
import numpy as np
# import requests

# import mongoengine as me
# from VYSOS.schema import weather, currentweather

##-------------------------------------------------------------------------
## Query AAG Solo for Weather Data
##-------------------------------------------------------------------------
def get_weather(logger, robust=True):
    logger.info('Getting Weather status from PANOPTES')

    now = dt.utcnow()
    end = now + tdelta(0,900)
    start = end - tdelta(0,3600)

    pan001_client = pymongo.MongoClient('192.168.1.50', 27017)
    pan001_db = pan001_client.panoptes
    pan001_weather = pan001_db.weather
    pan001_data = [x for x in pan001_weather.find({'date': {'$gt': start, '$lt': end}},
                                    sort=[('date', pymongo.DESCENDING)])]
    latest = pan001_data[0]

    weatherdoc = {"date": latest['date'],
                  "querydate": now,
                  "clouds": float(latest['data']['sky_temp_C']),
                  "temp": float(latest['data']['ambient_temp_C']),
                  "wind": float(latest['data']['wind_speed_KPH']),
                  "gust": float(latest['data']['wind_speed_KPH']),
                  "rain": int(latest['data']['rain_frequency']),
                  "light": 0,
                  "switch": latest['data']['safe'],
                  "safe": latest['data']['safe'],
                 }


    threshold = 30
    age = (weatherdoc["querydate"] - weatherdoc["date"]).total_seconds()
    logger.debug('Data age = {:.1f} seconds'.format(age))
    if age > threshold:
        logger.warning('Age of weather data ({:.1f}) is greater than {:.0f} seconds'.format(
                       age, threshold))

    logger.info('Saving weather document')
    logger.info('Connecting to mongoDB')
    client = pymongo.MongoClient('192.168.1.101', 27017)
    db = client.vysos
    weather = db.weather

    try:
        inserted_id = weather.insert_one(weatherdoc).inserted_id
        logger.info("  Inserted document with id: {}".format(inserted_id))
    except:
        e = sys.exc_info()[0]
        logger.error('Failed to add new document')
        logger.error(e)

    client.close()

    # Example sld
    # 2017-02-25 17:27:31.00 C K    3.8    8.8    8.8    1.0  -1  100.0  25 2 2 00000 042791.72744 0 1 3 1 1 1
    # From Boltwood manual:
    # Date       Time        T V   SkyT   AmbT   SenT   Wind Hum  DewPt Hea R W Since  Now() Day's c w r d C A
    # 2005-06-03 02:07:23.34 C K  -28.5   18.7   22.5   45.3  75   10.3   3 0 0 00004 038506.08846 1 2 1 0 0 0
    # NowDays = date/time given as the VB6 Now() function result (in days) when Clarity II last wrote this file
    tref1 = dt.strptime('2005-06-03 02:07:23.34', '%Y-%m-%d %H:%M:%S.%f')
    dtref1 = 038506.08846
    to1 = tref1 - tdelta(days=dtref1)
    tref2 = dt.strptime('2017-02-25 17:27:31.00', '%Y-%m-%d %H:%M:%S.%f')
    dtref2 = 042791.72744
    to2 = tref2 - tdelta(days=dtref2)
    to = to2

    sld_file = os.path.expanduser('~/V20Data/aag_sld.dat')
    logger.info(f'Writing Single Line Data File to {sld_file}')
    local_time_str = dt.strftime(weatherdoc['date']-tdelta(0,10*3600), '%Y-%m-%d %H:%M:%S.00')
    SkyT = weatherdoc['clouds']
    AmbT = weatherdoc['temp']
    SenT = weatherdoc['temp'] # using ambient
    Wind = weatherdoc['wind']
    Hum = -1
    DewPt = 100.0
    Hea = 25
    R = {'Dry':0, 'Wet':1, 'Rain':1, 'Unknown':1}[latest['data']['rain_condition']]
    W = {'Dry':0, 'Wet':1, 'Rain':1, 'Unknown':1}[latest['data']['rain_condition']]
    Since = 00000
    NowDays = (weatherdoc['date']-tdelta(0,10*3600)-to).total_seconds()/3600/24
    c = {'Unknown':0, 'Very Cloudy':3, 'Cloudy':2, 'Clear':1}[latest['data']['sky_condition']]
    w = {'Unknown':0, 'Very Windy':3, 'Windy':2, 'Calm':1}[latest['data']['wind_condition']]
    r = {'Unknown':0, 'Rain':3, 'Wet':2, 'Dry':1}[latest['data']['rain_condition']]
    d = 1
    C = {True:0 , False:1}[latest['data']['safe']]
    A = C
    sld = f"{local_time_str:22s} C K {SkyT:6.1f} {AmbT:6.1f} {SenT:6.1f} {Wind:6.1f} {Hum:3.0f} {DewPt:6.1f} {Hea:3d} {R:1d} {W:1d} {Since:05d} {NowDays:012.5f} {c:1d} {w:1d} {r:1d} {d:1d} {C:1d} {A:1d}"
    logger.info("  Date       Time        T V   SkyT   AmbT   SenT   Wind Hum  DewPt Hea R W Since  Now() Day's c w r d C A")
    logger.info(f"  {sld}")
    if os.path.exists(sld_file):
        os.remove(sld_file)
    with open(sld_file, 'x') as sldFO:
        sldFO.write(f"{sld}\n")
    logger.info(f'  Done')


if __name__ == '__main__':

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
    parser.add_argument("--notrobust",
        action="store_true", dest="notrobust",
        default=False, help="Use try except to catch errors.")
    ## add arguments
    args = parser.parse_args()


    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    now = dt.utcnow()
    DateString = now.strftime("%Y%m%dUT")
    TimeString = now.strftime("%H:%M:%S")
    logger = logging.getLogger('get_status_{}'.format(DateString))
    if len(logger.handlers) < 1:
        logger.setLevel(logging.DEBUG)
        ## Set up console output
        LogConsoleHandler = logging.StreamHandler()
        if args.verbose:
            LogConsoleHandler.setLevel(logging.DEBUG)
        else:
            LogConsoleHandler.setLevel(logging.INFO)
        LogFormat = logging.Formatter('%(asctime)s %(levelname)8s: %(message)s',
                                      datefmt='%Y%m%d %H:%M:%S')
        LogConsoleHandler.setFormatter(LogFormat)
        logger.addHandler(LogConsoleHandler)

    while True:
        get_weather(logger, robust=not args.notrobust)
        logging.shutdown()
        sleep(20)
