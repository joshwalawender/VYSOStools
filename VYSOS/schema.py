import datetime
import mongoengine as me

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

