#!/usr/bin/env python
# encoding: utf-8
"""
MakeWebPage.py

Created by Josh Walawender on 2013-05-01.
Copyright (c) 2013 __MyCompanyName__. All rights reserved.
"""

import sys
import os
from argparse import ArgumentParser
import re
import shutil
import subprocess
import datetime
import yaml
import pickle

import IQMon


def main(argv=None):
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add flags
    parser.add_argument("-c", "--clobber",
        action="store_true", dest="clobber",
        default=False, help="Clobber past results and re-check")
    ## add arguments
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    args = parser.parse_args()

    telescope = args.telescope

    paths_to_check = [os.path.join(os.path.expanduser('~'), 'IQMon', 'Logs'),\
                      os.path.join('/', 'Volumes', 'DroboPro1', 'IQMon', 'Logs')]
    logs_path = None
    for path_to_check in paths_to_check:
        if os.path.exists(path_to_check):
            logs_path = path_to_check
    assert logs_path


    if telescope == "V20": telname = "VYSOS-20"
    if telescope == "V5":  telname = "VYSOS-5"
    NightSummariesDirectory = os.path.join(logs_path, telname)
    SummaryHTMLFile = os.path.join(NightSummariesDirectory, "index.html")
    TemporaryHTMLFile = os.path.join(NightSummariesDirectory, "index_tmp.html")

    pickle_file = os.path.join(logs_path, telname, 'WebPageList.pkl')
    if args.clobber:
        if os.path.exists(pickle_file):
            os.remove(pickle_file)

    if os.path.exists(pickle_file):
        with open(pickle_file, 'r') as pickleFO:
            Dates = pickle.load(pickleFO)
    else:
        Dates = []
    date_strings = [entry[0] for entry in Dates]

    today_string = datetime.datetime.utcnow().strftime('%Y%m%dUT')
    date = datetime.datetime(2013, 4, 19, 0, 0, 0)
    one_day = datetime.timedelta(1, 0)
    while date <= datetime.datetime.utcnow():
        date_string = date.strftime('%Y%m%dUT')
        if (date_string in date_strings):
            print('Found entry for {}'.format(date_string))
        else:
            print('Examining files for {}'.format(date_string))
            path = os.path.join(logs_path, telname)
            Dates.append([date_string, "", "", "", "", "", 0, False])

            night_summary_file = '{}_{}.png'.format(date_string, telescope)
            if os.path.exists(os.path.join(path, night_summary_file)):
                Dates[-1][1] = night_summary_file

            environmental_graph_file = '{}_{}_Env.png'.format(date_string, telescope)
            if os.path.exists(os.path.join(path, environmental_graph_file)):
                Dates[-1][2] = environmental_graph_file

            html_summary_file = '{}_{}.html'.format(date_string, telescope)
            if os.path.exists(os.path.join(path, html_summary_file)):
                Dates[-1][3] = html_summary_file

            system_status_file = '{}.png'.format(date_string)
            if os.path.exists(os.path.join(logs_path, 'SystemStatus', system_status_file)):
                Dates[-1][7] = True

            text_summary_file = '{}_{}_Summary.txt'.format(date_string, telescope)
            if os.path.exists(os.path.join(path, text_summary_file)):
                Dates[-1][5] = text_summary_file
                with open(os.path.join(path, text_summary_file), 'r') as summaryFO:
                    try:
                        yaml_list = yaml.load(summaryFO)
                        firstfile = yaml_list[0]['filename']
                        nImages = len(yaml_list)
    #                     print('  Summary is a YAML file with {} entries'.format(nImages))
                    except:
                        nImages = 0
                if nImages == 0:
                    with open(os.path.join(path, text_summary_file), 'r') as summaryFO:
                        summary_list = summaryFO.readlines()
                        nImages = len(summary_list)
    #                     print('  Summary is a text table with {} entries'.format(nImages))
                Dates[-1][6] = nImages
        date += one_day

    SortedDates = sorted(Dates, reverse=True)

    ##############################################################
    ## Make index.html file
    HTML = open(SummaryHTMLFile, 'w')
    pathHome = homePath = os.path.expandvars("$HOME")
    HTMLheader = open(os.path.join(pathHome, "git", "VYSOS", "ListOfNights.html"), 'r')
    header = HTMLheader.read()
    header = header.replace("telescopename", telname)
    imagenumbers = {"VYSOS-20": '0', "VYSOS-5": '4'}
    header = header.replace("imagenumber", imagenumbers[telname])
    HTMLheader.close()
    HTML.write(header)


    for DateInfo in SortedDates:
        HTML.write("    <tr>\n")
        ## Write UT Date
        DateObject = datetime.datetime.strptime(DateInfo[0], "%Y%m%dUT")
        NiceDateString = DateObject.strftime("%Y/%m/%d UT")
        HTML.write("      <td style='text-align:center'>%-21s</td>\n" % NiceDateString)
        ## Write Link to Night Summary Graphs
        if DateInfo[1] != "":
            HTML.write("      <td style='text-align:center'><a href='%s'>%-50s</a></td>\n" % (DateInfo[1], "Night Summary Graphs"))
        else:
            HTML.write("      <td style='text-align:center'></td>\n")
        ## Write Link to Environmental Plots
        if DateInfo[2] != "":
            HTML.write("      <td style='text-align:center'><a href='%s'>%-50s</a></td>\n" % (DateInfo[2], "Environmental Graphs"))
        else:
            HTML.write("      <td style='text-align:center'></td>\n")
        ## Write Link to HTML Summary
        if DateInfo[3] != "":
            HTML.write("      <td style='text-align:center'><a href='%s'>%-50s</a></td>\n" % (DateInfo[3], "Image Summary"))
        else:
            HTML.write("      <td style='text-align:center'></td>\n")
        ## Write Link to Text Summary
        if DateInfo[5] != "":
            HTML.write("      <td style='text-align:center'><a href='%s'>%-50s</a></td>\n" % (DateInfo[5], "Text Summary"))
        else:
            HTML.write("      <td style='text-align:center'></td>\n")
        ## Write Number of Images
        HTML.write("      <td style='text-align:center'>%-5d</td>\n" % (DateInfo[6]))
        ## Write Link to System Status Chart
        if DateInfo[7]:
            link = '../SystemStatus/{}.png'.format(DateInfo[0])
            HTML.write("      <td style='text-align:center'><a href='{}'>Status Graph</a></td>\n".format(link))
        else:
            HTML.write("      <td style='text-align:center'>{}</td>\n".format(''))

    HTML.write("    </tr>\n")
    HTML.write("    </table>\n")
    HTML.write("</body>\n")
    HTML.write("</html>\n")
    HTML.close()

    for entry in Dates:
        if entry[0] == today_string:
            print('Removing {}'.format(today_string))
            Dates.remove(entry)

    print('Saving records in pickle file')
    with open(pickle_file, 'w') as pickleFO:
        pickle.dump(Dates, pickleFO)


if __name__ == '__main__':
    main()

