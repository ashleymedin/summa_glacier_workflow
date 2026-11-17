#!/usr/bin/env python3
"""KGE parts (r, variability ratio, bias ratio) and seasonal mass-balance bias of a rerun's aligned pairs, per period.

    ./kge_parts.py <rerun sample_<n>_aligned folder> [...]
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from plot_setup_runs import aligned  # noqa: E402

for path in sys.argv[1:]:
    ev = aligned(os.path.join(path, "output"))
    print(f"== {path}")
    for t, df in ev.items():
        if t.startswith("discharge") or t == "streamflow":
            o, s = df.obs, df.sim
            r = o.corr(s)
            print(f"  {t}: n {len(df)}  r {r:.3f}  alpha {s.std() / o.std():.3f}  beta {s.mean() / o.mean():.3f}  "
                  f"obs {o.mean():.2f}  sim {s.mean():.2f}")
        else:
            d = df.sim - df.obs
            print(f"  {t}: n {len(df)}  mean obs {df.obs.mean():.0f}  mean sim {df.sim.mean():.0f}  bias {d.mean():.0f}  "
                  f"rmse {(d ** 2).mean() ** 0.5:.0f}")
            if len(df) <= 60:
                print("   ", "  ".join(f"{i:%Y-%m}:{o:.0f}/{s:.0f}" for i, o, s in zip(df.index, df.obs, df.sim)))
