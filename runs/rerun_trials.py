#!/usr/bin/env python3
"""Rerun front members of a calibration with daily output, for plotting.

Each trial is rerun as calibrate.py evaluate reruns it (parameters pinned, spin-up over 2008 at the defaults,
2009-2022), but with write_timeseries (and mizuRoute's reach discharge and temperature) on, and daily means of runoff, glacier and snow variables added to its outputControl, in
<case>/<name>_rerun/sample_<n>.

    ./rerun_trials.py gulkana_corrected calibration 451 455 411 --jobs 3
"""

import argparse
import os
from concurrent.futures import ThreadPoolExecutor

import netCDF4 as nc4

from calibrate import HERE, PARAMS, SOIL_CHAIN, config_text, pin_settings, run_driver

OUTPUTS = ["averageRoutedRunoff", "glacierRoutedRunoff", "basin__GlacierMassChange", "basin__GlacierArea",
           "basin__SurfaceRunoff", "basin__AquiferBaseflow", "scalarSWE", "scalarRainfall", "scalarSnowfall",
           "scalarGlacierMelt", "scalarAquiferStorage", "DOMarea"]


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("case")
    p.add_argument("name", help="calibration folder in <case>, e.g. pilot or calibration")
    p.add_argument("samples", type=int, nargs="+", help="sample numbers, 1-based, as the trials file counts them")
    p.add_argument("--ranks", type=int, default=2)
    p.add_argument("--jobs", type=int, default=1)
    a = p.parse_args()
    run_dir = os.path.join(HERE, a.case)
    with nc4.Dataset(os.path.join(run_dir, a.name, "output", f"{a.case}_calibration.nc")) as d:
        names = [n for n in PARAMS + SOIL_CHAIN if n in d.variables]
        values = {s: {n: float(d[n][s - 1]) for n in names} for s in a.samples}

    def rerun(s):
        work = os.path.join(run_dir, f"{a.name}_rerun", f"sample_{s}")
        pinned = work + "_settings"
        pin_settings(os.path.join(run_dir, "summa_inputs"), pinned, values[s])
        with open(os.path.join(pinned, "outputControl.txt"), "a") as f:
            f.writelines(f"{v:<26}| day | mean\n" for v in OUTPUTS)
        config = config_text(a.case, run_dir, pinned, work, "2009-01-01", "2022-12-31", "2016-01-01", "2022-12-31",
                             "dds", 1, 1, temperature=True).replace("write_timeseries = false", "write_timeseries = true") \
            .replace("write_Qreach = false", "write_Qreach = true")
        run_driver(work, config, pinned, a.ranks)
        print(f"sample {s}: {work}/output", flush=True)

    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        list(pool.map(rerun, a.samples))


if __name__ == "__main__":
    main()
