#!/usr/bin/env python3
"""True-colour Sentinel-2 L2A chips (10 m) of a box from the clearest late-summer scenes on Microsoft Planetary Computer,
with a domain's NHD flowlines (blue) and waterbodies (cyan outline) drawn on, for looking at lakes, ponds and outwash.

    imagery_chips.py <domain dir> <name> lon_min lat_min lon_max lat_max <years ...> [--n 2]
"""
import argparse
import os

import geopandas as gpd
import matplotlib
import numpy as np
import planetary_computer
import pystac_client
from odc.stac import load

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("domain")
p.add_argument("name")
p.add_argument("box", nargs=4, type=float)
p.add_argument("years", nargs="+", type=int)
p.add_argument("--n", type=int, default=1, help="scenes a year")
p.add_argument("--months", default="07-15/09-15")
a = p.parse_args()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagery")
os.makedirs(out, exist_ok=True)
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
nhd = os.path.join(a.domain, "shapefiles", "nhd.gpkg")
flow = gpd.read_file(nhd, layer="flowlines")
water = gpd.read_file(nhd, layer="waterbodies")
ft = [c for c in water.columns if c.lower() == "ftype"][0]
water = water[water[ft].astype(int) == 390]
for y in a.years:
    m0, m1 = a.months.split("/")
    items = list(cat.search(collections=["sentinel-2-l2a"], bbox=a.box, datetime=f"{y}-{m0}/{y}-{m1}",
                            query={"eo:cloud_cover": {"lt": 20}}).items())
    items.sort(key=lambda i: i.properties["eo:cloud_cover"])
    for it in items[:a.n]:
        ds = load([it], bands=["B04", "B03", "B02"], bbox=a.box, crs="EPSG:4326", resolution=0.00009)
        rgb = np.dstack([ds[b].values[0].astype(float) for b in ("B04", "B03", "B02")])
        off = 1000 if float(it.properties.get("s2:processing_baseline", "0")) >= 4 else 0  # L2A offset from baseline 04.00
        rgb = np.clip((rgb - off) / 2500.0, 0, 1) ** 0.8
        fig, ax = plt.subplots(figsize=(10, 10 * rgb.shape[0] / rgb.shape[1]))
        ax.imshow(rgb, extent=(a.box[0], a.box[2], a.box[1], a.box[3]))
        flow.cx[a.box[0]:a.box[2], a.box[1]:a.box[3]].plot(ax=ax, color="dodgerblue", linewidth=0.8)
        water.cx[a.box[0]:a.box[2], a.box[1]:a.box[3]].boundary.plot(ax=ax, color="cyan", linewidth=1.0)
        ax.set_xlim(a.box[0], a.box[2]); ax.set_ylim(a.box[1], a.box[3])
        date = it.datetime.strftime("%Y-%m-%d")
        ax.set_title(f"{a.name} Sentinel-2 {date} (cloud {it.properties['eo:cloud_cover']:.0f}%)")
        f = os.path.join(out, f"{a.name}_{date}.png")
        fig.savefig(f, dpi=110, bbox_inches="tight")
        plt.close(fig)
        print(f)
