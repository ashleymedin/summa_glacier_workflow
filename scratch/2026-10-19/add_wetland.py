#!/usr/bin/env python3
"""Add a wetland domain to one HRU of a SUMMA cold state, its column copied from a stream domain's.

    add_wetland.py <coldState in> <coldState out> --hru 0 --area 50000 --elev 420 --depth 0.3 [--temp 274.15]

The new domain takes the next index of the dom dimension. In the chosen HRU it holds the stream domain's
lake and soil layers, with the lake layers resized to the given liquid depth (split 1:2 top to bottom) and
the whole column at --temp; the other HRUs get an empty slot. check_icond gives the upland what the
wetland takes.
"""
import argparse
import numpy as np
from netCDF4 import Dataset

WETLAND, STREAM = 5, 6
p = argparse.ArgumentParser()
p.add_argument('src'); p.add_argument('dst')
p.add_argument('--hru', type=int, default=0, help='0-based index of the HRU that gets the wetland')
p.add_argument('--area', type=float, required=True, help='wetland area (m2)')
p.add_argument('--elev', type=float, required=True, help='wetland elevation (m)')
p.add_argument('--depth', type=float, default=0.3, help='starting liquid depth (m)')
p.add_argument('--temp', type=float, default=274.15, help='starting temperature of the column (K)')
a = p.parse_args()

with Dataset(a.src) as s:
    dt = np.ma.filled(s['domType'][:], 0)
    if dt.ndim == 3: dt = dt[0]                                 # (hru, dom); a cold state has a leading scalarv
    restart = 'mLayerEnthalpy' in s.variables                   # a restart keeps the stream column's state as it is
    hs, ds = [int(x[0]) for x in np.where(dt == STREAM)]       # template: the stream domain
    nDom = len(s.dimensions['dom'])
    with Dataset(a.dst, 'w', format=s.data_model) as d:
        d.setncatts({k: s.getncattr(k) for k in s.ncattrs()})
        for name, dim in s.dimensions.items():
            d.createDimension(name, None if dim.isunlimited() else (nDom + 1 if name == 'dom' else len(dim)))
        for name, v in s.variables.items():
            fill = v.getncattr('_FillValue') if '_FillValue' in v.ncattrs() else None
            o = d.createVariable(name, v.dtype, v.dimensions, fill_value=fill)
            o.setncatts({k: v.getncattr(k) for k in v.ncattrs() if k != '_FillValue'})
            x = np.ma.filled(v[:], fill if fill is not None else 0)
            if 'dom' not in v.dimensions:
                o[:] = x; continue
            ax = v.dimensions.index('dom')
            if 'hru' not in v.dimensions:                              # the dom coordinate: one more index
                o[:] = np.concatenate([x, [np.max(x) + 1]]) if x.ndim == 1 else np.concatenate([x, np.take(x, [-1], axis=ax)], axis=ax); continue
            hx = v.dimensions.index('hru')
            new = np.take(x, [ds], axis=ax) * 0                    # an empty slot for every HRU
            if name == 'dt_init':
                new = np.take(x, [ds], axis=ax)
            y = np.concatenate([x, new], axis=ax)
            # the chosen HRU: the stream's column
            idx_new = [slice(None)] * y.ndim; idx_new[ax] = nDom; idx_new[hx] = a.hru
            idx_tpl = [slice(None)] * y.ndim; idx_tpl[ax] = ds;   idx_tpl[hx] = hs
            y[tuple(idx_new)] = y[tuple(idx_tpl)]
            o[:] = y
        def setv(name, val, layer=None):
            v = d[name]; ax = v.dimensions.index('dom'); hx = v.dimensions.index('hru')
            y = v[:]; idx = [slice(None)] * y.ndim; idx[ax] = nDom; idx[hx] = a.hru
            if layer is not None: idx[0] = layer
            y[tuple(idx)] = val; v[:] = y
        if restart:
            v = d['domType']; y = v[:]; y[a.hru, nDom] = WETLAND; v[:] = y
        else:
            setv('domType', WETLAND)
        setv('DOMarea', a.area); setv('DOMelev', a.elev)
        setv('DOMtan_slope', 0.01); setv('DOMcontourLength', np.sqrt(a.area)); setv('scalarAblFrac', 0.0)
        for k in ('glacMass4AreaChange', 'scalarGlceWE', 'scalarSWE', 'scalarSnowDepth', 'scalarSfcMeltPond'): setv(k, 0.0)
        if restart:
            print(f'wrote {a.dst}: wetland in HRU {a.hru}, dom {nDom + 1}, {a.area:.0f} m2, the stream column state kept'); raise SystemExit
        nLake = int(np.ma.filled(d['nLake'][:], 0)[0, a.hru, nDom]); nSoil = int(np.ma.filled(d['nSoil'][:], 0)[0, a.hru, nDom])
        split = np.array([1.0, 2.0][:nLake]) if nLake <= 2 else np.ones(nLake)
        lake = a.depth * split / split.sum()
        for i in range(nLake):
            setv('mLayerDepth', lake[i], i); setv('mLayerVolFracLiq', 1.0, i); setv('mLayerVolFracIce', 0.0, i)
        for i in range(nLake + nSoil):
            setv('mLayerTemp', a.temp, i)
        h = np.ma.filled(d['iLayerHeight'][:], 0)[:, a.hru, nDom].copy()
        h[:nLake + 1] = -np.concatenate([[lake.sum()], lake.sum() - np.cumsum(lake)])
        v = d['iLayerHeight']; y = v[:]; y[:, a.hru, nDom] = h; v[:] = y
print(f'wrote {a.dst}: wetland in HRU {a.hru}, dom {nDom + 1}, {a.area:.0f} m2, {a.depth} m of water over {nSoil} soil layers')
