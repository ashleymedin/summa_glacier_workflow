#!/usr/bin/env python3
"""Open-water area in a box from every Sentinel-2 or Landsat scene, with the gauged flow that day, as a CSV.

Sentinel-2 L2A (10 m, mid-2015 on) comes from the archive on AWS through the Element 84 Earth Search STAC API;
Landsat 5, 7, 8 and 9 Collection 2 surface reflectance (30 m) from the Microsoft Planetary Computer, whose
anonymous token signs the asset links.  A pixel is water when NDWI = (green - NIR) / (green + NIR) is above
--ndwi, MNDWI = (green - SWIR) / (green + SWIR) above --mndwi, and blue below --max-blue, on reflectance from
each band's scale and offset; the defaults pass turbid lake water and leave out wet gravel, ice and snow.
The scene's own mask (Sentinel-2 scene classification,
Landsat QA_PIXEL) gives the fraction of the box under cloud, cloud shadow or no data (`bad`, which includes
Landsat 7's scan-line gaps) and under snow or ice (`snow`), so a clear scene is one with both near zero.
Topographic shadow is not masked.  With --usgs-site each scene gets that day's mean discharge (m3 s-1, UTC
date of the scene).

Wolverine's proglacial lake, May to October:

    ./acquire_lake_area.py -148.918 60.3720 -148.905 60.3775 2015-06-01 2022-12-31 wolverine_lake_s2.csv \\
        --usgs-site 15236900
    ./acquire_lake_area.py -148.918 60.3720 -148.905 60.3775 2008-01-01 2015-12-31 wolverine_lake_landsat.csv \\
        --usgs-site 15236900 --source landsat

Columns: date, scene, water_km2, bad, snow, q_cms.
"""

import argparse
import csv
import json
import urllib.request

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds

from acquire_streamflow import fetch_usgs

SOURCES = {
    'sentinel2': {'stac': 'https://earth-search.aws.element84.com/v1/search', 'collection': 'sentinel-2-l2a',
                  'green': 'green', 'nir': 'nir', 'mask': 'scl', 'token': None},
    'landsat': {'stac': 'https://planetarycomputer.microsoft.com/api/stac/v1/search', 'collection': 'landsat-c2-l2',
                'green': 'green', 'nir': 'nir08', 'mask': 'qa_pixel',
                'token': 'https://planetarycomputer.microsoft.com/api/sas/v1/token/landsat-c2-l2'},
}
SCL_BAD, SCL_SNOW = [0, 1, 3, 8, 9, 10], [11]     # no data, saturated, shadow, cloud, cirrus; snow
QA_BAD, QA_SNOW = 0b11111, 0b100000                # QA_PIXEL bits 0-4 fill, cloud, cirrus, shadow; bit 5 snow


def search(src, box, start, end, max_cloud):
    """Every item of the source over the box, following the STAC `next` links."""
    items, url = [], src['stac']
    body = {'collections': [src['collection']], 'bbox': list(box), 'datetime': f'{start}T00:00:00Z/{end}T23:59:59Z',
            'query': {'eo:cloud_cover': {'lt': max_cloud}}, 'limit': 200}
    while url:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as r:
            page = json.load(r)
        items += page['features']
        nxt = next((l for l in page.get('links', []) if l['rel'] == 'next'), None)
        url, body = (nxt['href'], nxt.get('body', body)) if nxt else (None, None)
    return sorted(items, key=lambda i: i['properties']['datetime'])


def read_box(asset, box, token, shape=None, harmonized=False):
    """The box from one asset, as reflectance when the asset gives a scale, and where it is fill."""
    href = asset['href'] + ('?' + token if token else '')
    with rasterio.open(href) as r:
        T = Transformer.from_crs(4326, r.crs, always_xy=True)
        (x0, x1), (y0, y1) = zip(T.transform(box[0], box[1]), T.transform(box[2], box[3]))
        w = from_bounds(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), r.transform)
        x = r.read(1, window=w, boundless=True, out_shape=shape)
    rb = (asset.get('raster:bands') or [{}])[0]
    return x * rb.get('scale', 1.0) + (0.0 if harmonized else rb.get('offset', 0.0)), x == rb.get('nodata', 0)


