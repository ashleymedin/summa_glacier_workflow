#!/usr/bin/env python3
"""summa develop's gulkana_wolverine calibration test case from multi-calib's: the stream HRUs (domType 6) and
streamSegId dropped from attributes, cold state, trial parameters and forcing; the topology keeps develop's reaches,
each GRU's area the sum of its remaining HRUs. Develop's text settings are left as they are.

    strip_stream.py <multi-calib test folder> <develop test folder>
"""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np


def stream_hrus(folder):
    with nc4.Dataset(os.path.join(folder, "summa_inputs", "coldState.nc")) as c:
        t = np.ma.filled(c["domType"][0], -1)  # (hru, dom)
    return np.any(t == 6, axis=1)


def copy_without(src, dst, drop, skip_vars=("streamSegId",)):
    """src to dst with the hru positions in drop removed along every hru axis."""
    keep = np.where(~drop)[0]
    with nc4.Dataset(src) as s, nc4.Dataset(dst + ".tmp", "w", format=s.data_model) as d:
        d.setncatts({k: s.getncattr(k) for k in s.ncattrs()})
        for name, dim in s.dimensions.items():
            size = len(keep) if name == "hru" else len(dim)
            d.createDimension(name, None if dim.isunlimited() else size)
        for name, v in s.variables.items():
            if name in skip_vars:
                continue
            fill = v.getncattr("_FillValue") if "_FillValue" in v.ncattrs() else None
            out = d.createVariable(name, v.datatype, v.dimensions, fill_value=fill)
            out.setncatts({k: v.getncattr(k) for k in v.ncattrs() if k != "_FillValue"})
            v.set_auto_maskandscale(False)
            out.set_auto_maskandscale(False)
            data = v[:]
            if "hru" in v.dimensions:
                data = np.take(data, keep, axis=v.dimensions.index("hru"))
            out[:] = data
    os.replace(dst + ".tmp", dst)


def main():
    mc, dev = (os.path.abspath(p) for p in sys.argv[1:3])
    drop = stream_hrus(mc)
    print(f"dropping HRU positions {list(np.where(drop)[0])}")
    for f in ("attributes.nc", "coldState.nc", "trialParams.nc"):
        copy_without(os.path.join(mc, "summa_inputs", f), os.path.join(dev, "summa_inputs", f), drop)
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(mc, "forcing", "*.nc")))
    for n in names:
        copy_without(os.path.join(mc, "forcing", n), os.path.join(dev, "forcing", n), drop)
    with nc4.Dataset(os.path.join(dev, "summa_inputs", "attributes.nc")) as a:
        area = np.asarray(a["HRUarea"][:], float)
        gru = np.asarray(a["hru2gruId"][:])
    with nc4.Dataset(os.path.join(dev, "topology.nc"), "a") as t:
        t["area"][:] = [area[gru == g].sum() for g in np.asarray(t["hruId"][:])]
        print("topology areas (km2):", np.round(t["area"][:] / 1e6, 2))
    print(f"{len(names)} forcing files")


if __name__ == "__main__":
    main()
