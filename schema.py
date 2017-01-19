import mongoengine as me

class Weather(me.Document):
    pass


class V20Status(me.Document):
    date = me.DateTimeField(default=datetime.datetime.now, required=True)
    ## ACP Status
    tracking = me.BooleanField()
    slewing = me.BooleanField()
    connected = me.BooleanField()
    target_RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    target_DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    alt = me.DecimalField(min_value=0, max_value=90, precision=4)
    az = me.DecimalField(min_value=0, max_value=360, precision=4)
    park = me.BooleanField()
    ## RCOS TCC Status
    fan_speed = me.DecimalField(min_value=0, max_value=100, precision=0)
    truss_temperature  = me.DecimalField(min_value=-50, max_value=120, precision=1)
    primary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    secondary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    ## CBW Status
    dome_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    fan_state = me.BooleanField()
    fan_enable = me.BooleanField()

    meta = {'indexes': ['date']}


class V5Status(me.Document):
    date = me.DateTimeField(default=datetime.datetime.now, required=True)
    ## ACP Status
    tracking = me.BooleanField()
    slewing = me.BooleanField()
    connected = me.BooleanField()
    target_RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    target_DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    alt = me.DecimalField(min_value=0, max_value=90, precision=4)
    az = me.DecimalField(min_value=0, max_value=360, precision=4)
    park = me.BooleanField()
    ## FocusMax Status
    focuser_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)

    meta = {'indexes': ['date']}


class Image(me.Document):
    date = me.DateTimeField(default=datetime.datetime.now, required=True)
    telescope = me.StringField(max_length=3, required=True, choices=['V5', 'V20'])
    filename = me.StringField(max_length=128, required=True)
    compressed = me.BooleanField(required=True)
    analyzed = me.BooleanField(required=True)

    SIDREversion = me.StringField(max_length=12)
    full_field_jpeg = me.ImageField(thumbnail_size=(128,128,True))
    cropped_jpeg = me.ImageField(thumbnail_size=(128,128,True))
    

    meta = {'indexes': ['telescope', 'date', 'filename']}
