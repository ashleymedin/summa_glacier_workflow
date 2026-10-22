"""ITS_LIVE against the melt-out-bed runs at f_A 0.4: implied f_A = 0.4 x median observed / median model speed (2026-10-21/itslive_compare.py's method)."""
import sys
import numpy as np
sys.path.insert(0, '/Users/amedin/Research/SummaSundials/summa_glacier_workflow/scratch/2026-10-21')
from itslive_compare import WF, CASES, MAXERR, MINV, MINH, model

for name in CASES:
    cap = CASES[name][2]
    o = np.load(f'{WF}/data/domain_{cap}/observations/storage/velocity/itslive_annual.npz')
    for label in ('usgsmb3_A0.4', 'meltout_usgsmb_A0.4'):
        run = model(name, label)
        for years in (range(2009, 2012), range(2013, 2021)):
            a = []
            for y in years:
                i = list(o['years']).index(y)
                v, e = o['v'][i], o['v_error'][i]
                u, H, _ = run[y]
                ok = (H > MINH) & np.isfinite(v) & (e < MAXERR) & (v > MINV)
                a.append(np.c_[v[ok], u[ok]])
            a = np.vstack(a)
            print(f'{name:9s} {label:20s} {min(years)}-{max(years)}: n {len(a):5d} ITS_LIVE {np.median(a[:, 0]):5.1f} model {np.median(a[:, 1]):5.1f} implied f_A {0.4 * np.median(a[:, 0]) / np.median(a[:, 1]):.2f}')
