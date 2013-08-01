#!python

import subprocess32

## Get CPU Load over Last 1 minute
IOStatOutput = subprocess32.check_output('iostat', timeout=5)
idx_1m = IOStatOutput.split("\n")[1].split().index("1m")
CPU_1m = IOStatOutput.split("\n")[2].split()[idx_1m]

## Get Temperatures
TempHeader = subprocess32.check_output(['tempmonitor', '-f', '-th'], timeout=5)
TempOutput = subprocess32.check_output(['tempmonitor', '-f', '-tv'], timeout=5)
idx_cpu = TempHeader.split(",").index('"SMC CPU A PROXIMITY"')
TempCPU = TempOutput.split(",")[idx_cpu]
idx_time = TempHeader.split(",").index('"DATE AND TIME"')
TimeStamp = TempOutput.split(",")[idx_time]

## Write To Log
