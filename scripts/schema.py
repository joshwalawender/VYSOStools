import mongoengine as me

class Weather(me.Document):
    
    meta = {'collection': 'weather',
            'indexes': ['date']}


