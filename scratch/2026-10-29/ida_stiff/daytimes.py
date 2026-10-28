#!/usr/bin/env python3
"""Time each simulated day of a running single-process SUMMA run by watching its run.log (1 s resolution, wall clock).
usage: daytimes.py tag    (run ensemble.py with ONLY=<set> NW=1 under the same tag first); writes days_<tag>.csv"""
import sys, os, re, time, glob
S = os.path.dirname(os.path.abspath(__file__)); tag = sys.argv[1]
pat = re.compile(r"^\s*(20\d\d)\s+(\d+)\s+(\d+)\s+0\s+0\s*$", re.M)
seen, rows, t0 = 0, [], None
while True:
    f = glob.glob(f"{S}/ens_{tag}/*/run.log")
    if f:
        txt = open(f[0]).read(); d = pat.findall(txt); now = time.time()
        for x in d[seen:]: rows.append(("%s-%02d-%02d" % (x[0], int(x[1]), int(x[2])), now))
        seen = len(d)
        if "FORTRAN STOP" in txt or "elapsed physics" in txt: break
    time.sleep(0.5)
with open(f"{S}/days_{tag}.csv", "w") as o:
    for (a, ta), (b, tb) in zip(rows, rows[1:]): o.write(f"{a},{tb - ta:.1f}\n")
