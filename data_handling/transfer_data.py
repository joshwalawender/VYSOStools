import sys
import os
import re
import logging
import time
from glob import glob
from datetime import datetime as dt
from datetime import timedelta as tdelta
from argparse import ArgumentParser

import copy_data_remote

def main():

    V5_directories = glob('/Volumes/WD500B/V5/Images/20*UT')
    V20_directories = glob('/Volumes/WD500B/V20/Images/20*UT')

    for path in V5_directories:
        dir = os.path.split(path)[1]
        MatchNight = re.match('(\d{8}UT)', dir)
        if MatchNight:
            date = MatchNight.group(1)
            print('Copying {} on V5'.format(date))
            copy_data_remote.copy_night('V5', date)

    for path in V20_directories:
        dir = os.path.split(path)[1]
        MatchNight = re.match('(\d{8}UT)', dir)
        if MatchNight:
            date = MatchNight.group(1)
            print('Copying {} on V20'.format(date))
            copy_data_remote.copy_night('V20', date)



if __name__ == "__main__":
    main()
