#!/usr/bin/env python3
"""Rerun front members of a calibration with daily output, for plotting.

Each trial is rerun as calibrate.py evaluate reruns it (parameters pinned, spin-up over 2008 at the defaults,
2009-2022), but with write_timeseries (and mizuRoute's reach discharge and temperature) on, daily means of runoff, glacier and snow variables and yearly glacier surface and debris grids added to its outputControl, in
<case>/<name>_rerun/sample_<n>. --inputs reruns them on other summa_inputs than the case's, such as a rebuilt domain's.

    ./rerun_trials.py gulkana_corrected calibration 451 455 411 --jobs 3
    ./rerun_trials.py gulkana_corrected calibration_paper1 384 --set wallErosionRate=0 --label wall0
"""

import argparse
import os
from concurrent.futures import ThreadPoolExecutor

import netCDF4 as nc4

from calibrate import HERE, config_text, fit12, pin_settings, run_driver, search_of, searched_names

OUTPUTS = ["averageRoutedRunoff", "glacierRoutedRunoff", "basin__GlacierMassChange", "basin__GlacierArea",
           "basin__SurfaceRunoff", "basin__AquiferBaseflow", "scalarSWE", "scalarRainfall", "scalarSnowfall",
           "scalarGlacierMelt", "scalarAquiferStorage", "DOMarea", "DOMelev",
           "glacMass4AreaChange"]  # each domain's mass change since the last area update, which the flow model fits
GRIDS = ["surface_elev", "debris_thick"]  # glacier surface and debris maps at each year's end


def set_defaults(settings, overrides):
    """Each named parameter's default set to its value, the bounds widened to hold it."""
    for name in ("localParamInfo.txt", "basinParamInfo.txt"):
        path = os.path.join(settings, name)
        out = []
        for line in open(path):
            key = line.split("|")[0].strip() if "|" in line and not line.lstrip().startswith("!") else ""
            if key in overrides:
                v = float(overrides.pop(key))
                lo, hi = (float(x) for x in line.split("|")[2:4])
                line = f"{key:<26}| {fit12(v)} | {fit12(min(lo, v))} | {fit12(max(hi, v))}\n"
            out.append(line)
        open(path, "w").writelines(out)
    if overrides:
        raise SystemExit(f"not in the parameter files: {', '.join(overrides)}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("case")
    p.add_argument("name", help="calibration folder in <case>, e.g. pilot or calibration")
    p.add_argument("samples", type=int, nargs="+", help="sample numbers, 1-based, as the trials file counts them")
    p.add_argument("--ranks", type=int, default=2)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--set", action="append", default=[], metavar="NAME=VALUE",
                   help="override an unsearched parameter's default, e.g. wallErosionRate=0")
    p.add_argument("--label", help="appended to each folder, sample_<n>_<label>")
    p.add_argument("--inputs", help="summa_inputs folder to rerun on, default <case>/summa_inputs")
    a = p.parse_args()
    run_dir = os.path.join(HERE, a.case)
    search = search_of(os.path.join(run_dir, a.name))
    with nc4.Dataset(os.path.join(run_dir, a.name, "output", f"{a.case}_calibration.nc")) as d:
        names = [n for n in searched_names(search) if n in d.variables]
        values = {s: {n: float(d[n][s - 1]) for n in names} for s in a.samples}

    def rerun(s):
        work = os.path.join(run_dir, f"{a.name}_rerun", f"sample_{s}" + (f"_{a.label}" if a.label else ""))
        pinned = work + "_settings"
        pin_settings(os.path.abspath(a.inputs) if a.inputs else os.path.join(run_dir, "summa_inputs"), pinned, values[s])
        set_defaults(pinned, dict(kv.split("=") for kv in a.set))
        with open(os.path.join(pinned, "outputControl.txt"), "a") as f:
            f.writelines(f"{v:<26}| day | mean\n" for v in OUTPUTS)
            f.writelines(f"{v:<26}| annual\n" for v in GRIDS)
        config = config_text(a.case, run_dir, pinned, work, "2009-01-01", "2022-12-31", "2016-01-01", "2022-12-31",
                             "dds", 1, 1, temperature=True, search=search, pinned=values[s]).replace("write_timeseries = false", "write_timeseries = true") \
            .replace("write_Qreach = false", "write_Qreach = true")
        run_driver(work, config, pinned, a.ranks)
        print(f"sample {s}: {work}/output", flush=True)

    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        list(pool.map(rerun, a.samples))


if __name__ == "__main__":
    main()
