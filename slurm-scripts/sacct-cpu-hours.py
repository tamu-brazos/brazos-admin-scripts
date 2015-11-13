#!/usr/bin/env python

import argparse
from subprocess import Popen, PIPE
from datetime import date
from dateutil.relativedelta import relativedelta
from calendar import monthrange
import time
import os, sys, re

def slurm_time_to_sec(t, debug=False):
    t_f = re.findall(r"[\d]+", t)
    if debug: print "slurm_time_to_sec: %s -> %s" % (t, t_f)
    sec = 0
    # Handle days which aren't always present
    if len(t_f) == 4:
        offset = 4
        sec += 86400 * int(t_f[0])
    else:
        offset = 3
    # Hours
    sec += 3600 * int(t_f[offset-3])
    # Minutes
    sec += 60 * int(t_f[offset-2])
    # Seconds
    sec += int(t_f[offset-1])

    return sec

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
parser.add_argument('--debug', help="debug output", action="store_true", default=False)
args = parser.parse_args()

cmd = [	"sacct", "--allusers", "--parsable2", "--noheader", "--allocations", "--clusters", "brazos" ]
if args.account:
    cmd += "--accounts=%s" % args.account
if args.user:
    cmd += "--user=%s" % args.user
cmd += [
    "--format", "elapsed,ncpus",
    "--state", "CANCELLED,COMPLETED,FAILED,NODE_FAIL,PREEMPTED,TIMEOUT",
	"--starttime", args.start,
	"--endtime", args.end,
]

cmd_str = " ".join(cmd)

print cmd_str

cpu_hours = 0.0

process = Popen(cmd, stdout=PIPE)
out, err = process.communicate()

for line in out.split(os.linesep):
    _line =  line.strip()
    if args.debug: print "_line: %s" % _line
    if not _line:
        continue
    _data = _line.split("|")
    if args.debug: print "_data: %s" % _data
    _elapsed_sec = slurm_time_to_sec(t=_data[0], debug=args.debug)
    _hours = float(_elapsed_sec) / 3600.0
    _ncpus = int(_data[1])
    _cpu_hours = _hours * float(_ncpus)
    if args.debug: print "H: %f C: %d - CH: %f" % (_hours, _ncpus, _cpu_hours)
    cpu_hours = cpu_hours + _cpu_hours

print "CPU HOURS: %f" % cpu_hours