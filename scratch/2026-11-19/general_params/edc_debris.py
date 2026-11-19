#!/usr/bin/env python3
"""Englacial debris content (% by volume, literature compiled by McCarthy et al., plus Kennicott) against each glacier's
debris-covered fraction from Shaw et al. (2025)'s database: the largest glacier (by flowpath length) within 8 km of the
coordinates given.

    edc_debris.py
"""
import os

import h5py
import numpy as np

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
# name: (lat, lon, EDC % by volume low, high, how)
EDC = {"Kennicott": (61.55, -142.95, 0.017, 0.017, "inverted from debris thickness and velocity"),
       "Khumbu": (27.96, 86.83, 0.1, 0.7, "ice cliffs, active ice"),
       "Tasman": (-43.55, 170.25, 0.0095, 0.0095, "samples"),
       "Djankuat": (43.20, 42.76, 0.041, 0.041, "samples"),
       "Rakhiot": (35.33, 74.62, 0.079, 0.079, "samples"),
       "Kviarjokull": (63.97, -16.55, 0.19, 0.19, "samples"),
       "Muir": (58.95, -136.10, 0.62, 0.62, "tidewater, diffuse facies"),
       "Margerie": (58.95, -137.15, 0.3, 0.3, "tidewater, diffuse facies"),
       "Grand Pacific": (59.05, -136.95, 0.093, 0.093, "tidewater, diffuse facies")}
f = h5py.File(f"{WF}/data/external/Shaw25CoolingFactor/HISTORICAL_DECOUPLING_ESTIMATES_DATABASE.mat")
g = f["HISTORICAL_K"]
lat, lon, deb, length = (np.ravel(g[c][()]) for c in ("LAT", "LON", "DEB", "LEN"))
ids = np.ravel(g["RGI_ID"][()])
rows = []
for name, (y, x, lo, hi, how) in EDC.items():
    d = 6371 * np.hypot(np.radians(lat - y), np.radians(lon - x) * np.cos(np.radians(y)))
    near = np.where(d < 8)[0]
    i = near[np.argmax(length[near])] if len(near) else None
    rid = "".join(chr(c) for c in np.ravel(f[ids[i]][()])) if i is not None else "-"
    rows.append((name, rid, deb[i] if i is not None else np.nan, length[i] / 1e3 if i is not None else np.nan, np.sqrt(lo * hi), how))
    print(f"{name:14s} {rid:16s} debris {deb[i]:.2f}  length {length[i] / 1e3:5.1f} km  EDC {lo}-{hi} %  ({how})" if i is not None else f"{name}: none")
r = np.array([(x[2], x[4]) for x in rows if np.isfinite(x[2])])
keep = r[:, 0] > 0
b, a = np.polyfit(r[keep, 0], np.log10(r[keep, 1]), 1)
cor = np.corrcoef(r[keep, 0], np.log10(r[keep, 1]))[0, 1]
print(f"log10(EDC %) = {a:.2f} + {b:.2f} x debris fraction, r = {cor:.2f}, n = {keep.sum()}")
nt = np.array([x[5].startswith("tidewater") is False for x in rows if np.isfinite(x[2])]) & keep
b, a = np.polyfit(r[nt, 0], np.log10(r[nt, 1]), 1)
print(f"  without the tidewater glaciers: log10(EDC %) = {a:.2f} + {b:.2f} x debris fraction, r = {np.corrcoef(r[nt, 0], np.log10(r[nt, 1]))[0, 1]:.2f}, n = {nt.sum()}")
