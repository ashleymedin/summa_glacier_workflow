#!/usr/bin/env python3
"""Compare a raw_data month written from NCAR (acquire_era5.py --source ncar) with the CDS one: per field mean, max |diff|, correlation."""

import sys

import numpy as np
import xarray as xr

with xr.open_dataset(sys.argv[1]) as a, xr.open_dataset(sys.argv[2]) as b:
    assert (a.time.values == b.time.values).all() and (a.latitude.values == b.latitude.values).all() and (a.longitude.values == b.longitude.values).all()
    for k in a.data_vars:
        x, y = a[k].values.ravel(), b[k].values.ravel()
        print(f"{k:9s} ncar {x.mean():11.5g} cds {y.mean():11.5g}  max|d| {np.abs(x - y).max():9.3g}  r {np.corrcoef(x, y)[0, 1]:.4f}")
