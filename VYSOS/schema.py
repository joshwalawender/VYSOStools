import datetime
import mongoengine as me

weather_limits = {'Cloudiness (C)': [-35, -20],
                  'Wind (kph)': [20, 40],
                  'Rain': [2400, 2000],
                  }

class weatherbase(me.Document):
    querydate = me.DateTimeField(default=datetime.datetime.utcnow(), required=True)
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
            'abstract': True,
            'collection': 'weather'}

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
    date = me.DateTimeField(default=datetime.datetime.utcnow(), required=True)
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
