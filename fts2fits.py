#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

Created by Josh Walawender on 2013-05-14.
Copyright (c) 2013 __MyCompanyName__. All rights reserved.
"""

import sys
import getopt
import fnmatch
import shutil
import os

help_message = '''
The help message goes here.
'''


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hv", ["help"])
        except getopt.error, msg:
            raise Usage(msg)
    
        # option processing
        for option, value in opts:
            if option == "-v":
                verbose = True
            if option in ("-h", "--help"):
                raise Usage(help_message)
    
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2


    for item in sys.argv[1:]:
        if fnmatch.fnmatch(item, "*.fts"):
            newitem = item.replace("fts", "fits")
            print "copying %s to %s" % (item, newitem)
            if not os.path.exists(newitem):
                shutil.copy(item, newitem)
            else:
                print "  %s already exists" % newitem

if __name__ == "__main__":
    sys.exit(main())
