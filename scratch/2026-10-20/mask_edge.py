"""Ice cells next to a cell outside glacierMask (where ice leaks out), at the start and the end of a run."""
import glob, sys, numpy as np, netCDF4 as nc4
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
for case, trial in (('gulkana_corrected', 384), ('wolverine_corrected', 469)):
    ins = f'{WF}/runs/{case}/summa_inputs_flow'
    with nc4.Dataset(f'{ins}/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float); gm = np.asarray(d['glacierMask'][:, :, :, 0]) > 0
        nx = np.asarray(d['nx'][:, 0]).astype(int); ny = np.asarray(d['ny'][:, 0]).astype(int)
    g = int(np.argmax(nx * ny)); b = bed[:ny[g], :nx[g], g]; m = gm[:ny[g], :nx[g], g]
    with nc4.Dataset(f'{ins}/coldState.nc') as d:
        s0 = np.asarray(d['surface_elev'][:, :, g, 0], float)[:ny[g], :nx[g]]
    f = sorted(glob.glob(f'{WF}/runs/{case}/calibration_paper1_rerun/sample_{trial}_usgsmb_A1/output/*sample*_annual.nc'))[0]
    with nc4.Dataset(f) as d:
        s1 = np.asarray(d['surface_elev'][-1, :ny[g], :nx[g], g, 0], float)
    out = np.pad(~m, 1, constant_values=True)
    nb = out[:-2, 1:-1] | out[2:, 1:-1] | out[1:-1, :-2] | out[1:-1, 2:]
    for lab, s in (('start', s0), ('end', s1)):
        H = s - b; edge = m & nb & (H > 0.1)
        down = edge & ((np.pad(np.where(m, s, np.inf), 1, constant_values=np.inf)[:-2, 1:-1] > s))  # placeholder
        lower = np.zeros_like(edge)
        sp = np.pad(np.where(~m, b, np.nan), 1, constant_values=np.nan)
        for nbr in (sp[:-2, 1:-1], sp[2:, 1:-1], sp[1:-1, :-2], sp[1:-1, 2:]):
            lower |= edge & (nbr < s)
        print(f'{case} {lab}: {m.sum()} mask cells, {(H>0.1).sum()} ice; {edge.sum()} ice cells on the mask edge, '
              f'{lower.sum()} with an outside neighbour below their surface (median H {np.median(H[lower]) if lower.any() else 0:.0f} m)')
    # outward SIA flux across mask-edge faces, H at the face ~ the edge cell's, slope from the two surfaces only (lower bound on |grad S|)
    gamma = 2 * 2.4e-24 * (917 * 9.80616) ** 3 / 5; dx = 50.516; yr = 365.25 * 86400
    H = np.maximum(s1 - b, 0); q = 0.0
    sp = np.pad(np.where(~m, b, np.nan), 1, constant_values=np.nan)
    for nbr in (sp[:-2, 1:-1], sp[2:, 1:-1], sp[1:-1, :-2], sp[1:-1, 2:]):
        sl = np.where(m & (H > 0.1) & (nbr < s1), (s1 - nbr) / dx, 0.0)
        q += np.nansum(gamma * H ** 5 * sl ** 3) * dx * yr   # m3/yr: D*slope*width = gamma H^5 |gradS|^2 * slope * dx
    print(f'   leak estimate at the end: {q:.3g} m3/yr = {q/(m.sum()*dx*dx):.3f} m/yr over the mask')
