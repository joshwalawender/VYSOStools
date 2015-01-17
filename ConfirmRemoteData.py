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


def check_remote_shasum(remote_computer, remote_file, logger):
    ansi_escape = re.compile(r'\x1b[^m]*m')
    shasum_cmd = 'shasum {}'.format(remote_file)
    stdin, stdout, stderr = remote_computer.exec_command(shasum_cmd)
    ## stdout
    try:
        lines_with_ansi = stdout.readlines()
        lines = []
        for line in lines_with_ansi:
            cleanedline = ansi_escape.sub('', line).strip('\n')
            lines.append(str(cleanedline))
            logger.debug('  STDOUT: {}'.format(cleanedline))
        stdout = lines
    except:
        stdout = []
    ## stderr
    try:
        lines_with_ansi = stderr.readlines()
        lines = []
        for line in lines_with_ansi:
            cleanedline = ansi_escape.sub('', line).strip('\n')
            lines.append(str(cleanedline))
            logger.warning('  STDERR: {}'.format(cleanedline))
        stderr = lines
    except:
        stderr = []

    if (len(stderr) == 0):
        matchsum = re.match('.*\s+{}'.format(remote_file), stdout[0])
        if matchsum:
            logger.debug('  SHASUM recieved')
            remote_shasum = stdout[0].split()[0]
        else:
            remote_shasum = None
    elif re.search('No such file or directory', stderr[0]):
        logger.info('  Did not find file on remote machine.')
        remote_shasum = None
    else:
        logger.warning('  STDERR: {}'.format(stderr))
        remote_shasum = None

    return remote_shasum


def copy_file(file, local_shasum, remote_file, remote_computer_string, remote_computer, logger):
    ## Create Directories on Remote Machine as Needed
    remote_dest2 = os.path.split(remote_file)[0]
    remote_dest1 = os.path.split(remote_dest2)[0]
    mkdir_cmd1 = 'mkdir {}'.format(remote_dest1)
    mkdir_cmd2 = 'mkdir {}'.format(remote_dest2)
    logger.debug('  Ensuring {} exists'.format(remote_dest1))
    stdin, stdout, stderr = remote_computer.exec_command(mkdir_cmd1)
    logger.debug('  Ensuring {} exists'.format(remote_dest2))
    stdin, stdout, stderr = remote_computer.exec_command(mkdir_cmd2)

    ## Copy File
    scp_cmd = ['scp', file, '{}:{}'.format(remote_computer_string, remote_file)]
    logger.debug('  Running: {}'.format(' '.join(scp_cmd)))
    subprocess.call(scp_cmd)
    remote_shasum = check_remote_shasum(remote_computer, remote_file, logger)
    if not remote_shasum:
        logger.warning('  Copy to remote machine failed')
        return False
    elif remote_shasum == local_shasum:
        logger.info('  SHASUMs match.')
        return True
    else:
        logger.warning('  SHASUMs do not match!')
        logger.debug('  local:  {}'.format(local_shasum))
        logger.debug('  remote: {}'.format(remote_shasum))
        return False


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
    parser.add_argument("--copy",
        action="store_true", dest="copy",
        default=False, help="Copy the file over if SHASUM mismatch?")
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

    remote_computer_string = 'vysosuser@trapezium.ifa.hawaii.edu'
    remote_computer = paramiko.SSHClient()
    remote_computer.load_system_host_keys()
    remote_computer.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    remote_computer.connect(hostname=remote_computer_string.split('@')[1],\
                            username=remote_computer_string.split('@')[0])

#     remote_path = os.path.join('/', 'Volumes', 'DroboPro1', telescope)
    remote_path = os.path.join('/', 'Users', 'vysosuser', 'Data', telescope)

    for file in files:
        logger.info('Checking file: {}'.format(file))
        filename = os.path.split(file)[1]
        local_shasum = subprocess.check_output(['shasum', file]).split()[0]
        remote_file = file.replace(drobo_path, remote_path)
        remote_shasum = check_remote_shasum(remote_computer, remote_file, logger)

        ## Check Remote SHASUM against local SHASUM
        if not remote_shasum:
            if args.copy:
                logger.info('  Copying file to remote machine')
                copy_file(file, local_shasum, remote_file, remote_computer_string, remote_computer, logger)
        elif remote_shasum == local_shasum:
            logger.info('  SHASUMs match.')
        else:
            logger.warning('  SHASUMs do not match!')
            logger.debug('  local:  {}'.format(local_shasum))
            logger.debug('  remote: {}'.format(remote_shasum))
            if args.copy:
                logger.info('  Copying file to remote machine')
                copy_file(file, local_shasum, remote_file, remote_computer_string, remote_computer, logger)



if __name__ == '__main__':
    main()
