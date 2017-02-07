import mongoengine as me

class Weather(me.Document):
    
    meta = {'collection': 'weather',
            'indexes': ['date']}


class V20Status(me.Document):
    date = me.DateTimeField(default=datetime.datetime.now, required=True)
    ## ACP Status
    connected = me.BooleanField()
    park = me.BooleanField()
    slewing = me.BooleanField()
    tracking = me.BooleanField()
    alt = me.DecimalField(min_value=0, max_value=90, precision=4)
    az = me.DecimalField(min_value=0, max_value=360, precision=4)
    RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    ACPerr = me.StringField(max_length=256)
    ## FocusMax Status
    focuser_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    focuser_position = me.DecimalField(min_value=0, max_value=105000, precision=1)

    ## RCOS TCC Status
    fan_speed = me.DecimalField(min_value=0, max_value=100, precision=0)
    truss_temperature  = me.DecimalField(min_value=-50, max_value=120, precision=1)
    primary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    secondary_temperature = me.DecimalField(min_value=-50, max_value=120, precision=0)
    ## CBW Status
    dome_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    fan_state = me.BooleanField()
    fan_enable = me.BooleanField()

    meta = {'collection': 'V20.status',
            'indexes': ['date']}


class V5Status(me.Document):
    date = me.DateTimeField(default=datetime.datetime.now, required=True)
    ## ACP Status
    connected = me.BooleanField()
    park = me.BooleanField()
    slewing = me.BooleanField()
    tracking = me.BooleanField()
    alt = me.DecimalField(min_value=0, max_value=90, precision=4)
    az = me.DecimalField(min_value=0, max_value=360, precision=4)
    RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    ACPerr = me.StringField(max_length=256)
    ## FocusMax Status
    focuser_temperature = me.DecimalField(min_value=-50, max_value=120, precision=1)
    focuser_position = me.DecimalField(min_value=0, max_value=40000, precision=0)

    meta = {'collection': 'V5.status',
            'indexes': ['date']}


class Image(me.Document):
    date = me.DateTimeField(default=datetime.datetime.now, required=True)
    telescope = me.StringField(max_length=3, required=True, choices=['V5', 'V20'])
    filename = me.StringField(max_length=128, required=True)
    compressed = me.BooleanField(required=True)
    analyzed = me.BooleanField(required=True)
    
    SIDREversion = me.StringField(max_length=12)
    full_field_jpeg = me.ImageField(thumbnail_size=(128,128,True))
    cropped_jpeg = me.ImageField(thumbnail_size=(128,128,True))
    
    FWHM_pix = me.DecimalField(min_value=0, precision=1)
    ellipticity = me.DecimalField(min_value=0, precision=2)
    
    exptime = me.DecimalField(min_value=0, precision=1)
    exposure_start = me.DateTimeField()
    filter = me.StringField(max_length=15)
    header_RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    header_DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    RA = me.DecimalField(min_value=0, max_value=360, precision=4)
    DEC = me.DecimalField(min_value=-90, max_value=90, precision=4)
    perr_arcmin = me.DecimalField(min_value=0, precision=2)
    alt = me.DecimalField(min_value=0, max_value=90, precision=2)
    az = me.DecimalField(min_value=0, max_value=360, precision=2)
    airmass = me.DecimalField(min_value=1, precision=3)
    moon_illumination = me.DecimalField(min_value=0, max_value=100, precision=1)
    moon_separation = me.DecimalField(min_value=0, max_value=180, precision=1)
    
    meta = {'collection': 'images',
            'indexes': ['telescope', 'date', 'filename']}
