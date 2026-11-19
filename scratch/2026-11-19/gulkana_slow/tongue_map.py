#!/usr/bin/env python3
"""Model glacier (ice + debris) in 2004 and 2021 against the 2021 imagery's ice, for rerun folders' glacier_change/maps.npz.

    tongue_map.py out.png runs/gulkana_general/calibration_rerun_1119r4/sample_440 ...
"""
import sys

import matplotlib.pyplot as plt
import numpy as np

out, dirs = sys.argv[1], sys.argv[2:]
fig, axs = plt.subplots(1, len(dirs), figsize=(6 * len(dirs), 5.5))
for ax, d in zip(np.atleast_1d(axs), dirs):
    m = np.load(f"{d}/glacier_change/maps.npz")
    g04 = m["model_ice_2004-08-14"] | m["model_debris_2004-08-14"]
    g21 = m["model_ice_2021-08-02"] | m["model_debris_2021-08-02"]
    img = np.isin(m["classes_2021-08-02"], (1, 2))
    rgb = np.ones(g04.shape + (3,))
    rgb[g04 & g21] = (0.75, 0.75, 0.75)
    rgb[g04 & ~g21] = (0.2, 0.4, 0.9)    # lost
    rgb[~g04 & g21] = (0.9, 0.2, 0.2)    # gained
    ax.imshow(rgb)
    ax.contour(img, [0.5], colors="k", linewidths=0.6)
    ax.set_title(f"{d.split('runs/')[-1]}\nblue lost, red gained 2004-21; black 2021 imagery ice+debris", fontsize=8)
    ax.set_xticks([]); ax.set_yticks([])
    print(d, "lost", (g04 & ~g21).sum() * float(m["dx"]) ** 2 / 1e6, "gained", (~g04 & g21).sum() * float(m["dx"]) ** 2 / 1e6)
fig.tight_layout()
fig.savefig(out, dpi=110)
