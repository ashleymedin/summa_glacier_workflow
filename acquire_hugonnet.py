#!/usr/bin/env python3
"""Write a glacier's cumulative mass change from Hugonnet et al. (2021) as a SUMMA calibration observation file.

The source is the per-glacier cumulative elevation change (dh_<region>_rgi60_pergla_cumul.csv.zip, monthly, 2000-2019), times 850 kg m-3.
Each value is its mean over a water year, mm w.e., and is for a target with accumulate = true and a baseline, which compares departures
from the first year's mean; the file's time bounds are the water years. Elevation change is per the glacier's RGI area.

    ./acquire_hugonnet.py data/external/Hugonnet/time_series_01/dh_01_rgi60_pergla_cumul.csv.zip RGI60-01.01506 lemoncreek_hugonnet_01506.nc
"""

import argparse
import csv
import datetime as dt
import io
import zipfile

import numpy as np

from observation_netcdf import write_observations


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("archive")
    p.add_argument("glacier", help="RGI 6.0 id")
    p.add_argument("output")
    p.add_argument("--first", type=int, default=2006, help="first water year written; the first inside the run, as the baseline needs a whole simulated year")
    p.add_argument("--last", type=int, default=2019)
    a = p.parse_args()
    t, dh, err = [], [], []
    with zipfile.ZipFile(a.archive) as z, z.open(z.namelist()[0]) as f:
        for r in csv.DictReader(io.TextIOWrapper(f)):
            if r["rgiid"] == a.glacier:
                t.append(dt.datetime.fromisoformat(r["time"])); dh.append(float(r["dh"])); err.append(float(r["err_dh"]))
    if not t:
        raise SystemExit(f"{a.glacier} not in {a.archive}")
    sec = np.array([x.timestamp() for x in t])
    starts = [dt.datetime(y - 1, 10, 1) for y in range(a.first, a.last + 1)]
    ends = [dt.datetime(y, 10, 1) for y in range(a.first, a.last + 1)]
    hours = lambda s, e: np.linspace(s.timestamp(), e.timestamp(), 366)
    values = [850.0 * float(np.interp(hours(s, e), sec, dh).mean()) for s, e in zip(starts, ends)]
    write_observations(a.output, starts, ends, values, "mb_obs", "mm", "cumulative glacier-wide mass change, water equivalent, water-year mean",
                       attrs={"title": f"Cumulative mass change of {a.glacier}, for SUMMA calibration",
                              "source": "Hugonnet et al. (2021) doi:10.1038/s41586-021-03436-z per-glacier elevation change, 850 kg m-3",
                              "comment": f"departures from a baseline year only; mean 1-sigma of the cumulative elevation change {np.mean(err):.1f} m"})
    print(f"{a.output}: {len(values)} water years, {(values[-1] - values[0]) / (len(values) - 1):.0f} mm yr-1")


if __name__ == "__main__":
    main()
