#!/usr/bin/env python3
"""Balanced-trial parameter values of the paper-1 cases for Table 4, with any within 2% of a search limit flagged.

    table4_values.py calibration_1119r4 wolverine_general:465 gulkana_general:440 wolverine_added:463 gulkana_added:436
"""
import glob
import math
import os
import re
import sys

import netCDF4 as nc
import numpy as np

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "runs")
LOGS = {"k_soil@upland", "k_macropore@upland", "aquiferBaseflowRate"}


def bounds(case):
    """Search limits of each parameter: the config's own, else localParamInfo/basinParamInfo."""
    cfg = open(os.path.join(RUNS, case, NAME, "config.toml")).read()
    block = cfg.split("[calibration.parameters]")[1].split("\n[")[0]
    out = {}
    for name, rest in re.findall(r'^"([^"]+)"\s*=\s*\{(.*)\}', block, re.M):
        lo, hi = re.search(r"lower\s*=\s*([-\d.eE+]+)", rest), re.search(r"upper\s*=\s*([-\d.eE+]+)", rest)
        out[name] = [float(lo.group(1)) if lo else None, float(hi.group(1)) if hi else None]
    for f in ("localParamInfo.txt", "basinParamInfo.txt"):
        for line in open(os.path.join(RUNS, case, "summa_inputs", f)):
            p = [x.strip() for x in line.split("|")]
            if len(p) == 4 and not line.startswith("!"):
                for name, b in out.items():
                    if name.split("@")[0] == p[0]:
                        b[0] = float(p[2].replace("d", "e")) if b[0] is None else b[0]
                        b[1] = float(p[3].replace("d", "e")) if b[1] is None else b[1]
    return out


def value(d, name, case):
    """The trial's value on the upland domain, or on the glacier debris for @glacDbr."""
    base, _, where = name.partition("@")
    v = np.ma.filled(d[base][:].astype(float), np.nan)
    if "dom" in d[base].dimensions:
        v = v[0] if where != "glacDbr" else v[1:]  # debris sits in whichever glacier domain holds it
    v = np.ravel(v)
    return float(v[~np.isnan(v)][0]) if np.isfinite(v).any() else float("nan")


NAME = sys.argv[1]
for spec in sys.argv[2:]:
    case, sample = spec.split(":")
    f = glob.glob(os.path.join(RUNS, case, NAME, "output", f"*_sample{sample}_trialParams.nc"))[0]
    print(f"== {case} {sample}")
    with nc.Dataset(f) as d:
        for name, (lo, hi) in bounds(case).items():
            v = value(d, name, case)
            if None in (lo, hi):
                flag = "  (limits not found)"
            else:
                tr = (lambda x: math.log10(x)) if name in LOGS else (lambda x: x)
                pos = (tr(v) - tr(lo)) / (tr(hi) - tr(lo))
                flag = "  AT LOWER" if pos < 0.02 else "  AT UPPER" if pos > 0.98 else ""
            print(f"  {name:28s} {v:12.5g}   [{lo:.3g}, {hi:.3g}]{flag}" if None not in (lo, hi) else f"  {name:28s} {v:12.5g}{flag}")
        fp = np.ma.filled(d["frozenPrecipMultip"][:].astype(float), np.nan)
        print(f"  frozenPrecipMultip by dom x hru: {np.round(fp, 4).tolist()}")
