#!/usr/bin/env python3
"""Spin a built case up to a thermal equilibrium: the year before its calibrate start is cycled N times (30 by default)
from the cold state, each cycle restarting from the last restart file, and the final state replaces summa_inputs/coldState.nc.

The glacier ice, debris, soil, snow and canopy all start from the cold state's values and settle over the cycles; the
accumulated area-change mass is zeroed in the result. The cold state it started from is kept as coldState_cold.nc and
a rerun starts from it again. Needs summa's serial TOML executable (bin/summa_sundials_mizuroute.exe).

    ./spinup.py gulkana_added
    ./spinup.py wolverine_general --years 40
"""

import argparse
import datetime
import glob
import os
import re
import shutil
import subprocess

import netCDF4 as nc4
import numpy as np

from calibrate import GLACIER, HERE, SUMMA_DIR, config_text, periods


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__)
    p.add_argument("case", help="run folder, e.g. gulkana_added")
    p.add_argument("--years", type=int, default=30, help="cycles of the spin-up year")
    a = p.parse_args()
    run_dir = os.path.join(HERE, a.case)
    settings = os.path.join(run_dir, "summa_inputs")
    work = os.path.join(run_dir, "spinup")
    cal0 = datetime.date.fromisoformat(periods(a.case)[0])
    start = cal0.replace(year=cal0.year - 1)
    end = cal0 - datetime.timedelta(days=1)
    config = config_text(a.case, run_dir, settings, work, str(start), str(end), str(start), str(end), "dds", 1, 1, temperature=False)
    config = config[:config.index("\n[calibration]")]
    config = re.sub(r"^use_mizuroute .*", "use_mizuroute    = false", config, flags=re.M)
    cold = os.path.join(settings, "coldState_cold.nc")
    if not os.path.exists(cold):
        shutil.copy(os.path.join(settings, "coldState.nc"), cold)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(work, "output"))
    os.makedirs(os.path.join(work, "state"))
    with open(os.path.join(work, "config.toml"), "w") as f:
        f.write(config)
    exe = os.path.join(SUMMA_DIR, "bin", "summa_sundials_mizuroute.exe")
    current = cold
    for k in range(1, a.years + 1):
        for d in glob.glob(os.path.join(work, "state", "*")) + glob.glob(os.path.join(work, "output", "*")):
            os.remove(d)
        shutil.copy(current, os.path.join(work, "state", "coldState.nc"))
        with open(os.path.join(work, "run.log"), "w") as log:
            status = subprocess.run([exe, "-c", os.path.join(work, "config.toml"), "-r", "e"], cwd=work,
                                    stdout=log, stderr=subprocess.STDOUT).returncode
        restarts = sorted(glob.glob(os.path.join(work, "state", "*restart*.nc")) + glob.glob(os.path.join(work, "output", "*restart*.nc")))
        if status or not restarts:
            raise SystemExit(f"spin-up cycle {k} of {a.case} failed ({status}); see {work}/run.log")
        current = os.path.join(work, f"cycle_{k % 2}.nc")
        shutil.copy(restarts[-1], current)
        print(f"{a.case}: cycle {k}/{a.years}", flush=True)
    with nc4.Dataset(current, "r+") as d:
        v = d["glacMass4AreaChange"]
        x = np.ma.filled(v[:], 0.0)
        v[:] = np.where(np.abs(x) > 1e30, x, 0.0)
    shutil.copy(current, os.path.join(settings, "coldState.nc"))
    print(f"{a.case}: spun up over {a.years} cycles of {start} to {end}; cold state kept as {cold}")


if __name__ == "__main__":
    main()
