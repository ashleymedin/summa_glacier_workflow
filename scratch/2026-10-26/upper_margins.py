"""Gulkana 1650-2050 m (USGS heights): cells the model melts out by 2021 that the 2021 survey keeps, against cells both
lose. Per set: start ice, Millan's own or fill, distance in from the 2007 edge, the observed balance the run applied,
the thinning flow added, and Hugonnet's 2000-2020 dh/dt there."""
import sys, glob, os, tempfile
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
sys.path.insert(0, WF)
import numpy as np, geopandas as gpd, netCDF4 as nc4, rasterio
from rasterio.features import rasterize
from rasterio.warp import reproject, Resampling
from scipy.ndimage import distance_transform_edt
from domain_config import load_config
from glacier_cold_state import grid_transforms
from compare_glacier_change import yearly

DZ, Y0, Y1, ZLO, ZHI, RHO = -16.1, 2007, 2021, 1650, 2050, 0.9
c = load_config(f'{WF}/domains/gulkana.yaml')
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
labels = sys.argv[1:] or ['meltout_usgsmb_A0.4', 'usgsmb3_A0.4']


def on_grid(src_files, crs, shape, tr):
    """Mean of the source rasters' finite values, bilinear onto the flow grid."""
    out = np.full(shape, np.nan)
    for f in src_files:
        with rasterio.open(f) as s:
            a = np.full(shape, np.nan)
            reproject(rasterio.band(s, 1), a, src_transform=s.transform, src_crs=s.crs, dst_transform=tr, dst_crs=crs,
                      resampling=Resampling.bilinear, src_nodata=s.nodata, dst_nodata=np.nan)
            out = np.where(np.isfinite(a), a, out)
    return out


for label in labels:
    run = f'{WF}/runs/gulkana_corrected/calibration_paper1_rerun/sample_384_{label}'
    with nc4.Dataset(run + '_settings/attributes.nc') as d:
        bed = np.asarray(d['bed_elev'][:, :, :, 0], float)
        ids = np.asarray(d['gridId'][:, 0]).astype(int); nx = np.asarray(d['nx'][:, 0]).astype(int); ny = np.asarray(d['ny'][:, 0]).astype(int)
        dx = float(np.asarray(d['dx'][:]).flat[0])
    g = int(np.argmax(nx * ny)); sh = (ny[g], nx[g]); a = dx * dx / 1e6
    b = bed[:sh[0], :sh[1], g]
    with nc4.Dataset(run + '_settings/coldState.nc') as d:
        s0 = np.asarray(d['surface_elev'][:, :, g, 0], float)[:sh[0], :sh[1]]
        d0 = np.asarray(d['debris_thick'][:, :, g, 0], float)[:sh[0], :sh[1]]
    S, D, years = yearly(sorted(glob.glob(f'{run}/output/*sample*_annual.nc')))
    S = S[:, :sh[0], :sh[1], g]
    tr, crs = grid_transforms(c['project_dir'], c['domain'], c['utm_epsg']); tr = tr[int(ids[g])]
    gl = u[u.Glacier == 'Gulkana Glacier'].to_crs(crs)
    m = {y: rasterize(gl[gl.Year == y].geometry, out_shape=sh, transform=tr).astype(bool) for y in (Y0, Y1)}
    H0 = np.maximum(s0 - b, 0)
    k1 = int(np.where(years == Y1)[0][0]); H1 = np.maximum(S[k1] - b, 0)
    ice0, ice1 = H0 > 0.1, H1 > 0.1
    zu = s0 - DZ
    band = ice0 & (zu >= ZLO) & (zu < ZHI)
    # observed balance the run applied: each year's profile at the cell's own surface, clean ice
    prof = np.loadtxt(run + '_settings/glacierMassBal.txt', comments='!')
    ks = [k for k in range(len(years)) if Y0 < years[k] <= Y1]
    cum = np.zeros(sh)
    for k in ks:
        p = prof[(prof[:, 0] == years[k]) & (prof[:, 1] == 0)]
        if not len(p): continue
        cum += np.interp(S[k - 1], p[:, 2], p[:, 3]) / RHO
    dH = H1 - H0
    flow = dH - np.where(ice0, cum, 0)  # thinning not from the balance; melted-out cells floor at the bed, so a lower bound
    dist = distance_transform_edt(m[Y0]) * dx
    # Millan's own thickness on the flow grid (zero or missing = the setup's fill)
    rn = str(int(c['rgi6_region'][:2]))
    tdir = os.path.join(os.path.expanduser(c['data']['ice_thickness']), f'RGI-{rn}')
    mil = on_grid([os.path.join(tdir, f) for f in sorted(os.listdir(tdir)) if f.startswith(f'THICKNESS_RGI-{rn}.') and f.endswith('tif')], crs, sh, tr)
    hug = on_grid(sorted(glob.glob(f'{WF}/HugonnetData/01_02_rgi60_2000-01-01_2020-01-01/dhdt/N63W14[56]_*.tif')), crs, sh, tr)
    sets = {'model loses, 2021 keeps': band & ~ice1 & m[Y1],
            'both lose': band & ~ice1 & ~m[Y1],
            'model keeps, 2021 loses': band & ice1 & ~m[Y1],
            'both keep, edge 200 m': band & ice1 & m[Y1] & (dist < 200)}
    print(f'\nGulkana {label}: {Y0} ice {ZLO}-{ZHI} m {band.sum()*a:.2f} km2; dx {dx:.0f} m; years {years[ks[0]]}-{years[ks[-1]]}')
    print(f'{"set":26s} km2  H0 med  Millan own %  Millan H  dist m  balance m ice  flow m  dH m  Hugonnet m/yr  debris %')
    for n, s in sets.items():
        if not s.any(): print(f'{n:26s} 0'); continue
        own = np.isfinite(mil[s]) & (mil[s] > 0)
        f = lambda v: np.nanmedian(v[s])
        print(f'{n:26s} {s.sum()*a:4.2f} {f(H0):6.0f} {own.mean()*100:10.0f} {np.nanmedian(mil[s][own]) if own.any() else np.nan:9.0f}'
              f' {f(dist):7.0f} {f(cum):13.1f} {f(flow):7.1f} {f(dH):5.1f} {f(hug):13.2f} {(d0[s] >= 0.02).mean()*100:9.0f}')
    # where: by 100 m band and by the cell's aspect
    ov = sets['model loses, 2021 keeps']
    gy, gx = np.gradient(s0, dx); asp = (np.degrees(np.arctan2(-gx, gy)) + 360) % 360  # 0 = slope faces north (row 0 north)
    print(' band  over-lost km2  of band ice %  H0 med  balance  flow')
    for z in range(ZLO - 50, ZHI, 100):
        k = ov & (zu >= z) & (zu < z + 100); kb = band & (zu >= z) & (zu < z + 100)
        if kb.any(): print(f' {z:5d} {k.sum()*a:13.2f} {k.sum()/kb.sum()*100:13.0f} {np.median(H0[k]) if k.any() else np.nan:7.0f}'
                           f' {np.median(cum[k]) if k.any() else np.nan:8.1f} {np.median(flow[k]) if k.any() else np.nan:5.1f}')
    print(' over-lost aspect (deg, 0 north) quartiles', np.percentile(asp[ov], [25, 50, 75]).round(0) if ov.any() else '-')
    np.savez(f'{WF}/scratch/2026-10-26/upper_margins_{label}.npz', H0=H0, H1=H1, cum=cum, flow=flow, mil=mil, hug=hug,
             m0=m[Y0], m1=m[Y1], band=band, zu=zu, dist=dist, tr=np.array(tr)[:6])
