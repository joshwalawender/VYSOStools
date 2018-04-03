from datetime import datetime as dt
import mongoengine as me

from VYSOS import weather_limits

class weatherbase(me.Document):
    querydate = me.DateTimeField(default=dt.utcnow(), required=True)
    date = me.DateTimeField(required=True)
    clouds = me.DecimalField(precision=2)
    temp = me.DecimalField(precision=2)
    wind = me.DecimalField(precision=1)
    gust = me.DecimalField(precision=1)
    rain = me.IntField()
    light = me.IntField()
    switch = me.IntField()
    safe = me.BooleanField()

    meta = {'allow_inheritance': True,
            'abstract': True,}
#             'collection': 'weather'}

    def __str__(self):
        output = 'MongoEngine Document at: {}\n'.format(
                 self.querydate.strftime('%Y%m%d %H:%M:%S'))
        if self.date: output += '  Date: {}\n'.format(
                      self.date.strftime('%Y%m%d %H:%M:%S'))
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

class weather(weatherbase):
    meta = {'collection': 'weather',
            'indexes': ['date']}

class currentweather(weatherbase):
    meta = {'collection': 'currentweather'}

    def from_weather(self, wd):
        self.querydate = wd.querydate
        self.date      = wd.date
        self.clouds    = wd.clouds
        self.temp      = wd.temp
        self.wind      = wd.wind
        self.gust      = wd.gust
        self.rain      = wd.rain
        self.light     = wd.light
        self.switch    = wd.switch
        self.safe      = wd.safe


class telstatus(me.Document):
    telescope = me.StringField(max_length=3, required=True, choices=['V5', 'V20'])
    date = me.DateTimeField(default=dt.utcnow(), required=True)
    current = me.BooleanField(default=True, required=True)
    ## ACP Status
    connected = me.BooleanField()
    park = me.BooleanField()
    slewing = me.BooleanField()
    tracking = me.BooleanField()
    alt = me.DecimalField(min_value=-90, max_value=90, precision=4)
    az = me.DecimalField(min_value=0, max_value=360, precision=4)
    RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    ACPerr = me.StringField(max_length=256)
    ## FocusMax Status
    focuser_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    focuser_position = me.DecimalField(min_value=0, max_value=105000, precision=1)

    ## RCOS TCC Status
    fan_speed = me.DecimalField(min_value=0, max_value=100, precision=1)
    truss_temperature  = me.DecimalField(min_value=-50, max_value=120, precision=1)
    primary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    secondary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    ## CBW Status
    dome_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    fan_state = me.BooleanField()
    fan_enable = me.BooleanField()

    meta = {'collection': 'telstatus',
            'indexes': ['telescope', 'current', 'date']}

    def __str__(self):
        output = 'MongoEngine Document at: {}\n'.format(self.date.strftime('%Y%m%d %H:%M:%S'))
        if self.telescope: output += '  Telescope: {}\n'.format(self.telescope)
        if self.current: output += '  Current: {}\n'.format(self.current)
        if self.connected: output += '  connected: {}\n'.format(self.connected)
        if self.park: output += '  park: {}\n'.format(self.park)
        if self.slewing: output += '  slewing: {}\n'.format(self.slewing)
        if self.tracking: output += '  tracking: {}\n'.format(self.tracking)
        if self.alt: output += '  Altitude: {:.4f}\n'.format(self.alt)
        if self.az: output += '  Azimuth: {:.4f}\n'.format(self.az)
        if self.RA: output += '  RA: {:.4f}\n'.format(self.RA)
        if self.DEC: output += '  DEC: {:.4f}\n'.format(self.DEC)
        if self.ACPerr: output += '  ACPerr: {}\n'.format(self.ACPerr)
        if self.focuser_temperature: output += '  focuser_temperature: {:.1f}\n'.format(self.focuser_temperature)
        if self.focuser_position: output += '  focuser_position: {}\n'.format(self.focuser_position)
        if self.truss_temperature: output += '  truss_temperature: {:.1f}\n'.format(self.truss_temperature)
        if self.primary_temperature: output += '  primary_temperature: {:.1f}\n'.format(self.primary_temperature)
        if self.secondary_temperature: output += '  secondary_temperature: {:.1f}\n'.format(self.secondary_temperature)
        if self.fan_speed: output += '  fan_speed: {}\n'.format(self.fan_speed)
        if self.dome_temperature: output += '  dome_temperature: {:.1f}\n'.format(self.dome_temperature)
        if self.fan_state: output += '  fan_state: {}\n'.format(self.fan_state)
        if self.fan_enable: output += '  fan_enable: {}\n'.format(self.fan_enable)
        return output

    def __repr__(self):
        return self.__str__()


