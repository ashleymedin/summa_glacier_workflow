#!/usr/bin/env python3
"""Bring existing case and test inputs to summa b8b51ec4, which reads neither forcingElev nor windExposure (an unknown
attribute or parameter is fatal): forcingElev dropped from the attributes.nc that have it, and windExposure replaced in
each localParamInfo.txt by glacierWindFactor at the same value (1 where windExposure was 1), limits 0.3-3.

    python scratch/2026-11-11/migrate_inputs.py
"""
import glob
import os
import shutil
import sys

import netCDF4 as nc4

WF = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, WF)
from build_cases import set_param_line  # noqa: E402


def drop_forcing_elev(path):
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


def wind_factor(params):
    exposure = None
    for line in open(params):
        if line.split("|")[0].strip() == "windExposure":
            exposure = float(line.split("|")[1])
    if exposure is None:
        return None
    lines = [l for l in open(params) if l.split("|")[0].strip() != "windExposure"]
    open(params, "w").writelines(lines)
    set_param_line(params, "glacierWindFactor", exposure, 0.3, 3.0)
    return exposure


def main():
    inputs = sorted(glob.glob(os.path.join(WF, "runs", "*", "summa_inputs")) +
                    glob.glob(os.path.join(WF, "tests", "*", "summa_inputs")))
    for d in inputs:
        done = []
        attributes = os.path.join(d, "attributes.nc")
        if os.path.exists(attributes):
            with nc4.Dataset(attributes) as a:
                has = "forcingElev" in a.variables
            if has:
                drop_forcing_elev(attributes)
                done.append("forcingElev dropped")
        params = os.path.join(d, "localParamInfo.txt")
        if os.path.exists(params):
            e = wind_factor(params)
            if e is not None:
                done.append(f"glacierWindFactor {e:g}")
        if done:
            print(f"{os.path.relpath(d, WF)}: {', '.join(done)}")


if __name__ == "__main__":
    main()
