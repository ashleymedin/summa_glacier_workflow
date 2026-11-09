#!/usr/bin/env python3
"""Fill the \\tbd cells of glacier.tex's parameter table with each case's balanced calibrated trial, and the f_A row.

The columns are corrected forcing (the added-data setup) Wolverine and Gulkana, then ERA5 (the general setup) Wolverine
and Gulkana. The balanced trial is the front member nearest the ideal point, each objective scaled by its range on the
front. A parameter a case does not search is left as --; on the corrected forcing the ERA5-only rows have no cell.

    ./fill_param_table.py <glacier.tex> [--fa wolverine_added=0.40 ...] [--dry]
"""
import argparse
import os
import re

import netCDF4 as nc4
import numpy as np

RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "runs"))
COLUMNS = ["wolverine_added", "gulkana_added", "wolverine_general", "gulkana_general"]


def sci(x, digits=2):
    m, e = f"{x:.{digits - 1}e}".split("e")
    return f"${m}\\times10^{{{int(e)}}}$"


def fixed(form):
    return lambda x: (form % x).replace("-", "$-$")


F2, F3, F1, F0 = fixed("%.2f"), fixed("%.3f"), fixed("%.1f"), fixed("%.0f")
HOURS = lambda x: f"{x / 3600:.0f}"

# a row of the table, by the start of its line, and the parameters in its cells with their formats
ROWS = [
    ("$f_\\text{wind}^\\text{can}$ &", [("windReductionParam", F2)]),
    ("$\\rho_\\text{snow}^\\text{new,min}$ &", [("newSnowDenMin", F0)]),
    ("$\\alpha_\\text{max}$ &", [("albedoMax", F2)]),
    ("$\\tau_\\alpha$ &", [("albedoDecayRate", sci)]),
    ("$F_\\text{cap}$ &", [("Fcapil", F3)]),
    ("$k_\\text{sat}^\\text{snow}$ &", [("k_snow", F3)]),
    ("$\\xi_\\text{mw}$ &", [("mw_exp", F1)]),
    ("$f_\\text{sand}$ & sand fraction, which sets the conductivity of the solids, 2.9", [("frac_sand@upland", F2)]),
    ("$k_\\text{sat}^\\text{soil}$, $k_\\text{sat}^\\text{mac}$ &", [("k_soil@upland", sci), ("k_macropore@upland", sci)]),
    ("$\\Theta_\\text{s}$ & porosity & 0.35", [("theta_sat@upland", F2)]),
    ("$\\Theta_\\text{r}$, $\\Theta_\\text{wp}$", [("theta_res@upland", F3), ("critSoilWilting@upland", F3),
                                                   ("critSoilTranspire@upland", F3), ("fieldCapacity@upland", F3)]),
    ("$\\nG$ & van Genuchten", [("vGn_n@upland", F2)]),
    ("$f_\\text{sand}$ & sand fraction, which sets the conductivity of the solids & 0", [("frac_sand@glacDbr", F2)]),
    ("$\\Theta_\\text{s}$ & porosity & 0.2", [("theta_sat@glacDbr", F2)]),
    ("$C$ & englacial", [("debrisConc", F2)]),
    ("$k_\\text{base}$ &", [("aquiferBaseflowRate", sci)]),
    ("$n_\\text{base}$ &", [("aquiferBaseflowExp", F1)]),
    ("$f_\\text{surf}$ &", [("qSurfScale", F0)]),
    ("$\\tau$ & scale", [("routingGammaScale", sci)]),
    ("$b$ & shape", [("routingGammaShape", F2)]),
    ("$\\tau_\\text{fast}$", [("glacStor_kIce", HOURS), ("glacStor_kSnow", HOURS), ("glacStor_kFirn", HOURS)]),
    ("SCF &", [("frozenPrecipMultip", F2)]),
    ("$T_\\text{crit}$ &", [("tempCritRain", F2)]),
    ("$T_\\text{rng}$ &", [("tempRangeTimestep", F1)]),
    ("$\\Delta T$ &", [("glacierTempReduction", F2)]),
    ("$f_\\text{wind}$ & wind speed", [("glacierWindFactor", F2)]),
]


def balanced(case):
    """The balanced front member's searched values, or None if the calibration has not written its front."""
    path = os.path.join(RUNS, case, "calibration", "output", f"{case}_calibration.nc")
    if not os.path.exists(path):
        return None
    with nc4.Dataset(path) as d:
        front = np.flatnonzero(np.asarray(d["pareto_front"][:]) == 1)
        if front.size == 0:
            return None
        obj = np.ma.filled(d["objective"][:].astype(float), np.nan)[front]
        span = lambda x: (x.max() - x.min()) or 1.0
        kge, mb = obj[:, 0], obj[:, 1]
        i = int(front[np.argmin(np.hypot((kge.max() - kge) / span(kge), (mb - mb.min()) / span(mb)))])
        return {v.name: float(v[i]) for v in d.variables.values() if "sampled" in v.ncattrs() and v.sampled == 1}, i + 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tex")
    p.add_argument("--fa", nargs="*", default=[], help="case=value of glen_factor.py")
    p.add_argument("--dry", action="store_true")
    a = p.parse_args()
    trials = {c: balanced(c) for c in COLUMNS}
    for c, t in trials.items():
        print(f"{c}: balanced trial {t[1] if t else 'not ready'}")
    lines = open(a.tex).read().split("\n")
    for start, cells in ROWS:
        k = [j for j, l in enumerate(lines) if l.lstrip().startswith(start)]
        if len(k) != 1:
            raise SystemExit(f"row {start!r} matches {len(k)} lines")
        line = lines[k[0]]
        vals = []
        for c in COLUMNS:
            t = trials[c]
            if not t:
                vals.append("\\tbd")
                continue
            got = [f(t[0][n]) for n, f in cells if n in t[0]]
            vals.append(", ".join(got) if len(got) == len(cells) else "--")
        if "\\tbd & \\tbd & \\tbd & \\tbd" in line:
            line = line.replace("\\tbd & \\tbd & \\tbd & \\tbd", " & ".join(vals), 1)
        elif "& & \\tbd & \\tbd" in line:  # ERA5-only rows
            line = line.replace("& & \\tbd & \\tbd", "& & " + " & ".join(vals[2:]), 1)
        else:
            print(f"  no \\tbd cells left in {start!r}")
        lines[k[0]] = line
        print(f"  {start[:40]:40s} -> {' | '.join(vals)}")
    fa = dict(kv.split("=") for kv in a.fa)
    k = [j for j, l in enumerate(lines) if l.lstrip().startswith("$f_A$ &")]
    if fa and len(k) == 1:
        vals = [fa.get(c, "\\tbd") for c in COLUMNS]
        lines[k[0]] = lines[k[0]].replace("\\tbd & \\tbd & \\tbd & \\tbd", " & ".join(vals), 1)
        print(f"  f_A -> {' | '.join(vals)}")
    if not a.dry:
        open(a.tex, "w").write("\n".join(lines))
        print(f"wrote {a.tex}")


if __name__ == "__main__":
    main()
