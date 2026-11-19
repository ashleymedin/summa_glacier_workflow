#!/usr/bin/env python3
"""Glacier air-temperature decoupling factor k of Shaw et al. (2025, Nature Climate Change, doi:10.1038/s41558-025-02449-0),
the slope of near-surface on-glacier air temperature on ambient air temperature in summer, looked up by RGI 6 id from their
historical estimates (Zenodo doi:10.5281/zenodo.14044846, HISTORICAL_DECOUPLING_ESTIMATES_DATABASE.mat in
data/external/Shaw25CoolingFactor). It is used as SUMMA's glacierTempReduction.

The database covers every RGI 6 region but Greenland's periphery (05) and the Antarctic (19). A glacier missing from it can
be given k from Shaw's clean-ice regression on its own predictors (summer ERA5-Land air temperature TA in deg C and specific
humidity Q in kg/kg at the glacier's mean elevation, ERA5-Land wind FF in m/s, flowpath length LEN and mean elevation ELE in m);
refitted to the database's clean-ice glaciers (debris fraction under 0.1) it reproduces their k with R2 0.98:
    k = 0.987 - 0.00765 TA - 35.7 Q + 0.0194 FF - 5e-6 LEN - 1.3e-5 ELE

    shaw_cooling.py RGI60-01.00570 RGI60-01.09162
"""
import os
import sys

import numpy as np

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "external", "Shaw25CoolingFactor",
                        "HISTORICAL_DECOUPLING_ESTIMATES_DATABASE.mat")


def shaw_k(rgi_id, path=DATABASE):
    """Shaw et al.'s k of one RGI 6 glacier (RGI60-rr.nnnnn)."""
    import h5py
    with h5py.File(path) as f:
        g = f["HISTORICAL_K"]
        refs = np.ravel(g["RGI_ID"][()])
        for i, r in enumerate(refs):
            if "".join(chr(c) for c in np.ravel(f[r][()])) == rgi_id:
                return float(np.ravel(g["K"][()])[i])
    raise SystemExit(f"{rgi_id} is not in {path}; compute k from Shaw's regression (see shaw_cooling.py)")


if __name__ == "__main__":
    for rid in sys.argv[1:]:
        print(rid, round(shaw_k(rid), 3))
