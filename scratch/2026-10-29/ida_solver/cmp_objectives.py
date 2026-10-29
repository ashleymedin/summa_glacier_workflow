"""Compare calibration objectives of two tolall runs sample by sample where the sampled parameters match; usage: cmp_objectives.py <tagA> <tagB>"""
import sys, glob, numpy as np, xarray as xr
D = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/scratch/2026-10-28/ida_solver"
def load(tag):
    return xr.open_dataset(glob.glob(f"{D}/tolall_{tag}/output/*calibration*.nc")[0])
a, b = load(sys.argv[1]), load(sys.argv[2])
pars = [v for v in a.data_vars if a[v].dims == ("sample",) and v not in ("worker_rank", "trial_failed")]
same = np.all([np.isclose(a[p].values, b[p].values, rtol=1e-12) for p in pars], axis=0)
names = [s.decode().strip() for s in a.target_name.values]
oa, ob = a.objective.values, b.objective.values
print(f"{sys.argv[1]} vs {sys.argv[2]}: {same.sum()} of {same.size} samples with identical parameters; failed {a.trial_failed.values.sum()} / {b.trial_failed.values.sum()}")
for k, n in enumerate(names):
    d = np.abs(oa[same, k] - ob[same, k])
    print(f"  {n}: max |diff| {d.max():.3g}, median {np.median(d):.3g}, range A {oa[same,k].min():.4g}..{oa[same,k].max():.4g}")
print("  best A %.6g  best B %.6g" % (np.nanmax(oa[:, 0]) if 'kge' in names[0] else np.nanmin(oa[:, 0]), np.nanmax(ob[:, 0]) if 'kge' in names[0] else np.nanmin(ob[:, 0])))
