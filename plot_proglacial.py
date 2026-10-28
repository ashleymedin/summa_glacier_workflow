#!/usr/bin/env python3
"""Satellite images of each glacier's terminus and gauge, with the stream reach from the NHD and the model's: plot_proglacial.py <out.pdf>

Esri World Imagery (WorldView-2: Wolverine 29 Sep 2025, Gulkana 22 Jul 2024), fetched in Alaska Albers (EPSG:3338) so the axes are in
metres; Wolverine in (a), Gulkana in (b). Drawn over them, in each panel, the ice front found from the ArcticDEM strips (nhd_reach.py), the NHD stream from it to the gauge (dark blue,
dotted where NHD does not map it) and the reach the model's stream HRU has, its stream length (cases.yaml) from the gauge along that
stream (red).
Gauges from the USGS monitoring-location service.
"""
import io
import os
import sys
import urllib.request

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from pyproj import Transformer

from domain_config import load_config
from nhd_reach import cut_from_gauge, model_reach_length

HERE = os.path.dirname(os.path.abspath(__file__))
T = Transformer.from_crs(4326, 3338, always_xy=True)
URL = ("https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?"
       "bbox={},{},{},{}&bboxSR=3338&imageSR=3338&size={},{}&format=png&f=image")
# domain, title, gauge (lon, lat), terminus (lon, lat), panel centre (lon, lat), half width (m), features (label, lon, lat)
SITES = [("wolverine", "Wolverine Glacier and USGS 15236900", (-148.896667, 60.370556), (-148.9170, 60.3805), (-148.9065, 60.3755), 1100,
          [("proglacial lake\n0.021 km$^2$", -148.9113, 60.3745), ("delta", -148.9160, 60.3772), ("bedrock gorge", -148.9200, 60.3792)]),
         ("gulkana", "Gulkana Glacier and USGS 15478040", (-145.468056, 63.240278), (-145.4260, 63.2586), (-145.4470, 63.2500), 2100,
          [("moraine and\nbraided outwash", -145.4420, 63.2470), ("Phelan Creek", -145.4640, 63.2440)])]


def main():
    out = sys.argv[1]
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.2))
    for ax, letter, (domain, title, gauge, term, centre, half, feats) in zip(axes, "ab", SITES):
        c = load_config(os.path.join(HERE, "domains", f"{domain}.yaml"))
        cx, cy = T.transform(*centre)
        n = 1400
        img = Image.open(io.BytesIO(urllib.request.urlopen(URL.format(cx - half, cy - half, cx + half, cy + half, n, n), timeout=120).read()))
        ext = [-half / 1000, half / 1000, -half / 1000, half / 1000]
        ax.imshow(np.asarray(img.convert("RGB")), extent=ext)
        km = lambda lon, lat: ((T.transform(lon, lat)[0] - cx) / 1000, (T.transform(lon, lat)[1] - cy) / 1000)
        glat, glon = (float(v) for v in c["pour_point"].split("/"))
        gx, gy = km(glon, glat)  # the pour point, where the NHD path ends
        nhd = os.path.join(c["project_dir"], "shapefiles", "nhd.gpkg")
        full = gpd.read_file(nhd, layer="reach").to_crs(3338).geometry.iloc[0]
        mapped = gpd.read_file(nhd, layer="reach_mapped").to_crs(3338).geometry.iloc[0]
        front = gpd.read_file(nhd, layer="terminus").to_crs(3338).geometry.iloc[0]
        local = lambda g: ((np.array(g.xy[0]) - cx) / 1000, (np.array(g.xy[1]) - cy) / 1000)
        length = model_reach_length(c)
        ax.plot(*local(cut_from_gauge(full, length)), color="#ff4d4d", lw=9, alpha=0.5, solid_capstyle="round", zorder=3, label=f"model reach, {length:g} m")
        ax.plot(*local(full), color="#08306b", lw=1.8, ls=":", zorder=4)
        ax.plot(*local(mapped), color="#08306b", lw=3.0, zorder=4, label=f"NHD stream, ice front to gauge ({full.length:.0f} m; dotted: unmapped)")
        tx, ty = (front.x - cx) / 1000, (front.y - cy) / 1000
        ax.plot(gx, gy, marker="^", ms=12, mfc="red", mec="white", mew=1.5, ls="none", zorder=6)
        ax.annotate("gauge", (gx, gy), xytext=(8, -14), textcoords="offset points", color="white", fontsize=10, weight="bold")
        ax.plot(tx, ty, marker="o", ms=9, mfc="none", mec="yellow", mew=2, ls="none", zorder=6)
        ax.annotate("ice front", (tx, ty), xytext=(8, 6), textcoords="offset points", color="yellow", fontsize=10, weight="bold")
        for lab, lon, lat in feats:
            fx, fy = km(lon, lat)
            ax.annotate(lab, (fx, fy), color="white", fontsize=9, ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.2", fc="black", alpha=0.35, lw=0))
        x0, y0 = ext[0] + 0.1 * (ext[1] - ext[0]), ext[2] + 0.06 * (ext[3] - ext[2])
        ax.plot([x0, x0 + 0.5], [y0, y0], color="white", lw=3)
        ax.text(x0 + 0.25, y0 + 0.03 * (ext[3] - ext[2]), "500 m", color="white", ha="center", fontsize=9)
        ax.text(0.02, 0.98, f"({letter})", transform=ax.transAxes, ha="left", va="top", fontsize=13, fontweight="bold",
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=2))
        ax.set_xlim(ext[0], ext[1])
        ax.set_ylim(ext[2], ext[3])
        ax.set_title(title, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
        handles, labels = ax.get_legend_handles_labels()
        uniq = dict(zip(labels, handles))
        ax.legend(uniq.values(), uniq.keys(), loc="upper right", fontsize=8, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    print("wrote", out)


if __name__ == "__main__":
    main()
