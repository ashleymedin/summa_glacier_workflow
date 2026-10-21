"""Rerun trials 384 and 469 at windExposure 0.77 with glacierTempSlope in place of glacierTempReduction (labels sample_<n>_tslope<v>)."""
import os, sys
from concurrent.futures import ThreadPoolExecutor
import netCDF4 as nc4
sys.path.insert(0, "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs")
from calibrate import HERE, config_text, pin_settings, run_driver, search_of, searched_names
from rerun_trials import OUTPUTS, GRIDS

NAME = "calibration_paper1"
jobs = []
for case, s in (("gulkana_corrected", 384), ("wolverine_corrected", 469)):
    run_dir = os.path.join(HERE, case)
    search = search_of(os.path.join(run_dir, NAME))
    with nc4.Dataset(os.path.join(run_dir, NAME, "output", f"{case}_calibration.nc")) as d:
        base = {n: float(d[n][s - 1]) for n in searched_names(search) if n in d.variables}
    for k in (0.0, 0.15, 0.26, 0.38):
        v = dict(base)
        v["windExposure"] = 0.77
        if k > 0:
            v["glacierTempReduction"] = 0.0
        jobs.append((case, run_dir, search, s, f"tslope{k}", v, k))


def rerun(job):
    case, run_dir, search, s, label, values, k = job
    work = os.path.join(run_dir, f"{NAME}_rerun", f"sample_{s}_{label}")
    pinned = work + "_settings"
    pin_settings(os.path.join(run_dir, "summa_inputs"), pinned, values)
    with open(os.path.join(pinned, "localParamInfo.txt"), "a") as f:
        f.write(f"{'glacierTempSlope':<26}| {k:12.4f} | {k:12.4f} | {k:12.4f}\n")
    with open(os.path.join(pinned, "outputControl.txt"), "a") as f:
        f.writelines(f"{v:<26}| day | mean\n" for v in OUTPUTS)
        f.writelines(f"{v:<26}| annual\n" for v in GRIDS)
    config = config_text(case, run_dir, pinned, work, "2009-01-01", "2022-12-31", "2016-01-01", "2022-12-31",
                         "dds", 1, 1, temperature=True, search=search, pinned=values) \
        .replace("write_timeseries = false", "write_timeseries = true")
    run_driver(work, config, pinned, 2)
    print(f"{case} {s} {label} glacierTempReduction={values['glacierTempReduction']:.3f} glacierTempSlope={k}: {work}/output", flush=True)


with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(rerun, jobs))
