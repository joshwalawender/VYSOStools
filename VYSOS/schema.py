from datetime import datetime as dt
import mongoengine as me


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
    moon_alt = me.DecimalField(min_value=-90, max_value=90, precision=1)
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
    
    meta = {}

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

