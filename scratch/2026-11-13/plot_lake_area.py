#!/usr/bin/env python3
"""Wolverine's proglacial lake in the imagery (acquire_lake_area.py CSVs): open water on clear June-September scenes
from October 2004, with the share of the box under snow or ice, and on ice-free Sentinel-2 scenes against the day's
discharge, with a power law fitted to the scenes the water test passes.

    ./plot_lake_area.py LAKE_DIR OUT.pdf      LAKE_DIR data/domain_Wolverine/observations/lake_area
"""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

WORLDVIEW = ("2025-09-29", 0.021)   # the 1 m image of Figure fig:proglacial


def scenes(lake_dir, name):
    x = pd.read_csv(os.path.join(lake_dir, f"wolverine_lake_{name}.csv"), parse_dates=["date"])
    x = x[(x.bad < 0.05) & x.date.dt.month.isin([6, 7, 8, 9])]
    return x.groupby("date").agg(water=("water_km2", "median"), snow=("snow", "median"), q=("q_cms", "first"))


def main():
    lake_dir, out = sys.argv[1:3]
    ls, s2 = scenes(lake_dir, "landsat"), scenes(lake_dir, "sentinel2")
    fig, (a, b) = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})
    a.bar(ls.index, ls.snow * 0.06, width=12, color="0.75", label="snow or ice share of box (Landsat, $\\times$0.06)")
    a.plot(ls.index, ls.water, "o", ms=4, color="#1b6ca8", label="Landsat 5/7/8, 30 m")
    a.plot(s2.index, s2.water, "s", ms=3.5, color="#e07b39", label="Sentinel-2, 10 m")
    a.axhline(WORLDVIEW[1], ls=":", color="k", lw=1)
    a.text(pd.Timestamp("2004-12-01"), WORLDVIEW[1] + 0.001, "WorldView-2, 29 Sep 2025", fontsize=7)
    a.set_xlim(pd.Timestamp("2004-10-01"), pd.Timestamp("2026-10-01")); a.set_ylim(0, 0.08)
    a.set_ylabel("open water (km$^2$)"); a.legend(fontsize=7, loc="upper left", frameon=False)
    a.set_title("(a) June–September clear scenes, from October 2004", fontsize=10)
    free = s2[(s2.snow < 0.05) & s2.q.notna() & (s2.q > 0)]
    ok, turbid = free[free.water > 0.005], free[free.water <= 0.005]
    k, p = np.polyfit(np.log(ok.q), np.log(ok.water), 1)
    sc = b.scatter(ok.q, ok.water, c=ok.index.year, cmap="viridis", s=14)
    b.plot(turbid.q, turbid.water, "x", color="r", label="turbid, not counted")
    qq = np.linspace(ok.q.min(), ok.q.max(), 50)
    b.plot(qq, np.exp(p) * qq ** k, "k-", lw=1, label=f"A = {np.exp(p):.3f} Q$^{{{k:.2f}}}$")
    b.set_xlabel("daily mean discharge at USGS 15236900 (m$^3$ s$^{-1}$)"); b.set_ylim(0, 0.08)
    b.set_ylabel("open water (km$^2$)"); b.legend(fontsize=7, frameon=False)
    b.set_title("(b) Sentinel-2, ice-free box, against flow", fontsize=10)
    fig.colorbar(sc, ax=b, label="year")
    for ax in (a, b):
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(out); print("wrote", out)


if __name__ == "__main__":
    main()
