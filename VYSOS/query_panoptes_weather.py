import sys
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
                  "clouds": float(latest['sky_temp_C']),
                  "temp": float(latest['ambient_temp_C']),
                  "wind": float(latest['wind_speed_KPH']),
                  "gust": float(latest['wind_speed_KPH']),
                  "rain": int(latest['rain_frequency']),
                  "light": 0,
                  "switch": {'1': True, '0': False}[latest['safe']],
                  "safe": {'1': True, '0': False}[latest['safe']],
                 }

#     http://aagsolo/cgi-bin/cgiLastData
#     http://aagsolo/cgi-bin/cgiHistData
#     querydate = dt.utcnow()
#     address = 'http://192.168.1.105/cgi-bin/cgiLastData'
# 
#     try:
#         r = requests.get(address)
#     except:
#         logger.error('Failed to connect to AAG Solo')
#     else:
#         lines = r.text.splitlines()
#         result = {}
#         for line in lines:
#             key, val = line.split('=')
#             result[str(key)] = str(val)
#             logger.debug('  {} = {}'.format(key, val))
#         logger.info('  Done.')
# 
#         weatherdoc = {"date": dt.strptime(result['dataGMTTime'], '%Y/%m/%d %H:%M:%S'),
#                       "querydate": querydate,
#                       "clouds": float(result['clouds']),
#                       "temp": float(result['temp']),
#                       "wind": float(result['wind']),
#                       "gust": float(result['gust']),
#                       "rain": int(result['rain']),
#                       "light": int(result['light']),
#                       "switch": int(result['switch']),
#                       "safe": {'1': True, '0': False}[result['safe']],
#                      }

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
