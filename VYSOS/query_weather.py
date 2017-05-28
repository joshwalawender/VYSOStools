import logging
import argparse
import datetime
from time import sleep
import mongoengine as me

from VYSOS.schema import weather, currentweather

##-------------------------------------------------------------------------
## Query AAG Solo for Weather Data
##-------------------------------------------------------------------------
def get_weather(logger, robust=True):
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
        logger.debug('  {} = {}'.format(key, val))
    logger.info('  Done.')

    logger.info('Connecting to mongoDB')
    me.connect('vysos', host='192.168.1.101')

    weatherdoc = weather(date=datetime.datetime.strptime(result['dataGMTTime'],
                                                         '%Y/%m/%d %H:%M:%S'),
                         clouds=float(result['clouds']),
                         temp=float(result['temp']),
                         wind=float(result['wind']),
                         gust=float(result['gust']),
                         rain=int(result['rain']),
                         light=int(result['light']),
                         switch=int(result['switch']),
                         safe={'1': True, '0': False}[result['safe']],
                        )

    threshold = 30
    age = (weatherdoc.querydate - weatherdoc.date).total_seconds()
    logger.debug('Data age = {:.1f} seconds'.format(age))
    if age > threshold:
        logger.warning('Age of weather data ({:.1f}) is greater than {:.0f} seconds'.format(
                       age, threshold))


    logger.info('Saving weather document')
    try:
        weatherdoc.save()
        logger.info("  Done")
        logger.info("\n{}".format(weatherdoc))
    except:
        logger.error('Failed to add new document')



    cw = currentweather(date=datetime.datetime.strptime(result['dataGMTTime'],
                                                         '%Y/%m/%d %H:%M:%S'),
                        clouds=float(result['clouds']),
                        temp=float(result['temp']),
                        wind=float(result['wind']),
                        gust=float(result['gust']),
                        rain=int(result['rain']),
                        light=int(result['light']),
                        switch=int(result['switch']),
                        safe={'1': True, '0': False}[result['safe']],
                        )
    logger.info('Saving current document')
    current = currentweather.objects()
    cw.drop_collection()
    cw.save()
    logger.info('  Found {:d} current docs'.format(current.count()))
    if current.count() == 0:
        logger.info('  Saving single document')
        try:
            cw.save()
            logger.info("  Done")
        except:
            logger.warning('Failed to save document to currentweather')
    elif current.count() == 1:
        old = currentweather.objects.get()
        old.delete()
        cw.save()
    else:
        logger.info('  Updating existing document')
        try:
            current.update_one(set__querydate = cw.querydate,
                               set__date      = cw.date,
                               set__clouds    = cw.clouds,
                               set__temp      = cw.temp,
                               set__wind      = cw.wind,
                               set__gust      = cw.gust,
                               set__rain      = cw.rain,
                               set__light     = cw.light,
                               set__switch    = cw.switch,
                               set__safe      = cw.safe,
                               )
            logger.info("  Done")
        except:
            logger.warning('Failed to update currentweather')



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
        get_weather(logger, robust=not args.notrobust)
        logging.shutdown()
        sleep(20)
