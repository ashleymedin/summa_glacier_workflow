#!/usr/bin/env python3
"""Case and template inputs for summa's glacier factors: glacierTempReduction is the glacier air temperature above
freezing as a fraction of the forcing's, glacierWindFactor is limited to 0.3-1.5.

The cases in runs/ and tests/ take Site B's temperature factor (air_cooling_from_campaign.py) with the searched range
0.5-0.9 as limits; the domain templates take 1 (no cooling) with limits 0-1.

    python scratch/2026-11-12/migrate_glacier_factors.py
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from build_cases import air_cooling_station  # noqa: E402

site_b = air_cooling_station()
cases = sorted(glob.glob(os.path.join(ROOT, "runs", "*", "summa_inputs", "localParamInfo.txt")) +
               glob.glob(os.path.join(ROOT, "tests", "*", "summa_inputs", "localParamInfo.txt")))
templates = sorted(glob.glob(os.path.join(ROOT, "data", "domain_*", "settings", "SUMMA", "localParamInfo.txt")))
for path in cases + templates:
    out = []
    for line in open(path):
        cells = [c.strip() for c in line.split("|")]
        end = "\n" if line.endswith("\n") else ""
        if cells[0] == "glacierTempReduction":
            value, lower, upper = (site_b, 0.5, 0.9) if path in cases else (1.0, 0.0, 1.0)
            line = f"{cells[0]:<26}| {value:12.6f} | {lower:12.4f} | {upper:12.4f}{end}"
        elif cells[0] == "glacierWindFactor":
            line = f"{cells[0]:<26}| {float(cells[1]):12.6f} | {0.3:12.4f} | {1.5:12.4f}{end}"
        out.append(line)
    open(path, "w").writelines(out)
    print(os.path.relpath(path, ROOT))
