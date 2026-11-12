#!/usr/bin/env python3
"""True-colour Sentinel-2 crops of a box with the pixels a water test passes, for checking the test by eye.

    ./fan_water_look.py OUT.png DATE [DATE ...]      Gulkana terminus-to-gauge box, two tests side by side
"""
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from acquire_lake_area import SOURCES, read_box, search  # noqa: E402

BOX = (-145.4731, 63.2381, -145.4210, 63.2609)
TESTS = [(0.3, 0.6, 0.25), (0.1, 0.3, 0.3)]


def main():
    out, dates = sys.argv[1], sys.argv[2:]
    src = SOURCES["sentinel2"]
    fig, axes = plt.subplots(len(dates), 3, figsize=(15, 4.2 * len(dates)), squeeze=False)
    for row, day in zip(axes, dates):
        item = [i for i in search(src, BOX, day, day, 70)][0]
        a, h = item["assets"], bool(item["properties"].get("earthsearch:boa_offset_applied"))
        G, fill = read_box(a["green"], BOX, None, harmonized=h)
        R, _ = read_box(a["red"], BOX, None, G.shape, h)
        B, _ = read_box(a["blue"], BOX, None, G.shape, h)
        N, _ = read_box(a["nir"], BOX, None, G.shape, h)
        W, _ = read_box(a["swir16"], BOX, None, G.shape, h)
        rgb = np.clip(np.dstack([R, G, B]) / 0.3, 0, 1)
        row[0].imshow(rgb); row[0].set_title(f"{day} true colour", fontsize=9)
        for ax, (nd, mn, bl) in zip(row[1:], TESTS):
            with np.errstate(divide="ignore", invalid="ignore"):
                w = ((G - N) / (G + N) > nd) & ((G - W) / (G + W) > mn) & (B < bl) & ~fill
            ax.imshow(rgb); ax.imshow(np.ma.masked_where(~w, w), cmap="autumn", alpha=0.8)
            ax.set_title(f"NDWI>{nd} MNDWI>{mn} blue<{bl}: {w.sum() * 100 / 1e6:.3f} km2", fontsize=9)
        for ax in row:
            ax.set_xticks([]); ax.set_yticks([])
    fig.tight_layout(); fig.savefig(out, dpi=110)


if __name__ == "__main__":
    main()
