import logging
import argparse
import datetime
from time import sleep
import mongoengine as me

from VYSOS.schema import weather, currentweather

##-------------------------------------------------------------------------
## Query AAG Solo for Weather Data
##-------------------------------------------------------------------------
def get_weather(logger):
    logger.info('Getting Weather status')
    import requests
    # http://aagsolo/cgi-bin/cgiLastData
    # http://aagsolo/cgi-bin/cgiHistData
    address = 'http://192.168.1.105/cgi-bin/cgiLastData'
    r = requests.get(address)
    lines = r.text.splitlines()
    result = {}
    for line in lines:
        key, val = line.split('=')
        result[str(key)] = str(val)

    weatherdoc = weather(date=datetime.datetime.strptime(result['dataGMTTime'], '%Y/%m/%d %H:%M:%S'))
    weatherdoc.clouds = float(result['clouds'])
    weatherdoc.temp = float(result['temp'])
    weatherdoc.wind = float(result['wind'])
    weatherdoc.gust = float(result['gust'])
    weatherdoc.rain = int(result['rain'])
    weatherdoc.light = int(result['light'])
    weatherdoc.switch = int(result['switch'])
    weatherdoc.safe = {'1': True, '0': False}[result['safe']]

    threshold = 30
    age = (weatherdoc.querydate - weatherdoc.date).total_seconds()
    if age > threshold:
        logger.warning('Age of weather data ({:.1f}) is greater than {:.0f} seconds'.format(
                       age, threshold))

    me.connect('vysos', host='192.168.1.101')

    try:
        logger.info('Saving new document')
        weatherdoc.save()
        logger.info("  Done")
        logger.info("\n{}".format(weatherdoc))
    except:
        logger.error('Failed to add new document')

    try:
        logger.info('Saving current document')
        current = currentweather.objects()
        logger.info('  Found {:d} current docs'.format(current.count()))
        if current.count() < 1:
            logger.info('  Saving single document')
            cw = currentweather()
            cw.from_weather(weatherdoc)
            cw.save()
            logger.info("  Done")
        else:
            logger.info('  Updating existing document')
            current.update_one(set__querydate = weatherdoc.querydate,
                               set__date      = weatherdoc.date,
                               set__clouds    = weatherdoc.clouds,
                               set__temp      = weatherdoc.temp,
                               set__wind      = weatherdoc.wind,
                               set__gust      = weatherdoc.gust,
                               set__rain      = weatherdoc.rain,
                               set__light     = weatherdoc.light,
                               set__switch    = weatherdoc.switch,
                               set__safe      = weatherdoc.safe,
                               )
            logger.info("  Done")
    except:
        logger.warning('Failed to save document to currentweather')




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
    ## add arguments
    args = parser.parse_args()


    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    now = datetime.datetime.utcnow()
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
        get_weather(logger)
        logging.shutdown()
        sleep(20)
