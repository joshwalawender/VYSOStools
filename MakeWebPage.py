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
import subprocess32
import datetime

import IQMon


def main(argv=None):
    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = ArgumentParser(description="Describe the script")
    ## add arguments
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    args = parser.parse_args()

    telescope = args.telescope

    ##-------------------------------------------------------------------------
    ## Establish IQMon Configuration
    ##-------------------------------------------------------------------------
    config = IQMon.Config()
    if telescope == "V20": telname = "VYSOS-20"
    if telescope == "V5":  telname = "VYSOS-5"
    NightSummariesDirectory = os.path.join(config.pathLog, telname)
    SummaryHTMLFile = os.path.join(NightSummariesDirectory, "index.html")
    TemporaryHTMLFile = os.path.join(NightSummariesDirectory, "index_tmp.html")


    ##############################################################
    ## Read Contents of Night Summaries Directory
    Files = os.listdir(NightSummariesDirectory)
    MatchDateOnFile  = re.compile("([0-9]{8}UT)_"+telescope+".*")
    
    ## Make List of Dates for Files in Directory
    ## - loop through files, extract date
    ## - compare against list of dates already recorded
    ## - if date not already recorded, add to list
    Dates = []
    for File in Files:
        HasDate = MatchDateOnFile.match(File)
        if HasDate:
            Date = HasDate.group(1)
            DateAlreadyListed = False
            for ListedDate in Dates:
                if ListedDate[0] == Date:
                    DateAlreadyListed = True
            if not DateAlreadyListed:
                Dates.append([Date, "", "", "", "", "", 0])

            IsPNGFile     = re.match(Date+"_"+telescope+"\.png", File)
            if IsPNGFile:
                print "Found Summary Graphs File for "+Date
                Dates[-1][1] = File
            IsEnvFile     = re.match(Date+"_"+telescope+"_Env\.png", File)
            if IsEnvFile:
                print "Found Environmantal Graphs File for "+Date
                Dates[-1][2] = File
            IsHTMLFile    = re.match(Date+"_"+telescope+"\.html", File)
            if IsHTMLFile:
                print "Found HTML File for "+Date
                Dates[-1][3] = File
            IsIQMonFile   = re.match(Date+"_"+telescope+"_IQMonLog\.txt", File)
            if IsIQMonFile:
                print "Found IQMonLog File for "+Date
                Dates[-1][4] = File
            IsSummaryFile = re.match(Date+"_"+telescope+"_Summary\.txt", File)
            if IsSummaryFile:
                print "Found Summary File for "+Date
                Dates[-1][5] = File
                wcSTDOUT = subprocess32.check_output(["wc", "-l", os.path.join(NightSummariesDirectory, File)], stderr=subprocess32.STDOUT, timeout=5)

                try:
                    nLines = int(wcSTDOUT.strip().split(" ")[0])
                    nImages = nLines - 1
                except:
                    nImages = 0
                Dates[-1][6] = nImages
                
            
    # for Date in Dates:
    #     print Date

    SortedDates = sorted(Dates, reverse=True)
    # for item in SortedDates:
    #     print item

    ##############################################################
    ## Make index.html file
    HTML = open(SummaryHTMLFile, 'w')
    pathHome = homePath = os.path.expandvars("$HOME")
    HTMLheader = open(os.path.join(pathHome, "bin", "VYSOS", "ListOfNights.html"), 'r')
    header = HTMLheader.read()
    header = header.replace("telescopename", telname)
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
            HTML.write("      <td style='text-align:center'><a href='%s'>%-50s</a></td>\n" % (DateInfo[2], "Environmantal Graphs"))
        else:
            HTML.write("      <td style='text-align:center'></td>\n")
        ## Write Link to HTML Summary
        if DateInfo[3] != "":
            HTML.write("      <td style='text-align:center'><a href='%s'>%-50s</a></td>\n" % (DateInfo[3], "Image Summary"))
        else:
            HTML.write("      <td style='text-align:center'></td>\n")
        ## Write Link to IQMon Log
        if DateInfo[4] != "":
            HTML.write("      <td style='text-align:center'><a href='%s'>%-50s</a></td>\n" % (DateInfo[4], "IQMon Log"))
        else:
            HTML.write("      <td style='text-align:center'></td>\n")
        ## Write Link to Text Summary
        if DateInfo[5] != "":
            HTML.write("      <td style='text-align:center'><a href='%s'>%-50s</a></td>\n" % (DateInfo[5], "Text Summary"))
        else:
            HTML.write("      <td style='text-align:center'></td>\n")
        ## Write Number of Images
        HTML.write("      <td style='text-align:center'>%-5d</td>\n" % (DateInfo[6]))

    HTML.write("    </tr>\n")
    HTML.write("    </table>\n")
    HTML.write("</body>\n")
    HTML.write("</html>\n")
    HTML.close()


if __name__ == '__main__':
    main()

