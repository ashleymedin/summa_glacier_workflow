"""Median ice thickness by year on the cells each glacier's last survey loses (clean and debris), per run label."""
import sys, glob
sys.argv = sys.argv[:1] + ['x']
exec(open('lost_cells.py').read().split("label = ")[0])
for label in ('flow_A1', 'flow_A0.25'):
  for name, case, trial, glacier, y0, y1 in (('gulkana', 'gulkana_corrected', 384, 'Gulkana Glacier', 2007, 2021),
                                             ('wolverine', 'wolverine_corrected', 469, 'Wolverine Glacier', 2006, 2020)):
    c = load_config(f'{WF}/domains/{name}.yaml')
    run = f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_{label}'
    with nc4.Dataset(run + '_settings/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float)
        ids = np.asarray(d['gridId'][:, 0]).astype(int); nx = np.asarray(d['nx'][:, 0]).astype(int); ny = np.asarray(d['ny'][:, 0]).astype(int)
    g = int(np.argmax(nx * ny))
    with nc4.Dataset(run + '_settings/coldState.nc') as d:
        s0 = np.asarray(d['surface_elev'][:, :, g, 0], float)[:ny[g], :nx[g]]; d0 = np.asarray(d['debris_thick'][:, :, g, 0], float)[:ny[g], :nx[g]]
    S, D, years = yearly(sorted(glob.glob(f'{run}/output/*sample*_annual.nc')))
    b = bed[:ny[g], :nx[g], g]
    tr, crs = grid_transforms(c['project_dir'], c['domain'], c['utm_epsg'])
    gl = u[u.Glacier == glacier].to_crs(crs)
    mask = lambda y: rasterize(gl[gl.Year == y].geometry, out_shape=(ny[g], nx[g]), transform=tr[int(ids[g])]).astype(bool)
    H0 = np.maximum(s0 - b, 0); lost = mask(y0) & ~mask(y1) & (H0 > 0.1); keep = mask(y1) & (H0 > 0.1)
    H = np.maximum(S[:, :ny[g], :nx[g], g] - b, 0)
    for lab, sel in (('clean', lost & (d0 < 0.02)), ('debris', lost & (d0 >= 0.02)), ('kept', keep)):
        print(f'{name:9s} {label:10s} {lab:6s}', ' '.join(f'{v:4.0f}' for v in [np.median(H0[sel])] + [np.median(h[sel]) for h in H]))
  print('years', years)
