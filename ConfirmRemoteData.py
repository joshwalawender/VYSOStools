#!/usr/env/python

from __future__ import division, print_function

## Import General Tools
import sys
import os
import argparse
import logging
import re
import datetime
import glob
import subprocess
import paramiko


##-------------------------------------------------------------------------
## Main Program
##-------------------------------------------------------------------------
def main():

    ##-------------------------------------------------------------------------
    ## Parse Command Line Arguments
    ##-------------------------------------------------------------------------
    ## create a parser object for understanding command-line arguments
    parser = argparse.ArgumentParser(
             description="Program description.")
    ## add flags
    parser.add_argument("-v", "--verbose",
        action="store_true", dest="verbose",
        default=False, help="Be verbose! (default = False)")
    parser.add_argument("--delete",
        action="store_true", dest="delete",
        default=False, help="Delete the file after confirmation of SHA sum?")
    ## add arguments
    parser.add_argument("-t", "--telescope",
        dest="telescope", required=True, type=str,
        choices=["V5", "V20"],
        help="Telescope which took the data ('V5' or 'V20')")
    parser.add_argument("-d", "--date",
        type=str, dest="date",
        help="The date to copy.")
    args = parser.parse_args()

    telescope = args.telescope
    if args.date:
        if re.match('\d{8}UT', args.date):
            date = args.date
        elif args.date == 'yesterday':
            today = datetime.datetime.utcnow()
            oneday = datetime.timedelta(1, 0)
            date = (today - oneday).strftime('%Y%m%dUT')
    else:
        date = datetime.datetime.utcnow().strftime('%Y%m%dUT')

    ## Safety Feature: do not have delete active if working on today's data
    if date == datetime.datetime.utcnow().strftime('%Y%m%dUT'):
        args.delete = False

    ##-------------------------------------------------------------------------
    ## Create logger object
    ##-------------------------------------------------------------------------
    logger = logging.getLogger('ConfirmRemoteData_{}_{}'.format(telescope, date))
    logger.setLevel(logging.DEBUG)
    ## Set up console output
    LogConsoleHandler = logging.StreamHandler()
    if args.verbose:
        LogConsoleHandler.setLevel(logging.DEBUG)
    else:
        LogConsoleHandler.setLevel(logging.INFO)
    LogFormat = logging.Formatter('%(asctime)23s %(levelname)8s: %(message)s')
    LogConsoleHandler.setFormatter(LogFormat)
    logger.addHandler(LogConsoleHandler)
    ## Set up file output
    LogFileName = 'ConfirmRemoteData_{}_{}'.format(telescope, date)
    LogFilePath = os.path.join('/', 'Users', 'vysosuser', 'logs')
    LogFileHandler = logging.FileHandler(os.path.join(LogFilePath, LogFileName))
    LogFileHandler.setLevel(logging.DEBUG)
    LogFileHandler.setFormatter(LogFormat)
    logger.addHandler(LogFileHandler)

    ##-------------------------------------------------------------------------
    ## Confirm Data on Drobo Matches Data in Hilo
    ##-------------------------------------------------------------------------
    drobo_path = os.path.join('/', 'Volumes', 'Drobo', telescope)

    ## Make list of files to analyze
    files = glob.glob(os.path.join(drobo_path, 'Images', date, '*.fts'))
    if os.path.exists(os.path.join(drobo_path, 'Images', date, 'Calibration')):
        files.extend(glob.glob(os.path.join(drobo_path, 'Images', date, 'Calibration', '*.fts')))
    if os.path.exists(os.path.join(drobo_path, 'Images', date, 'AutoFlat')):
        files.extend(glob.glob(os.path.join(drobo_path, 'Images', date, 'AutoFlat', '*.fts')))
    files.extend(glob.glob(os.path.join(drobo_path, 'Logs', date, '*.*')))
    logger.info('Found {} files to analyze'.format(len(files)))

    remote_computer = paramiko.SSHClient()
    remote_computer.load_system_host_keys()
    remote_computer.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    remote_computer.connect(hostname='trapezium.ifa.hawaii.edu', username='vysosuser')

#     remote_path = os.path.join('/', 'Volumes', 'DroboPro1', telescope, date)
    remote_path = os.path.join('/', 'Users', 'vysosuser', 'Data', telescope, 'Images', date)

    ansi_escape = re.compile(r'\x1b[^m]*m')
    for file in files:
        logger.info('Checking file: {}'.format(file))
        filename = os.path.split(file)[1]
        local_shasum = subprocess.check_output(['shasum', file]).split()[0]
        remote_file = os.path.join(remote_path, filename)

        command = 'shasum {}'.format(remote_file)
        stdin, stdout, stderr = remote_computer.exec_command(command)
        ## Handle STDIN
        try:
            stdinlines_with_ansi = stdin.readlines()
            stdinlines = []
            for line in stdinlines_with_ansi:
                cleanedline = ansi_escape.sub('', line).strip('\n')
                stdinlines.append(str(cleanedline))
                if logger: logger.debug('  stdin: {0}'.format(cleanedline))
        except:
            stdinlines = []
        ## Handle STDOUT
        try:
            stdoutlines_with_ansi = stdout.readlines()
            stdoutlines = []
            for line in stdoutlines_with_ansi:
                cleanedline = ansi_escape.sub('', line).strip('\n')
                stdoutlines.append(str(cleanedline))
                if logger: logger.debug('  stdout: {0}'.format(cleanedline))
        except:
            if logger: logger.debug('  No lines read from STDOUT')
            stdoutlines = []
        ## Handle STDERR
        try:
            stderrlines_with_ansi = stderr.readlines()
            stderrlines = []
            for line in stderrlines_with_ansi:
                cleanedline = ansi_escape.sub('', line).strip('\n')
                stderrlines.append(str(cleanedline))
                if logger: logger.debug('  stderr: {0}'.format(cleanedline))
        except:
            if logger: logger.debug('  No lines read from STDERR')
            stderrlines = []

        matchsum = re.match('.*\s+{}'.format(remote_file), stdoutlines[0])
        if matchsum:
            logger.debug('  SHASUM recieved')
            remote_shasum = stdoutlines[0].split()[0]
            if remote_shasum == local_shasum:
                logger.info('  SHASUMs match.')
            else:
                logger.warning('  SHASUMs do not match!')
                logger.debug('  local:  {}'.format(local_shasum))
                logger.debug('  remote: {}'.format(remote_shasum))
        else:
            logger.warning('  Could not parse response.')
            logger.warning('  {}'.format(stdout))



if __name__ == '__main__':
    main()
