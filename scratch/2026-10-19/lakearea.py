"""Wolverine proglacial lake + delta water area from Sentinel-2 L2A (earth-search STAC), NDWI on 10 m bands."""
import json, sys, urllib.request
import numpy as np, rasterio
from rasterio.windows import from_bounds
from pyproj import Transformer

BOX = (-148.919, 60.3725, -148.906, 60.3790)        # lake and delta
STAC = 'https://earth-search.aws.element84.com/v1/search'
items, body = [], {'collections': ['sentinel-2-l2a'], 'bbox': list(BOX), 'datetime': '2016-05-01T00:00:00Z/2025-11-01T00:00:00Z',
                   'query': {'eo:cloud_cover': {'lt': 70}}, 'limit': 200}
url = STAC
while url:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    r = json.load(urllib.request.urlopen(req, timeout=120))
    items += r['features']
    nxt = [l for l in r.get('links', []) if l['rel'] == 'next']
    url, body = (nxt[0]['href'], nxt[0].get('body', body)) if nxt else (None, None)
items = [i for i in items if 5 <= int(i['properties']['datetime'][5:7]) <= 10]
print(len(items), 'scenes May-Oct', file=sys.stderr)
out = []
for it in sorted(items, key=lambda i: i['properties']['datetime']):
    a = it['assets']
    try:
        with rasterio.open(a['green']['href']) as g:
            T = Transformer.from_crs(4326, g.crs, always_xy=True)
            x0, y0 = T.transform(BOX[0], BOX[1]); x1, y1 = T.transform(BOX[2], BOX[3])
            w = from_bounds(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), g.transform)
            G = g.read(1, window=w, boundless=True).astype(float)
        with rasterio.open(a['nir']['href']) as n:
            N = n.read(1, window=w, boundless=True).astype(float)
        with rasterio.open(a['scl']['href']) as s:      # 20 m: upsample by repeat
            w20 = from_bounds(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), s.transform)
            S = s.read(1, window=w20, boundless=True, out_shape=G.shape)
    except Exception as e:
        print('skip', it['id'], e, file=sys.stderr); continue
    if G.size == 0 or (G == 0).mean() > 0.05: continue
    bad = np.isin(S, [0, 1, 3, 8, 9, 10]).mean()          # nodata, saturated, shadow, cloud, cirrus
    snow = (S == 11).mean()
    ndwi = (G - N) / (G + N + 1e-9)
    wat = ndwi > 0.0
    d = it['properties']['datetime'][:10]
    out.append((d, it['id'], wat.sum() * 100 / 1e6, bad, snow, (S == 6).sum() * 100 / 1e6))
    print(f'{d} water {wat.sum()*100/1e6:.4f} km2  bad {bad:.2f} snow {snow:.2f} sclwater {(S==6).sum()*100/1e6:.4f}', flush=True)
json.dump(out, open('lakearea.json', 'w'))
