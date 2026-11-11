#!/usr/bin/env python3
"""Drop forcingElev from the general cases' attributes.nc, which summa 8cd0949a no longer reads (an unknown attribute is fatal).

    python scratch/2026-11-11/drop_forcing_elev.py
"""
import os
import shutil

import netCDF4 as nc4

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs")

for case in ("wolverine_general", "gulkana_general"):
    path = os.path.join(RUNS, case, "summa_inputs", "attributes.nc")
    tmp = path + ".tmp"
    with nc4.Dataset(path) as src, nc4.Dataset(tmp, "w", format=src.data_model) as dst:
        dst.setncatts({k: src.getncattr(k) for k in src.ncattrs()})
        for name, dim in src.dimensions.items():
            dst.createDimension(name, None if dim.isunlimited() else len(dim))
        for name, v in src.variables.items():
            if name == "forcingElev":
                continue
            fill = v.getncattr("_FillValue") if "_FillValue" in v.ncattrs() else None
            w = dst.createVariable(name, v.datatype, v.dimensions, fill_value=fill)
            w.setncatts({k: v.getncattr(k) for k in v.ncattrs() if k != "_FillValue"})
            w[:] = v[:]
    shutil.move(tmp, path)
    print(f"{case}: forcingElev dropped")
