#!/usr/bin/python
###############################################################################
# @File         logmerge.py
# @Title        HTB and FW log merging script
# @Copyright    Copyright (c) Imagination Technologies Ltd. All Rights Reserved
# @Description  Script to execute a set of tests and collate the benchmark
#               performance into a single report.
#
#               A Host Trace can be merged with a corresponding Firmware Trace.
#               This is achieved by inserting synchronisation data into both
#               traces and post processing to merge them.
#
#               The FW Trace will contain a "Sync Partition Marker". This is
#               updated every time the RGX is brought out of reset (RGX clock
#               timestamps reset at this point) and is repeated when the FW
#               Trace buffer wraps to ensure there is always at least 1
#               Partition Marker in the Firmware Trace buffer whenever it is
#               read.
#
#               The Host Trace will contain corresponding "Sync Partition
#               Markers". Each partition is then subdivided into "Sync Scale"
#               sections. The "Sync Scale" data allows the timestamps from the
#               two traces to be correlated. The "Sync Scale" data is updated as
#               part of the standard RGX time correlation code (rgxtimecorr.c)
#               and is updated periodically including on power and clock
#               changes.
#
# @License      Strictly Confidential.
###############################################################################

import sys

#############################
# Log syntax markers
#############################
SYNC_PARTITION_MK="marker:"
SYNC_PARTITION_RPT="repeat:"
SYNC_PARTITION_OFF=-1
SYNC_PARTITION_BASE=10

SYNC_SCALE_MK="HTBFWSync"

OSTS_ID="OSTS"
OSTS_BASE=16
OSTS_OFF=-1

CRTS_ID="CRTS"
CRTS_BASE=16
CRTS_OFF=-1

CLKS_ID="CalcClkSpd"
CLKS_BASE=10
CLKS_OFF=-1

LOGTS_BASE=10
#############################

# sync timestamps are in ns, but log timestamps are in us
# so alter calculated timestamps by 1/TIME_SCALE
TIME_SCALE=1000
#############################

LOGPAD="**********"
#############################


###############################################################################
# Find and return the value of the current or next SYNC_PARTITION in the file
###############################################################################
def find_next_sp_or_rpt(f):
    sp = 0
    line = f.readline()
    while line:
        if (SYNC_PARTITION_MK in line) or (SYNC_PARTITION_RPT in line):
            sp = int(line.split()[SYNC_PARTITION_OFF], SYNC_PARTITION_BASE)
            break
        line = f.readline()
    return (sp, line)


###############################################################################
# Find and return the value of the next SYNC_PARTITION in the given file
###############################################################################
def find_next_sp(f):
    sp = 0
    line = f.readline()
    while line:
        if SYNC_PARTITION_MK in line:
            sp = int(line.split()[SYNC_PARTITION_OFF], SYNC_PARTITION_BASE)
            break
        line = f.readline()
    return (sp, line)


###############################################################################
# Find and return the value of a given SYNC_PARTION in the given file
# SYNC_PARTITIONs are assumed to be always increasing
# SYNC_PARTITIONs with value 0 are ignored
###############################################################################
def find_sp(f, sp):
    line="non-empty string"
    new_sp = 0
    while line and new_sp < sp:
        new_sp, line = find_next_sp(f)
    return (new_sp, line)


###############################################################################
# Read a line
###############################################################################
def read_line(f):
    pos = f.tell()
    line = f.readline()

    if line and not SYNC_PARTITION_MK in line:
        try:
            line_ts, sep, message = line.partition(':')
            return message, int(line_ts)
        except ValueError:
            return (line, 0)
    f.seek(pos)


###############################################################################
# Read a line if its timestamp is less than the one provided
###############################################################################
def read_line_ts(f, ts):
    pos = f.tell()
    line = f.readline()
    if line and not SYNC_PARTITION_MK in line:
        try:
            line_ts, sep, message = line.partition(':')
            if not int(ts) or int(line_ts) < int(ts):
                return message, int(line_ts)
        except ValueError:
            return (line, 0)
    f.seek(pos)
    return ("", 0)


###############################################################################
# Print a log line with timestamp
###############################################################################
def print_log_line(message, ts):
    print "%010d:%s" % (ts, message),


###############################################################################
# Get Host and FW native timestamps from the next SYNC_SCALE line
# return 0 if no valid line is found
###############################################################################
def get_log_block_end_ts(h):
    pos = h.tell()
    line = h.readline()
    ts = 0
    cr_ts = 0

    while line and not SYNC_PARTITION_MK in line:
        if SYNC_SCALE_MK in line:
            ts, sep, message = line.partition(':')
            for token in message.split():
                if CRTS_ID in token:
                    cr_ts = int(token.split('=')[CRTS_OFF], CRTS_BASE)
            break;
        line = h.readline()

    h.seek(pos)
    return int(ts), int(cr_ts)


###############################################################################
# Convert timestamp from FW clock to real time
###############################################################################
def convert_fw_clock(clock, offset, scale):
#    return (offset + (clock * scale))
    return ((float(offset) + (float(clock) * float(scale)))/TIME_SCALE)


