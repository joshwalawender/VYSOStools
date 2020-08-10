import sys
import os
import logging
import argparse
from datetime import datetime as dt
from time import sleep
import pymongo
import requests

# import mongoengine as me
# from VYSOS.schema import weather, currentweather

##-------------------------------------------------------------------------
## Query AAG Solo for Weather Data
##-------------------------------------------------------------------------
def get_weather(logger, robust=True):
    logger.info('Getting Weather status')
    
    # http://aagsolo/cgi-bin/cgiLastData
    # http://aagsolo/cgi-bin/cgiHistData
    querydate = dt.utcnow()
    address = 'http://192.168.1.105/cgi-bin/cgiLastData'

    try:
        r = requests.get(address)
    except:
        logger.error('Failed to connect to AAG Solo')
    else:
        lines = r.text.splitlines()
        result = {}
        for line in lines:
            key, val = line.split('=')
            result[str(key)] = str(val)
            logger.debug('  {} = {}'.format(key, val))
        logger.info('  Done.')

        weatherdoc = {"date": dt.strptime(result['dataGMTTime'], '%Y/%m/%d %H:%M:%S'),
                      "querydate": querydate,
                      "clouds": float(result['clouds']),
                      "temp": float(result['temp']),
                      "wind": float(result['wind']),
                      "gust": float(result['gust']),
                      "rain": int(result['rain']),
                      "light": int(result['light']),
                      "switch": int(result['switch']),
                      "safe": {'1': True, '0': False}[result['safe']],
                     }

        threshold = 60
        age = (weatherdoc["querydate"] - weatherdoc["date"]).total_seconds()
        logger.debug('Data age = {:.1f} seconds'.format(age))
        if age > threshold:
            logger.warning(f'Weather data age ({age:.0f}) > {threshold:.0f} s')
            now_str = querydate.strftime('%Y%m%dUT %H:%M:%S')
            today_str = querydate.strftime('%Y%m%dUT')
            alert_file = f"~/Dropbox/VYSOSAlerts/WeatherData_{today_str}.txt"
            with open(os.path.expanduser(alert_file), 'a') as FO:
                FO.write(f"At {now_str} weather data is {age:.0f} s old\n")
#             with open(os.path.expanduser(alert_file), 'r') as FO:
#                 lines = FO.read().split('\n')

        logger.info('Saving weather document')
        logger.info('Connecting to mongoDB')
        client = pymongo.MongoClient('localhost', 27017)
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
        sleep(60)
