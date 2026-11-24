#!/usr/bin/env python3
"""Open water (NDWI > 0.1) in a box on each Lemon Creek lake and on the dark patch at the corner of Figure 12a's box, clear Jul-Oct Landsat (30 m) and Sentinel-2 (10 m) by year; the glaciers' mean aspects."""
import sys, warnings; warnings.filterwarnings("ignore"); sys.path.insert(0, ".")
import numpy as np, planetary_computer, pystac_client, rasterio, geopandas as gpd
from odc.stac import load
from odc.geo.geobox import GeoBox
from pyproj import Transformer
T = Transformer.from_crs(4326, 32608, always_xy=True)
B = {"upper": (-134.3793, 58.4098, -134.3712, 58.4145), "middle": (-134.3800, 58.4050, -134.3700, 58.4096), "lower": (-134.3865, 58.4020, -134.3785, 58.4052), "corner": (-134.3965, 58.3975, -134.3840, 58.4015)}
lo = np.array([b for b in B.values()]); x0, y0 = T.transform(lo[:, 0].min(), lo[:, 1].min()); x1, y1 = T.transform(lo[:, 2].max(), lo[:, 3].max())
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
for col, bands, res, years in (("landsat-c2-l2", ["green", "nir08", "qa_pixel"], 30, range(1999, 2026, 2)), ("sentinel-2-l2a", ["B03", "B08", "SCL"], 10, range(2017, 2027, 2))):
    gb = GeoBox.from_bbox((x0, y0, x1, y1), "EPSG:32608", resolution=res); xx = np.array(gb.coords["x"].values); yy = np.array(gb.coords["y"].values); X, Y = np.meshgrid(xx, yy); L = Transformer.from_crs(32608, 4326, always_xy=True).transform(X, Y)
    for yr in years:
        try:
            it = sorted(cat.search(collections=[col], bbox=(-134.40, 58.395, -134.36, 58.415), datetime=f"{yr}-07-15/{yr}-10-05", query={"eo:cloud_cover": {"lt": 45}}).items(), key=lambda i: i.properties["eo:cloud_cover"])[:6]
            best = None
            for i in it:
                d = load([i], bands=bands, geobox=gb, resampling="nearest"); g, n, q = (d[b].values[0].astype(float) for b in bands)
                if col[0] == "l": g, n = g * 2.75e-5 - .2, n * 2.75e-5 - .2; bad = (q.astype(int) & 0b11010) > 0
                else:
                    g, n = g - (1000 if float(i.properties.get("s2:processing_baseline", 0)) >= 4 else 0), n - (1000 if float(i.properties.get("s2:processing_baseline", 0)) >= 4 else 0); bad = np.isin(q, (0, 1, 8, 9, 10))
                bad |= ~np.isfinite(g) | (g + n <= 0); w = (g - n) / np.where(g + n > 0, g + n, 1); s = bad.mean()
                if best is None or s < best[0]: best = (s, w, g, n, bad, i.datetime.date())
            if best:
                s, w, g, n, bad, dt = best; dark = (w > .1) & ~bad & (g < (.35 if col[0] == "l" else 3500))
                print(col[:8], dt, "cloud %.2f" % s, {k: (round(float((dark & (L[0] > b[0]) & (L[0] < b[2]) & (L[1] > b[1]) & (L[1] < b[3])).sum() * res * res / 1e6), 3)) for k, b in B.items()}, flush=True)
        except Exception as e: print(yr, "failed", str(e)[:80])
with rasterio.open("data/domain_LemonCreek_grus/attributes/elevation/dem/domain_LemonCreek_glacier_elv_utm.tif") as r:
    z = r.read(1, masked=True).filled(np.nan); tr = r.transform; gy, gx = np.gradient(z, abs(tr.e), tr.a); slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    R = gpd.read_file("data/external/RGI_data/nsidc0770_01.rgi60.Alaska/01_rgi60_Alaska.shp", where="RGIId in ('RGI60-01.01506','RGI60-01.01105','RGI60-01.01104')").to_crs(r.crs)
    for _, g in R.iterrows():
        m = ~rasterio.features.geometry_mask([g.geometry], z.shape, tr) & np.isfinite(gx); e, n = -gx[m], gy[m]  # downhill, rows run south
        print(g.RGIId, "mean aspect %.0f deg, RGI aspect %s, slope %.0f, elevation %.0f" % (np.degrees(np.arctan2(e.mean(), n.mean())) % 360, g.Aspect, np.nanmean(slope[m]), np.nanmean(z[m])))
