#!/usr/bin/env python3
"""Fetch or rebuild a domain's observations over its forcing_period, from the `observations:` block of its domain YAML.

Every key is optional, so a basin without the data leaves it out (the mass balance is the USGS benchmark glaciers' only):

  streamflow          {source: usgs|wsc, gauge}                  calibration/<source>_<gauge>_daily_flow.nc
  stream_temperature  {site, aquarius?}                          calibration/USGS_<site>_daily_temperature.nc; aquarius
                                                                 is an hourly export under observations/ in place of USGS's daily means
  grace               true                                       calibration/<domain>_grace_tws.nc, the cell holding GRU 1
  mass_balance        {release, balance: seasonal|annual}        calibration/<domain>_mass_balance_<balance>.nc from the
                                                                 USGS release table under observations/ (a by-hand download)
  velocity            true                                       storage/velocity/itslive_annual.npz
  lake_area           [{name, box: [W, S, E, N], usgs_site?}]    lake_area/<name>_{landsat,sentinel2}.csv, one scan a year

Paths are relative to the domain's observations folder; the clock is UTC, as the forcing is.

    ./acquire_observations.py domains/wolverine.yaml --only streamflow lake_area --jobs 8
"""

import argparse
import calendar
import csv
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS = ("streamflow", "stream_temperature", "grace", "mass_balance", "velocity", "lake_area")


DRY = False


def run(*args):
    print("$ " + " ".join(str(x) for x in args), flush=True)
    if not DRY:
        subprocess.run([str(x) for x in args], check=True)


def period(c):
    first, last = c["forcing_period"]["first"], c["forcing_period"]["last"]
    y, m = (int(v) for v in last.split("-"))
    return f"{first}-01", f"{last}-{calendar.monthrange(y, m)[1]:02d}"


def lake_area(c, spec, obs, jobs):
    """One scan per sensor and year in parallel, merged by date and scene into one CSV per sensor."""
    start, end = period(c)
    first, last = int(start[:4]), int(end[:4])
    os.makedirs(os.path.join(obs, "lake_area"), exist_ok=True)
    for source, label, years in (("landsat", "landsat", range(first, last + 1)),
                                 ("sentinel2", "sentinel2", range(max(first, 2015), last + 1))):
        parts = {}
        for y in years:
            parts[y] = os.path.join(obs, "lake_area", f".{spec['name']}_{label}_{y}.csv")
        def scan(y):
            lo, hi = max(f"{y}-01-01", start), min(f"{y}-12-31", end)
            args = [sys.executable, os.path.join(HERE, "acquire_lake_area.py"), *map(str, spec["box"]), lo, hi, parts[y], "--source", source]
            if spec.get("usgs_site"):
                args += ["--usgs-site", str(spec["usgs_site"])]
            run(*args)
        with ThreadPoolExecutor(jobs) as pool:
            list(pool.map(scan, years))
        if DRY:
            continue
        rows = {}
        for y, f in parts.items():
            with open(f) as fh:
                for r in csv.DictReader(fh):
                    rows[(r["date"], r["scene"])] = r
            os.remove(f)
        out = os.path.join(obs, "lake_area", f"{spec['name']}_{label}.csv")
        with open(out, "w", newline="") as fh:
            w = csv.DictWriter(fh, ["date", "scene", "water_km2", "bad", "snow", "q_cms"])
            w.writeheader()
            w.writerows(rows[k] for k in sorted(rows))
        print(f"{out}: {len(rows)} scenes")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--only", nargs="+", choices=KINDS, help="kinds to fetch; default every kind the YAML names")
    p.add_argument("--jobs", type=int, default=6, help="lake-area scans at once")
    p.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    a = p.parse_args()
    global DRY
    DRY = a.dry_run
    c = load_config(a.config)
    spec = c.get("observations") or {}
    obs = os.path.join(c["project_dir"], "observations")
    cal = os.path.join(obs, "calibration")
    os.makedirs(cal, exist_ok=True)
    start, end = period(c)
    py = sys.executable
    for kind in (a.only or [k for k in KINDS if k in spec]):
        if kind not in spec:
            print(f"{kind}: not in the YAML, skipped")
            continue
        s = spec[kind]
        if kind == "streamflow":
            run(py, os.path.join(HERE, "acquire_streamflow.py"), s["source"], s["gauge"], start, end,
                os.path.join(cal, f"{s['source'].upper()}_{s['gauge']}_daily_flow.nc"), "--model-utc-offset", 0)
        elif kind == "stream_temperature":
            args = [py, os.path.join(HERE, "acquire_stream_temperature.py"), s["site"], start, end,
                    os.path.join(cal, f"USGS_{s['site']}_daily_temperature.nc"), "--model-utc-offset", 0]
            if s.get("aquarius"):
                args += ["--aquarius", os.path.join(obs, s["aquarius"])]
            run(*args)
        elif kind == "grace":
            run(py, os.path.join(HERE, "acquire_grace_tws.py"), "--attributes",
                os.path.join(c["project_dir"], "settings", "SUMMA", "attributes.nc"), "--gru", 1,
                os.path.join(cal, f"{c['domain'].lower()}_grace_tws.nc"))
        elif kind == "mass_balance":
            run(py, os.path.join(HERE, "acquire_glacier_mass_balance.py"), os.path.join(obs, s["release"]), s["balance"],
                os.path.join(cal, f"{c['domain'].lower()}_mass_balance_{s['balance']}.nc"))
        elif kind == "velocity":
            run(py, os.path.join(HERE, "acquire_velocity.py"), a.config, "--first", start[:4])
        elif kind == "lake_area":
            for lake in s:
                lake_area(c, lake, obs, a.jobs)


if __name__ == "__main__":
    main()
