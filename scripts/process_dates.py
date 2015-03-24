import sys
import os
import re
from glob import glob
from datetime import datetime as dt
from datetime import timedelta as tdelta
from argparse import ArgumentParser

import measure_image

def main(startdate, enddate):
    MatchFilename = re.compile("(.*)\-([0-9]{8})at([0-9]{6})\.fts")
    MatchEmpty = re.compile(".*\-Empty\-.*\.fts")
    oneday = tdelta(1, 0)
    now = startdate
    while now <= enddate:
        date_string = now.strftime('%Y%m%dUT')
        print('Checking for images from {}'.format(date_string))
        images = []
        V5_path = os.path.join("/Volumes", "Drobo", "V5", "Images", date_string)
        V20_path = os.path.join("/Volumes", "Drobo", "V20", "Images", date_string)
        if os.path.exists(V5_path):
            V5_images = glob(os.path.join(V5_path, '*.fts'))
            print('  Found {} images for the night of {} for V5'.format(len(V5_images), date_string))
            images.extend(V5_images)
        if os.path.exists(V20_path):
            V20_images = glob(os.path.join(V20_path, '*.fts'))
            print('  Found {} images for the night of {} for V20'.format(len(V20_images), date_string))
            images.extend(V20_images)
        for image in images:
            if MatchFilename.match(image) and not MatchEmpty.match(image):
                try:
                    measure_image.MeasureImage(image,\
                                 clobber_logs=True,\
                                 zero_point=True,\
                                 analyze_image=True)
                except:
                    print('WARNING:  MeasureImage failed on {}'.format(image))
                    measure_image.MeasureImage(image,\
                                 clobber_logs=False,\
                                 zero_point=False,\
                                 analyze_image=False)

        now += oneday

    
    
    
if __name__ == "__main__":
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    parser.add_argument("-s", "--start", 
        dest="start", required=True, type=str,
        help="UT date of first night to analyze. (i.e. '20130805UT')")
    parser.add_argument("-e", "--end", 
        dest="end", required=True, type=str,
        help="UT date of last night to analyze. (i.e. '20130805UT')")
    args = parser.parse_args()

    startdate = dt.strptime(args.start, '%Y%m%dUT')
    enddate = dt.strptime(args.end, '%Y%m%dUT')

    main(startdate, enddate)
