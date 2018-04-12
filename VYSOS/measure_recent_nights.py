import os
from glob import glob
from VYSOS.measure_night import measure_night

dirs = glob(os.path.join(os.path.expanduser('~'), 'V20Data', 'Images', '*UT'))

dates = [os.path.split(dir)[1] for dir in dirs]

for date in dates:
    measure_night(date=date, telescope='V20')
