"""Layer state of HRU 1 on 30 Sep 2005 vs 30 Sep 2006, per domain, snow/soil-or-debris/below labelled; usage: compare_drift.py"""
import os
import numpy as np, xarray as xr
H = os.path.dirname(os.path.abspath(__file__))
for name in ("wolverine", "gulkana"):
    d = xr.open_dataset(f"{H}/{name}/output/{name}_day.nc"); ts = xr.open_dataset(f"{H}/{name}/output/{name}_timestep.nc")
    nsoil = xr.open_dataset(f"{H}/{name}/summa_inputs/coldState.nc").nSoil.values[0, 0]
    print(name)
    for j in range(d.sizes["dom"]):
        if int(d.domType.values[0, j]) < 0: continue
        rows = {}
        for t in ("2005-09-30", "2006-09-30"):
            s = d.sel(time=t, method="nearest").isel(hru=0, dom=j)
            z = s.mLayerDepth.values; k = np.where(z > 0)[0]; ns = int(ts.nSnow.sel(time=s.time.values, method="nearest").isel(hru=0, dom=j).item())
            lab = ["snow"] * ns + ["soil" if j == 0 else "debris"] * int(nsoil[j]) + ["below"] * (len(k) - ns - int(nsoil[j]))
            rows[t] = (s.scalarSWE.item(), s.scalarGlceWE.item(), [(lab[i], z[i], s.mLayerTemp.values[i] - 273.15, s.mLayerVolFracIce.values[i], s.mLayerVolFracLiq.values[i]) for i in k])
        print(f"  dom {j+1} (type {int(d.domType.values[0, j])})")
        for t, (swe, gwe, L) in rows.items():
            print(f"    {t}: SWE {swe:6.1f}, GlceWE {gwe:8.1f} kg/m2; " + "  ".join(f"{l[0][0]}{l[1]:.3f}:{l[2]:+.2f}C/{l[3]:.2f}i/{l[4]:.2f}w" for l in L if l[0] != "below"))
        a = [l for l in rows["2005-09-30"][2] if l[0] == "below"]; b = [l for l in rows["2006-09-30"][2] if l[0] == "below"]
        if a: print("    below, dT 05->06 (K): " + " ".join(f"{p[1]:.2f}m {q[2]-p[2]:+.2f}" for p, q in zip(a, b)))
