from astropy.time import Time
from astroplan import Observer
from astropy import coordinates
import logging


##-------------------------------------------------------------------------
## Create logger object
##-------------------------------------------------------------------------
log = logging.getLogger('HandleTwilightFlats')
log.setLevel(logging.DEBUG)
## Set up console output
LogConsoleHandler = logging.StreamHandler()
LogConsoleHandler.setLevel(logging.DEBUG)
LogFormat = logging.Formatter('%(asctime)s %(levelname)8s: %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
LogConsoleHandler.setFormatter(LogFormat)
log.addHandler(LogConsoleHandler)


now = Time.now()
loc = coordinates.EarthLocation.of_site('Keck Observatory') # Close enough
observer = Observer(location=loc, name="Ohina")
sun = coordinates.get_sun(now)
sun_alt = observer.altaz(now, sun).alt.value
log.info(f"Sun alt = {sun_alt:.1f} deg")
triggered_autoflat_directory = False

while sun_alt > -12:
    sleep(300)
    sun_alt = observer.altaz(Time.now(), sun).alt
    log.info(f"Sun alt = {sun_alt:.1f} deg")
    if sun_alt > 0:
        pass
    elif sun_alt < 0 and triggered_autoflat_directory is False:
        log.info(f"Triggering qlcd --flats")
        subprocess.call(['/Users/vysosuser/anaconda/bin/qlcd', '--flats'])
    elif sun_alt <= -12:
        log.info(f"Triggering qlcd")
        subprocess.call(['/Users/vysosuser/anaconda/bin/qlcd'])
log.info(f"Pau!")
log.info(f"")
