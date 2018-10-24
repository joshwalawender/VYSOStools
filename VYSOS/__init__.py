from astropy import units as u

weather_limits = {'Cloudiness (C)': [-30, -20],
                  'Wind (kph)': [20, 40],
                  'Rain': [2400, 2000],
                  }

styles = {'p': {'font-family': 'Arial, Helvetica, sans-serif'},
          'table': {'font-family': 'Arial, Helvetica, sans-serif',
                    'border-collapse': 'collapse',
                    'margin-left': 'auto',
                    'margin-right': 'auto',
                    'border': '1px solid black',
                    'vertical-align': 'top',
                    'text-align': 'center',
                    'padding-top': '5px',
                    'padding-right': '5px',
                    'padding-bottom': '5px',
                    'padding-left': '5px',
                    },
          'tdc': {'font-family': 'Arial, Helvetica, sans-serif',
                  'border': '1px solid black',
                  'vertical-align': 'top',
                  'text-align': 'center',
                  'padding-top': '5px',
                  'padding-right': '5px',
                  'padding-bottom': '5px',
                  'padding-left': '5px',
                 },
          'tdr': {'font-family': 'Arial, Helvetica, sans-serif',
                  'border': '1px solid black',
                  'vertical-align': 'top',
                  'text-align': 'right',
                  'padding-top': '5px',
                  'padding-right': '5px',
                  'padding-bottom': '5px',
                  'padding-left': '5px',
                 },
          'tdl': {'font-family': 'Arial, Helvetica, sans-serif',
                  'border': '1px solid black',
                  'vertical-align': 'top',
                  'text-align': 'left',
                  'padding-top': '5px',
                  'padding-right': '5px',
                  'padding-bottom': '5px',
                  'padding-left': '5px',
                 },
         }


class Telescope(object):
    '''This object stores some basic info about the telescope in use (either
    V5 or V20).
    '''
    def __init__(self, name):
        self.name = name
        self.mongo_address = '192.168.1.101'
        self.mongo_port = 27017
        self.mongo_db = 'vysos'
        self.mongo_collection = 'images'
        self.units_for_FWHM = u.pix
        self.get_pixel_scale()
        self.get_limits()
    
    def get_pixel_scale(self):
        if self.name == 'V20':
            self.units_for_FWHM = u.arcsec
            self.pixel_scale = 206.265*9/4300 * u.arcsec/u.pix
        elif self.name == 'V5':
            self.units_for_FWHM = u.pix
            self.pixel_scale = 206.265*9/735 * u.arcsec/u.pix
        else:
            self.units_for_FWHM = u.pix
            self.pixel_scale = None
    
    def get_limits(self):
        if self.name == 'V20':
            self.FWHM_limit_pix = (3.5*u.arcsec/self.pixel_scale).decompose()
            self.ellipticity_limit = 1.3
            self.pointing_error_limit = 3
        elif self.name == 'V5':
            self.FWHM_limit_pix = 2.5
            self.ellipticity_limit = 1.3
            self.pointing_error_limit = 6
        else:
            self.FWHM_limit_pix = None
            self.ellipticity_limit = None
            self.pointing_error_limit = None

