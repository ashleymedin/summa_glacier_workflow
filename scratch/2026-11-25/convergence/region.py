#!/usr/bin/env python3
"""Held-out scores over the balanced region of each round's front: the N members nearest the span-scaled balance point of the
(merged) front, from the evaluation reruns. Rounds 5b and 6 are one search; rounds 8 to 10 merge seeds 42 and 43.

    region.py [N]
"""
import os
import sys

import numpy as np
import pandas as pd

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "runs")
CASES = ["wolverine_general", "gulkana_general", "wolverine_added", "gulkana_added"]
ROUNDS = {"5b": ["calibration_evaluation_1120r5b"], "r6": ["calibration_evaluation_1120r6"],
          "r8": ["calibration_evaluation_1123r8", "calibration_s43_evaluation_1123r8"],
          "r9": ["calibration_evaluation_1125r9", "calibration_s43_evaluation_1125r9"],
          "r10": ["calibration_evaluation", "calibration_s43_evaluation"]}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5

for case in CASES:
    print(f"\n{case}: balanced region of {N}; KGE and mass RMSE (mm), median [min-max]; balanced trial first")
    for r, folders in ROUNDS.items():
        df = pd.concat([pd.read_csv(os.path.join(RUNS, case, f, "evaluation.csv")).assign(src=f) for f in folders
                        if os.path.exists(os.path.join(RUNS, case, f, "evaluation.csv"))], ignore_index=True)
        df.columns = [c.replace("wgms_amce", "mass").replace("mass_balance", "mass") for c in df.columns]
        k, m = df.cal_discharge.to_numpy(), df.cal_mass.to_numpy()
        front = [i for i in range(len(k)) if not np.any((k >= k[i]) & (m <= m[i]) & ((k > k[i]) | (m < m[i])))]
        df = df.iloc[front].reset_index(drop=True)
        k, m = df.cal_discharge.to_numpy(), df.cal_mass.to_numpy()
        span = lambda x: (x.max() - x.min()) or 1.0  # noqa: E731
        df["d"] = np.hypot((k.max() - k) / span(k), (m - m.min()) / span(m))
        reg = df.sort_values("d").head(N)
        b = reg.iloc[0]
        f = lambda x, p: f"{np.median(x):{p}} [{x.min():{p}}-{x.max():{p}}]"  # noqa: E731
        print(f"  {r:3s} front {len(df):2d}  trial {int(b['sample']):3d} cal {b.cal_discharge:.3f}/{b.cal_mass:4.0f} "
              f"held {b.eval_discharge:.3f}/{b.eval_mass:4.0f} | region held KGE {f(reg.eval_discharge, '.3f')}, "
              f"RMSE {f(reg.eval_mass, '.0f')}")
