#!/usr/bin/env python3
"""Open-water area in a box from every Sentinel-2 scene, with the gauged flow that day, as a CSV.

Scenes are the Sentinel-2 L2A archive on AWS, found through the Element 84 Earth Search STAC API.  Water is
NDWI = (green - NIR) / (green + NIR) above --ndwi on the 10 m bands; the 20 m scene classification gives the
fraction of the box under cloud, cloud shadow or no data (`bad`) and under snow or ice (`snow`), so a clear
scene is one with both near zero.  Topographic shadow is not masked.  With --usgs-site each scene gets that
day's mean discharge (m3 s-1, UTC date of the scene).

Wolverine's proglacial lake and the delta above it, May to October:

    ./acquire_lake_area.py -148.919 60.3725 -148.906 60.3790 2016-05-01 2025-11-01 wolverine_lake_area.csv \\
        --usgs-site 15236900

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

STAC = 'https://earth-search.aws.element84.com/v1/search'
SCL_BAD = [0, 1, 3, 8, 9, 10]      # no data, saturated, cloud shadow, cloud medium/high, cirrus
SCL_SNOW = 11


def search(box, start, end, max_cloud):
    """Every Sentinel-2 L2A item over the box, following the STAC `next` links."""
    items, url = [], STAC
    body = {'collections': ['sentinel-2-l2a'], 'bbox': list(box), 'datetime': f'{start}T00:00:00Z/{end}T00:00:00Z',
            'query': {'eo:cloud_cover': {'lt': max_cloud}}, 'limit': 200}
    while url:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as r:
            page = json.load(r)
        items += page['features']
        nxt = next((l for l in page.get('links', []) if l['rel'] == 'next'), None)
        url, body = (nxt['href'], nxt.get('body', body)) if nxt else (None, None)
    return sorted(items, key=lambda i: i['properties']['datetime'])


def scene_water(item, box, ndwi_min):
    """Water area (km2) and the bad and snow fractions of the box in one scene; None if the box is off the scene."""
    a = item['assets']
    with rasterio.open(a['green']['href']) as g:
        T = Transformer.from_crs(4326, g.crs, always_xy=True)
        (x0, x1), (y0, y1) = zip(T.transform(box[0], box[1]), T.transform(box[2], box[3]))
        bounds = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        G = g.read(1, window=from_bounds(*bounds, g.transform), boundless=True).astype(float)
    with rasterio.open(a['nir']['href']) as n:
        N = n.read(1, window=from_bounds(*bounds, n.transform), boundless=True).astype(float)
    with rasterio.open(a['scl']['href']) as s:
        S = s.read(1, window=from_bounds(*bounds, s.transform), boundless=True, out_shape=G.shape)
    if G.size == 0 or (G == 0).mean() > 0.05:
        return None
    water = (G - N) / (G + N + 1e-9) > ndwi_min
    return water.sum() * 100 / 1e6, np.isin(S, SCL_BAD).mean(), (S == SCL_SNOW).mean()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('west', type=float); p.add_argument('south', type=float)
    p.add_argument('east', type=float); p.add_argument('north', type=float)
    p.add_argument('start', help='first date, YYYY-MM-DD'); p.add_argument('end', help='last date, YYYY-MM-DD')
    p.add_argument('output', help='CSV to write')
    p.add_argument('--months', default='5-10', help='months to keep, first-last (default 5-10)')
    p.add_argument('--max-cloud', type=float, default=70, help='scene cloud cover to search below, percent')
    p.add_argument('--ndwi', type=float, default=0.0, help='NDWI above which a pixel is water')
    p.add_argument('--usgs-site', help='USGS site whose daily discharge goes beside each scene')
    a = p.parse_args()

    box = (a.west, a.south, a.east, a.north)
    m0, m1 = (int(m) for m in a.months.split('-'))
    items = [i for i in search(box, a.start, a.end, a.max_cloud) if m0 <= int(i['properties']['datetime'][5:7]) <= m1]
    flows = fetch_usgs(a.usgs_site, a.start, a.end) if a.usgs_site else {}
    flows = {d.isoformat(): q for d, q in flows.items()}
    print(f'{len(items)} scenes')
    with open(a.output, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'scene', 'water_km2', 'bad', 'snow', 'q_cms'])
        for it in items:
            try:
                r = scene_water(it, box, a.ndwi)
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
