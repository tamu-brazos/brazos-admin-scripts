#!/usr/bin/env python

import argparse
from subprocess import Popen, PIPE
from datetime import date
from dateutil.relativedelta import relativedelta
from calendar import monthrange
import time
import dateutil.parser
import os, sys, re
from decimal import Decimal

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib.slurm import slurm_duration_to_sec

def cmp_start_end_time(start, end, debug=False):
    _start = dateutil.parser.parse(start).strftime("%s")
    _end = dateutil.parser.parse(end).strftime("%s")
    _sec = int(_end) - int(_start)
    return _sec

def cmp_start_end_suspended_time(start, end, suspend, debug=False):
    _end_start_sec = cmp_start_end_time(start=start, end=end, debug=debug)
    _suspend = slurm_time_to_sec(t=suspend, debug=debug)
    _sec = int(_end_start_sec) - int(_suspend)
    return _sec

TODAY = date.today()
LAST_MONTH = TODAY - relativedelta(months=1)
LAST_DAY_OF_MONTH=monthrange(LAST_MONTH.year, LAST_MONTH.month)[1]
DEFAULT_STARTTIME="%s-%s-01T00:00:00" % (LAST_MONTH.year, LAST_MONTH.month)
DEFAULT_ENDTIME="%s-%s-%sT23:59:59" % (LAST_MONTH.year, LAST_MONTH.month, LAST_DAY_OF_MONTH)

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--account', help="SLURM account", default=None)
parser.add_argument('--user', help="SLURM user", default=None)
parser.add_argument('--start', help="sacct starttime", default=DEFAULT_STARTTIME)
parser.add_argument('--end', help="sacct endtime", default=DEFAULT_ENDTIME)
parser.add_argument('--calc2', help="calculate using end-start times", action="store_true", default=False)
parser.add_argument('--calc3', help="calculate using end-start times minus suspended time", action="store_true", default=False)
parser.add_argument('--file', help='read sacct output from file instead of command', default=None)
parser.add_argument('--debug', help="debug output", action="store_true", default=False)
args = parser.parse_args()

if args.file:
    if not os.path.isfile(args.file):
        print "ERROR: File %s not found" % args.file
        sys.exit(1)
    with open(args.file, 'r') as file:
        out = file.read()
else:
    cmd = [	"sacct", "--allusers", "--parsable2", "--noheader", "--allocations", "--clusters", "brazos" ]
    if args.account:
        cmd += ["--accounts=%s" % args.account]
    if args.user:
        cmd += ["--user=%s" % args.user]
    cmd += [
        "--format", "elapsed,ncpus,start,end,suspended",
        "--state", "CANCELLED,COMPLETED,FAILED,NODE_FAIL,PREEMPTED,TIMEOUT",
    	"--starttime", args.start,
    	"--endtime", args.end,
    ]
    cmd_str = " ".join(cmd)
    print cmd_str

cpu_hours = Decimal('0.0')

process = Popen(cmd, stdout=PIPE)
out, err = process.communicate()

for line in out.split(os.linesep):
    _line =  line.strip()
    if args.debug: print "_line: %s" % _line
    if not _line:
        continue
    _data = _line.split("|")
    if args.debug: print "_data: %s" % _data
    if args.calc2:
        _elapsed_sec = cmp_start_end_time(start=_data[2], end=_data[3], debug=args.debug)
    elif args.calc3:
        _elapsed_sec = cmp_start_end_suspended_time(start=_data[2], end=_data[3], suspend=_data[4], debug=args.debug)
    else:
        _elapsed_sec = slurm_duration_to_sec(t=_data[0], debug=args.debug)
    _hours = Decimal(str(_elapsed_sec)) / Decimal('3600.0')
    _ncpus = Decimal(_data[1])
    _cpu_hours = _hours * _ncpus
    if args.debug: print "H: %f C: %d - CH: %f" % (_hours, _ncpus, _cpu_hours)
    cpu_hours = cpu_hours + _cpu_hours

print "CPU HOURS: %d" % int(round(cpu_hours, 0))
