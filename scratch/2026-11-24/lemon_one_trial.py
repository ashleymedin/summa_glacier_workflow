#!/usr/bin/env python3
"""One DDS trial of a case at its default parameters through the calibration driver, the aligned target series written (check of the targets)."""
import os, sys
W = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")); sys.path.insert(0, W + "/runs"); os.chdir(W + "/runs")
import calibrate as c
case, name, end, targ = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
run = f"{W}/runs/{case}"; work = f"{run}/{name}"; s = c.search_for(case, "domain")
keep = ["routingGammaShape"]  # one harmless parameter held at its default, the rest at the files' values
search = {"params": keep, "logs": [], "chains": [], "bounds": {"routingGammaShape": (2.5, 2.5)}}
t = c.config_text(case, run, run + "/summa_inputs", work, "2005-10-01", end, "2005-10-01", end, "dds", 1, 1, False, search=search)
t = t.replace("write_aligned = false", "write_aligned = true").replace("write_timeseries = false", "write_timeseries = true")
c.run_driver(work, t, run + "/summa_inputs", 2)
import netCDF4 as nc
d = nc.Dataset(c.calibration_file(work)); print(d["objective"].target, d["objective"][:])