###############################################################################
# Process the two log files within the scope of the current scale parameters
###############################################################################
def sync_block_loop(h, f, scale_params):
    # scan ahead for next scale_params block, partition, or EOF
    os_ts_limit, fw_ts_limit = get_log_block_end_ts(h)

    h_line, osts_us = read_line_ts(h, os_ts_limit)
    f_line, fwts_clk = read_line_ts(f, fw_ts_limit)
    fwts_us = convert_fw_clock(fwts_clk, *scale_params)

    # loop while log line timestamps are within the limit of the block
    # and not a Sync Partition or an EOF
    while h_line and f_line:
        if fwts_us < osts_us:
            print_log_line(f_line, fwts_us)
            f_line, fwts_clk = read_line_ts(f, fw_ts_limit)
            fwts_us = convert_fw_clock(fwts_clk, *scale_params)
        else:
            print_log_line(h_line, osts_us)
            h_line, osts_us = read_line_ts(h, os_ts_limit)

    while f_line:
        print_log_line(f_line, fwts_us)
        f_line, fwts_clk = read_line_ts(f, fw_ts_limit)
        fwts_us = convert_fw_clock(fwts_clk, *scale_params)
    while h_line:
        print_log_line(h_line, osts_us)
        h_line, osts_us = read_line_ts(h, os_ts_limit)



###############################################################################
# Parse the Sync Scale data and return the scale parameters
###############################################################################
def get_sync_scale_params(line, unused):
    if not SYNC_SCALE_MK in line:
        print "Sync data expected but not found, offending Host Trace line:"
        print "            %s" % line
        return

    for token in line.split():
        if OSTS_ID in token:
            os_ts = int(token.split('=')[OSTS_OFF], OSTS_BASE)
        elif CRTS_ID in token:
            cr_ts = int(token.split('=')[CRTS_OFF], CRTS_BASE)
        elif CLKS_ID in token:
            spd = int(token.split('=')[CLKS_OFF], CLKS_BASE)

    scale_factor = 256000000000/float(spd)
    offset_ns = os_ts - (cr_ts*scale_factor)

#    return (offset_ns/TIME_SCALE, scale_factor/TIME_SCALE)
    return (offset_ns, scale_factor)


###############################################################################
# Loop over all Sync Blocks within the current Sync Partition
###############################################################################
def sync_partition_loop(h, f, sync_pt):
    print "%s: SYNC_PARTITION Marker: %d" % (LOGPAD, sync_pt)
    line = read_line(h)
    while line:
        scale_params = get_sync_scale_params(*line)
        if scale_params:
            print_log_line(*line)
            sync_block_loop(h, f, scale_params)
            line = read_line(h)
        else:
            break


###############################################################################
# Process FW logs before the first FW SYNC_PARTITION
# if there is a valid corresponding Host SYNC_PARTITION
###############################################################################
def old_sync_partition_preamble(h, f):
    f_sp, ok = find_next_sp(f)
    if ok:
        h_sp, ok = find_next_sp(h)

    if ok and h_sp < f_sp:
        # find the Host SYNC_PARTITION preceding the first
        # (partial) FW SYNC_PARTION
        while h_sp < f_sp and ok:
            target_sp = h_sp
            h_sp, ok = find_next_sp(h)

        # rewind files
        h.seek(0)
        f.seek(0)

        find_sp(h, target_sp)
        sync_partition_loop(h, f, target_sp)

    else:
        # rewind files
        h.seek(0)
        f.seek(0)


###############################################################################
###############################################################################
def sync_partition_preamble(h, f):
    f_sp, f_sp_type = find_next_sp_or_rpt(f)
    if f_sp:
        h_sp, ok = find_next_sp(h)

    if f_sp and h_sp and h_sp < f_sp:
        # find the Host SYNC_PARTITION preceding the first (partial)
        # FW SYNC_PARTION and the one corresponding to it
        while h_sp < f_sp and ok:
            prev_sp = h_sp
            h_sp, ok = find_next_sp(h)

        # rewind files
        h.seek(0)
        f.seek(0)

        if SYNC_PARTITION_RPT in f_sp_type:
            target_sp = h_sp
        else:
            target_sp = prev_sp

        find_sp(h, target_sp)
        sync_partition_loop(h, f, target_sp)

    else:
        # rewind files
        h.seek(0)
        f.seek(0)


###############################################################################
# Usage
###############################################################################
def print_usage():
    print
    print "logmerge.py -",
    print "Merge Host and Firmware logs, converting FW clock timestamps to us"
    print
    print "Usage:"
    print "    logmerge.py hosttrace.log fwtrace.log"
    print


###############################################################################
# Main: Host log file Firmware log file
###############################################################################

if len(sys.argv) != 3:
    print_usage()
    sys.exit()

try:
    host_file = open(sys.argv[1], "r")
except IOError:
    print "Host Trace input file not found: %s" % (sys.argv[1])
    print_usage()
    sys.exit()

try:
    fw_file = open(sys.argv[2], "r")
except IOError:
    print "Firmware Trace input file not found: %s" % (sys.argv[2])
    print_usage()
    sys.exit()

sync_partition_preamble(host_file, fw_file)

# Print interleaved logs until either source is exhausted
f_sync = 0
while True:
    h_sync, host_line = find_next_sp(host_file)
    if not host_line:
        print "**********: Host file EOF"
        break

    f_sync, fw_line = find_sp(fw_file, h_sync)
    if not fw_line:
        print "**********: FW File EOF"
        break

    if f_sync != h_sync:
        print "**********: FW sync %d does not match Host sync %d" % (f_sync, h_sync)
        continue

    sync_partition_loop(host_file, fw_file, h_sync)

fw_file.close()
host_file.close()

# EOF
