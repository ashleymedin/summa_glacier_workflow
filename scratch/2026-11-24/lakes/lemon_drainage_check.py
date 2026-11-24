#!/usr/bin/env python3
"""Lemon Creek's drainage past the lakes: the NHD water bodies on Ptarmigan's and the lakes' streams down to the gauge, distances of the 2012 terminus of
Sheik et al. (2015) to the lakes and the 2025 ice front, and Esri World Imagery now and in Wayback releases (argument: folder for the images)."""
import sys, io, math, json, urllib.request, warnings; warnings.filterwarnings("ignore")
import geopandas as gpd, numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point, LineString
f = "data/domain_LemonCreek_grus/shapefiles/nhd.gpkg"; C = 32608
F = gpd.read_file(f, layer="flowlines").to_crs(C).explode(index_parts=False).reset_index(drop=True); F.columns = [c.lower() for c in F.columns]
W = gpd.read_file(f, layer="waterbodies").to_crs(C); W.columns = [c.lower() for c in W.columns]; W = W[W.ftype.isin((390, 436))]
pt = lambda lon, lat: gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(C).iloc[0]
named = {"Ptarmigan stream": pt(-134.37369, 58.38108), "upper-middle lake stream": pt(-134.37295, 58.41051)}
for n, p in named.items():
    k = F.distance(p).idxmin(); hit = []; path = 0
    for _ in range(60):
        g = F.geometry[k]; path += g.length
        for j, w in W.iterrows():
            if w.geometry.intersection(LineString([q[:2] for q in g.coords])).length > 5: hit.append((round(w.geometry.area / 1e6, 3), int(F.ftype[k])))
        tail = Point(g.coords[-1][:2]); nxt = [i for i in F.index if i != k and Point(F.geometry[i].coords[0][:2]).distance(tail) < 1]
        if not nxt: break
        k = nxt[0]
    print(n, "passes NHD lakes (km2, ftype)", hit, "over %.0f m" % path)
t12 = pt(-134 - 22 / 60 - 6.18 / 3600, 58 + 24 / 60 + 22.14 / 3600); t25 = pt(-134.369, 58.4045)
print("2012 terminus to 2025 front %.0f m" % t12.distance(t25), [(round(w.geometry.area / 1e6, 3), "d12 %.0f d25 %.0f m, bearing from 2012 %.0f" % (w.geometry.distance(t12), w.geometry.distance(t25), math.degrees(math.atan2(w.geometry.centroid.x - t12.x, w.geometry.centroid.y - t12.y)) % 360)) for _, w in W.iterrows() if w.geometry.distance(t12) < 1500])
if len(sys.argv) > 1:
    z = 17; n = 2 ** z; tx = lambda lon: (lon + 180) / 360 * n; ty = lambda lat: (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    x0, x1, y0, y1 = int(tx(-134.3865)), int(tx(-134.3645)), int(ty(58.4135)), int(ty(58.4005))
    cfg = json.load(urllib.request.urlopen("https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json", timeout=60))
    rel = sorted(cfg.items(), key=lambda kv: kv[1]["itemTitle"]); rel = [rel[int(i)] for i in np.linspace(0, len(rel) - 1, 7)]
    for k, v in rel:
        im = Image.new("RGB", (256 * (x1 - x0 + 1), 256 * (y1 - y0 + 1))); 
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                try: im.paste(Image.open(io.BytesIO(urllib.request.urlopen(f"https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{k}/{z}/{y}/{x}", timeout=60).read())), ((x - x0) * 256, (y - y0) * 256))
                except Exception as e: pass
        d = ImageDraw.Draw(im)
        for lon, lat, c in ((-134.368383, 58.406150, "cyan"), (-134.369, 58.4045, "yellow")):
            a, b = (tx(lon) - x0) * 256, (ty(lat) - y0) * 256; d.ellipse([a - 10, b - 10, a + 10, b + 10], outline=c, width=3)
        o = f"{sys.argv[1]}/wb_{v['itemTitle'][-11:-1]}.png"; im.save(o); print(o, im.size, np.asarray(im).mean().round(2))