class Image(me.Document):
    # Basics
    filename = me.StringField(max_length=128, required=True)
    analysis_date = me.DateTimeField(default=dt.utcnow(), required=True)
    telescope = me.StringField(max_length=3, choices=['V5', 'V20'])
    compressed = me.BooleanField()
    # Header Info
    target = me.StringField(max_length=128)
    exptime = me.DecimalField(min_value=0, precision=1)
    date = me.DateTimeField()
    filter = me.StringField(max_length=15)
    header_RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    header_DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    alt = me.DecimalField(min_value=0, max_value=90, precision=2)
    az = me.DecimalField(min_value=0, max_value=360, precision=2)
    airmass = me.DecimalField(min_value=1, precision=3)
    moon_alt = me.DecimalField(min_value=0, max_value=90, precision=1)
    moon_illumination = me.DecimalField(min_value=0, max_value=100, precision=1)
    moon_separation = me.DecimalField(min_value=0, max_value=180, precision=1)
    # Analysis Results
    analyzed = me.BooleanField()
    SIDREversion = me.StringField(max_length=12)
    FWHM_pix = me.DecimalField(min_value=0, precision=1)
    ellipticity = me.DecimalField(min_value=0, precision=2)
    RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    perr_arcmin = me.DecimalField(min_value=0, precision=2)
    # JPEGs
    full_field_jpeg = me.ImageField(thumbnail_size=(128,128,True))
    cropped_jpeg = me.ImageField(thumbnail_size=(128,128,True))
    
    meta = {'collection': 'images',
            'indexes': ['telescope', 'date', 'filename']}

    def __str__(self):
        output = 'MongoEngine Document for: {}\n'.format(self.filename)
        output += '  Analysis Date: {}\n'.format(self.analysis_date.isoformat())
        if self.telescope: output += '  Telescope: {}\n'.format(self.telescope)
        if self.target: output += '  Target Field: {}\n'.format(self.target)
        if self.date: output += '  Image Date: {}\n'.format(self.date.isoformat())
        if self.exptime: output += '  Exposure Time: {:.1f}\n'.format(self.exptime)
        if self.filter: output += '  Filter: {}\n'.format(self.filter)
        if self.header_RA: output += '  Header RA: {:.4f}\n'.format(self.header_RA)
        if self.header_DEC: output += '  Header Dec: {:.4f}\n'.format(self.header_DEC)
        if self.alt: output += '  Altitude: {:.4f}\n'.format(self.alt)
        if self.az: output += '  Azimuth: {:.4f}\n'.format(self.az)
        if self.airmass: output += '  Airmass: {:.3f}\n'.format(self.airmass)
        if self.moon_illumination: output += '  moon_illumination: {:.2f}\n'.format(self.moon_illumination)
        if self.moon_separation: output += '  moon_separation: {:.0f}\n'.format(self.moon_separation)
        if self.SIDREversion: output += '  SIDREversion: {}\n'.format(self.SIDREversion)
        if self.FWHM_pix: output += '  FWHM_pix: {:.1f}\n'.format(self.FWHM_pix)
        if self.ellipticity: output += '  ellipticity: {:.2f}\n'.format(self.ellipticity)
        if self.RA: output += '  WCS RA: {:.4f}\n'.format(self.RA)
        if self.DEC: output += '  WCS DEC: {:.4f}\n'.format(self.DEC)
        if self.perr_arcmin: output += '  Pointing Error: {:.1f} arcmin\n'.format(self.perr_arcmin)
        return output

    def __repr__(self):
        return self.__str__()