def scene_water(item, src, box, test, token):
    """Water area (km2) and the bad and snow fractions of the box in one scene; None if the box is off the scene."""
    a = item['assets']
    h = bool(item['properties'].get('earthsearch:boa_offset_applied'))   # pixels already carry the offset
    G, fill = read_box(a[src['green']], box, token, harmonized=h)
    N, _ = read_box(a[src['nir']], box, token, G.shape, h)
    B, _ = read_box(a['blue'], box, token, G.shape, h)
    W, _ = read_box(a['swir16'], box, token, G.shape, h)
    M, _ = read_box(a[src['mask']], box, token, G.shape)
    if G.size == 0 or fill.mean() > 0.95:
        return None
    if src['mask'] == 'scl':
        bad, snow = np.isin(M, SCL_BAD) | fill, np.isin(M, SCL_SNOW)
    else:
        M = M.astype(np.int64)
        bad, snow = ((M & QA_BAD) > 0) | fill, (M & QA_SNOW) > 0
    ndwi_min, mndwi_min, blue_max = test
    with np.errstate(divide='ignore', invalid='ignore'):
        water = ((G - N) / (G + N) > ndwi_min) & ((G - W) / (G + W) > mndwi_min) & (B < blue_max) & ~fill
    px = ((a[src['green']].get('raster:bands') or [{}])[0].get('spatial_resolution') or item['properties'].get('gsd') or 30) ** 2
    return water.sum() * px / 1e6, bad.mean(), snow.mean()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('west', type=float); p.add_argument('south', type=float)
    p.add_argument('east', type=float); p.add_argument('north', type=float)
    p.add_argument('start', help='first date, YYYY-MM-DD'); p.add_argument('end', help='last date, YYYY-MM-DD')
    p.add_argument('output', help='CSV to write')
    p.add_argument('--source', choices=SOURCES, default='sentinel2')
    p.add_argument('--months', default='5-10', help='months to keep, first-last (default 5-10)')
    p.add_argument('--max-cloud', type=float, default=70, help='scene cloud cover to search below, percent')
    p.add_argument('--ndwi', type=float, default=0.3, help='NDWI above which a pixel can be water (wet gravel ~0.25)')
    p.add_argument('--mndwi', type=float, default=0.6, help='MNDWI (green, SWIR 1.6 um) above which it can be water')
    p.add_argument('--max-blue', type=float, default=0.25, help='blue reflectance below which it can be water (not ice or snow)')
    p.add_argument('--usgs-site', help='USGS site whose daily discharge goes beside each scene')
    a = p.parse_args()

    src = SOURCES[a.source]
    box = (a.west, a.south, a.east, a.north)
    m0, m1 = (int(m) for m in a.months.split('-'))
    items = [i for i in search(src, box, a.start, a.end, a.max_cloud) if m0 <= int(i['properties']['datetime'][5:7]) <= m1]
    flows = {d.isoformat(): q for d, q in (fetch_usgs(a.usgs_site, a.start, a.end) if a.usgs_site else {}).items()}
    print(f'{len(items)} scenes')
    token = None
    with open(a.output, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'scene', 'water_km2', 'bad', 'snow', 'q_cms'])
        for n, it in enumerate(items):
            if src['token'] and n % 50 == 0:          # tokens last about an hour
                with urllib.request.urlopen(src['token'], timeout=60) as r:
                    token = json.load(r)['token']
            try:
                r = scene_water(it, src, box, (a.ndwi, a.mndwi, a.max_blue), token)
            except rasterio.errors.RasterioIOError as e:
                print('skipped', it['id'], e); continue
            if r is None:
                continue
            day = it['properties']['datetime'][:10]
            q = flows.get(day)
            w.writerow([day, it['id'], f'{r[0]:.4f}', f'{r[1]:.3f}', f'{r[2]:.3f}', '' if q is None else f'{q:.3f}'])
            f.flush()
    print('wrote', a.output)


if __name__ == '__main__':
    main()
