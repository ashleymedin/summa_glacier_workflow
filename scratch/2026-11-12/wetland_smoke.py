#!/usr/bin/env python3
"""One water year of the stream cases of cases.yaml, built in OUT and run from the cold state with routing, to check the
wetland domain is read, takes the glacier's runoff and releases it to the reach. Prints the wetland's monthly inflow,
outflow and temperature beside the stream domain's.

    SUMMA_DIR=<summa> ./wetland_smoke.py OUT [case ...]      default wolverine_stream gulkana_stream

SMOKE_FIRST and SMOKE_LAST (YYYY-MM) change the water year it runs.
"""

import glob
import os
import re
import shutil
import subprocess
import sys

import netCDF4 as nc4
import numpy as np
import yaml

GLACIER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path[:0] = [GLACIER, os.path.join(GLACIER, "runs")]
import build_cases  # noqa: E402
from calibrate import SUMMA_DIR, config_text  # noqa: E402

FIRST, LAST = os.environ.get("SMOKE_FIRST", "2015-10"), os.environ.get("SMOKE_LAST", "2016-09")
OUTPUT = ["scalarStreamLatInflow", "scalarStreamLatInflowTemp", "scalarStreamOutflow", "scalarStreamTemp", "DOMarea",
          "scalarWetlandFullArea"]
WETLAND, STREAM = 5, 6


def main():
    out = os.path.abspath(sys.argv[1])
    with open(os.path.join(GLACIER, "cases.yaml")) as f:
        cases = yaml.safe_load(f)
    for name in sys.argv[2:] or ["wolverine_stream", "gulkana_stream"]:
        spec = dict(cases[name], first_month=FIRST, last_month=LAST, dest=os.path.join(out, name),
                    template=os.path.join(GLACIER, cases[name]["template"]))
        shutil.rmtree(spec["dest"], ignore_errors=True)
        build_cases.build(name, spec, GLACIER)
        run_dir = spec["dest"]
        settings, work = os.path.join(run_dir, "summa_inputs"), os.path.join(run_dir, "smoke")
        with open(os.path.join(settings, "outputControl.txt"), "a") as f:
            f.write("\n" + "".join(f"{v:<26}| 1\n" for v in OUTPUT))
        config = config_text(name, run_dir, settings, work, f"{FIRST}-01", f"{LAST}-30", f"{FIRST}-01", f"{LAST}-30",
                             "dds", 1, 1, temperature=False)
        config = re.sub(r"^write_timeseries .*", "write_timeseries = true", config[:config.index("\n[calibration]")], flags=re.M)
        for d in ("output", "state"):
            os.makedirs(os.path.join(work, d), exist_ok=True)
        shutil.copy(os.path.join(settings, "coldState.nc"), os.path.join(work, "state", "coldState.nc"))
        with open(os.path.join(work, "config.toml"), "w") as f:
            f.write(config)
        with open(os.path.join(work, "run.log"), "w") as log:
            status = subprocess.run([os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute.exe"), "-c",
                                     os.path.join(work, "config.toml")], cwd=work, stdout=log, stderr=subprocess.STDOUT).returncode
        if status:
            raise SystemExit(f"{name}: summa failed ({status}); see {work}/run.log")
        report(name, settings, work)


def report(name, settings, work):
    with nc4.Dataset(os.path.join(settings, "coldState.nc")) as s:
        dom_type = np.array(s["domType"][:]).squeeze()  # (hru, dom)
    files = sorted(glob.glob(os.path.join(work, "output", "*timestep.nc")))
    with nc4.Dataset(files[0]) as d:
        t = nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)
        month = np.array([x.month for x in t])
        reach = np.array(d["T_reach"][:, 0])
        print(f"\n{name}: {files[0]}")
        for kind, label in ((WETLAND, "wetland"), (STREAM, "stream")):
            for hru, dom in zip(*np.where(dom_type == kind)):
                pick = lambda v: np.array(d[v][:]).reshape(len(t), *dom_type.shape)[:, hru, dom]
                print(f"  {label}: HRU index {hru}, domain {dom}, area {pick('DOMarea')[0]:.0f} -> {pick('DOMarea')[-1]:.0f} m2")
                print("    month  inflow m3/s  inflow C  outflow m3/s  water C  reach C")
                for m in list(range(10, 13)) + list(range(1, 10)):
                    k = month == m
                    print(f"    {m:5d}  {pick('scalarStreamLatInflow')[k].mean():11.3f}  "
                          f"{pick('scalarStreamLatInflowTemp')[k].mean() - 273.16:8.2f}  "
                          f"{pick('scalarStreamOutflow')[k].mean():12.3f}  {pick('scalarStreamTemp')[k].mean() - 273.16:7.2f}  {reach[k].mean() - 273.16:7.2f}")


if __name__ == "__main__":
    main()
