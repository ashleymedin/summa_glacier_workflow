#!/usr/bin/env python3
"""Front, trade-offs and parameter correlations of a cheap lemon_grus calibration (its _calibration.nc as the argument)."""
import sys, numpy as np, xarray as xr, pandas as pd
d = xr.open_dataset(sys.argv[1]); print(list(d.data_vars)); n = [t.decode().strip() if isinstance(t, bytes) else str(t).strip() for t in d.target_name.values]
o = pd.DataFrame(d.objective.values.reshape(-1, len(n)) if d.objective.dims[0] == "sample" else d.objective.values.T, columns=n, index=d.sample.values)
p = pd.DataFrame({v: d[v].values for v in d.data_vars if d[v].dims == ("sample",) and v not in ("birth_generation", "pareto_front") and d[v].dtype.kind == "f"}, index=o.index)
ok = np.isfinite(o).all(axis=1) & (o.abs() < 1e6).all(axis=1); print("finite", ok.sum(), "of", len(o))
f = o[(d.pareto_front.values == 1) & ok]; print("front values", np.unique(d.pareto_front.values)); print(f.sort_values(n[0]).round(3).to_string())
print(o[ok].corr("spearman").round(2).to_string()); print(o[ok].describe().round(2).to_string())
c = pd.concat([o[ok], p[ok]], axis=1).corr("spearman").loc[p.columns, n]; print(c[c.abs().max(axis=1) > .35].round(2).to_string())
v = [x for x in p if any(k in x for k in ("frozen", "albedo", "tempCrit", "k_", "lapse"))]; print(p.loc[f.index, v].round(3).T.to_string())
