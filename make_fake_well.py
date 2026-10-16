#!/usr/bin/env python3
"""Write a synthetic well record from a reference SUMMA run, for a calibration test's well target.

The record is the run's own series of one HRU variable (default scalarAquiferStorage, m), as the calibration
driver collects an hru target: the mean over the HRU's domains weighted by their area (objfunc/simulated_series.f90;
the reference run has to write DOMarea), then the mean over each UTC day, stamped at the day's end. A trial at the
reference run's parameters reproduces it, so the target tests the machinery, not the model.

    ./make_fake_well.py wellref_timestep.nc 5 2015-10-01 2018-12-31 well_hru5_daily.nc
"""

import argparse
import datetime as dt
import os
import sys

import netCDF4 as nc4
import numpy as np

SUMMA_DIR = os.environ.get("SUMMA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "summa"))
sys.path.insert(0, os.path.join(SUMMA_DIR, "utils", "pre-processing"))
from observation_netcdf import write_observations


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("timestep", help="SUMMA timestep output of the reference run")
    p.add_argument("hru", type=int, help="hruId of the well")
    p.add_argument("first_day", help="YYYY-MM-DD, first day written")
    p.add_argument("last_day", help="YYYY-MM-DD, last day written")
    p.add_argument("output")
    p.add_argument("--variable", default="scalarAquiferStorage")
    a = p.parse_args()

    with nc4.Dataset(a.timestep) as d:
        d.set_auto_mask(False)
        ix = list(np.asarray(d["hruId"][:])).index(a.hru)
        values = np.asarray(d[a.variable][:, ix, :], dtype=float)
        areas = np.asarray(d["DOMarea"][:, ix, :], dtype=float)
        units = d[a.variable].units
        times = nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                             only_use_python_datetimes=True)
    areas = np.where((areas > 0) & (values > -9998.0), areas, 0.0)
    hourly = np.sum(np.where(areas > 0, values, 0.0) * areas, axis=1) / np.sum(areas, axis=1)

    first = dt.datetime.fromisoformat(a.first_day)
    last = dt.datetime.fromisoformat(a.last_day)
    days = {}
    for t, v in zip(times, hourly):
        day = (t - dt.timedelta(seconds=1)).date()  # a time stamps the end of its hour
        days.setdefault(day, []).append(v)
    per_day = max(len(v) for v in days.values())
    starts, ends, means = [], [], []
    for day in sorted(days):
        start = dt.datetime.combine(day, dt.time())
        if start < first or start > last or len(days[day]) < per_day:
            continue
        starts.append(start)
        ends.append(start + dt.timedelta(days=1))
        means.append(float(np.mean(days[day])))
    write_observations(a.output, starts, ends, means, "well_obs", units,
                       f"synthetic well: daily mean {a.variable} of HRU {a.hru}",
                       attrs={"title": "synthetic well record from a reference SUMMA run",
                              "source": os.path.abspath(a.timestep),
                              "history": f"created {dt.date.today()} by make_fake_well.py"})
    print(f"{a.output}: {len(means)} days, {min(means):.4g} to {max(means):.4g} {units}")


if __name__ == "__main__":
    main()
