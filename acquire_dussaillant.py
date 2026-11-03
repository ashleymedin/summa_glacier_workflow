#!/usr/bin/env python3
"""Write the annual mass change of Dussaillant et al. (2025) for a basin's glaciers as a SUMMA calibration observation file.

The source is the WGMS release "Annual mass-change estimates for the world's glaciers" (doi:10.5904/wgms-amce-2026-02-10),
unzipped under data/external; --release names its folder.  glacier/<region>_mwe.csv holds each RGI 6.0 glacier's
area-average mass change in m w.e. for each hydrological year, labelled by the calendar year it ends in (1 Oct to 30 Sep
in the Northern Hemisphere).  The basin's value is the mean of its glaciers weighted by their RGI areas.

Values are written in mm w.e., each stamped at the end of its year (1 Oct), for a target with balance = "annual", which
compares them with the change between the simulated mass minima near the year ends.  The series is the product's own:
geodetic over the multi-year trend, with its year-to-year shape taken from glaciological records near the glacier.

    ./acquire_dussaillant.py data/external/wgms-amce-2026-02-10 ALA RGI60-01.09162 wolverine_dussaillant.nc --first 2005
"""

import argparse
import csv
import datetime as dt
import os

import numpy as np

from observation_netcdf import write_observations


def read_table(path):
    """Rows of a glacier table as {outline_id: {column: value}}, the first row of a repeated outline kept."""
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            out.setdefault(row["outline_id"], row)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("release", help="folder of the unzipped WGMS release")
    p.add_argument("region", help="GTN-G region code of the glacier files, e.g. ALA")
    p.add_argument("outlines", help="comma-separated RGI 6.0 ids of the basin's glaciers")
    p.add_argument("output", help="NetCDF file to write")
    p.add_argument("--first", type=int, default=2001, help="first hydrological year written")
    a = p.parse_args()

    ids = a.outlines.split(",")
    folder = os.path.join(a.release, "glacier")
    meta = read_table(os.path.join(folder, f"{a.region}_metadata.csv"))
    mwe = read_table(os.path.join(folder, f"{a.region}_mwe.csv"))
    sigma = read_table(os.path.join(folder, f"{a.region}_mwe_sigma.csv"))
    missing = [i for i in ids if i not in mwe]
    if missing:
        raise SystemExit(f"{missing} not in {a.region}_mwe.csv")
    area = np.array([float(meta[i]["area_km2"]) for i in ids])
    years = [int(y) for y in next(iter(mwe.values())) if y.isdigit() and int(y) >= a.first]

    def mean(table, year):
        v = np.array([float(table[i][str(year)]) if table[i][str(year)] not in ("", "nan") else np.nan for i in ids])
        return np.nan if np.isnan(v).any() else float(np.sum(v * area) / area.sum())

    values = [1000.0 * mean(mwe, y) for y in years]
    # glaciers' errors are strongly correlated, so the basin's is taken as the area-weighted mean of theirs
    sig = [1000.0 * mean(sigma, y) for y in years]
    keep = [k for k, v in enumerate(values) if not np.isnan(v)]
    years, values, sig = [years[k] for k in keep], [values[k] for k in keep], [sig[k] for k in keep]

    starts = [dt.datetime(y - 1, 10, 1) for y in years]
    ends = [dt.datetime(y, 10, 1) for y in years]
    write_observations(
        a.output, starts, ends, values,
        varname="mb_obs", units="mm", long_name="annual glacier-wide mass change, water equivalent",
        cell_methods="time: sum",
        attrs={
            "title": "Annual mass change of the basin's glaciers, Dussaillant et al. (2025), for SUMMA calibration",
            "source": "WGMS (2026) doi:10.5904/wgms-amce-2026-02-10; Dussaillant et al. (2025) doi:10.5194/essd-17-1977-2025",
            "glaciers": ", ".join(ids),
            "comment": "Area-weighted mean over the glaciers of the hydrological-year mass change, 1 Oct to 30 Sep; "
                       f"mean 1-sigma {np.mean(sig):.0f} mm per year.",
            "history": f"created {dt.date.today()} by acquire_dussaillant.py",
        },
        time_zone="dates only",
    )
    print(f"{a.output}: {len(values)} annual values {years[0]} to {years[-1]}, mean {np.mean(values):.0f} mm, 1-sigma {np.mean(sig):.0f} mm")


if __name__ == "__main__":
    main()
