#!/usr/bin/env python3
"""Repeat WY2005 on an added case (--case, default wolverine_added) for several firnViscosity values, from a given spun-up state.

Each value gets its own run directory under --work, a copy of --settings with firnViscosity appended to
localParamInfo.txt, and --cycles one-year runs, each starting from the previous run's restart. The flow model is not
triggered (the state's update day is left as it is). Compare the final restarts with the cores using firn_cores.py.

  python3 fit_firn_viscosity.py --exe <summa_firn>/bin/summa_sundials_mizuroute.exe --state <coldState.nc> \
      --settings <settings dir> --work <scratch dir> --values 6e12 1.2e13 2.4e13 1e14
"""
import argparse
import glob
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "..", "runs")


def run_value(a, value):
    work = os.path.join(a.work, f"visc_{value:.2g}")
    shutil.rmtree(work, ignore_errors=True)
    for d in ("output", "state"):
        os.makedirs(os.path.join(work, d))
    settings = os.path.join(work, "settings")
    shutil.copytree(a.settings, settings)
    with open(os.path.join(settings, "localParamInfo.txt"), "a") as f:
        f.write(f"firnViscosity             | {value:12.4e} |   1.0000e+12 |   1.0000e+14\n")
    with open(os.path.join(RUNS, a.case, "spinup", "config.toml")) as f:
        config = f.read()
    for key, path in (("work_path", "output"), ("settings_path", "settings/"), ("state_path", "state/"), ("output_path", "output/")):
        config = "\n".join(f'{key} = "{os.path.join(work, path)}"' if line.split("=")[0].strip() == key else line
                           for line in config.splitlines())
    with open(os.path.join(work, "config.toml"), "w") as f:
        f.write(config + "\n")
    current = a.state
    for k in range(1, a.cycles + 1):
        for f in glob.glob(os.path.join(work, "state", "*")) + glob.glob(os.path.join(work, "output", "*")):
            os.remove(f)
        shutil.copy(current, os.path.join(work, "state", "coldState.nc"))
        with open(os.path.join(work, "run.log"), "w") as log:
            status = subprocess.run([a.exe, "-c", "config.toml", "-r", "e"], cwd=work, stdout=log, stderr=subprocess.STDOUT).returncode
        restarts = sorted(glob.glob(os.path.join(work, "state", "*restart*.nc")))
        if status or not restarts:
            return f"{value:.2g}: cycle {k} failed, see {work}/run.log"
        current = os.path.join(work, f"cycle_{k}.nc")
        shutil.copy(restarts[-1], current)
    return f"{value:.2g}: {a.cycles} cycles, final state {current}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--exe", required=True)
    p.add_argument("--state", required=True)
    p.add_argument("--settings", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--values", type=float, nargs="+", required=True)
    p.add_argument("--cycles", type=int, default=10)
    p.add_argument("--case", default="wolverine_added")
    a = p.parse_args()
    with ThreadPoolExecutor(len(a.values)) as pool:
        for line in pool.map(lambda v: run_value(a, v), a.values):
            print(line, flush=True)


if __name__ == "__main__":
    main()
