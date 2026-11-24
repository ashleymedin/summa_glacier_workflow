#!/usr/bin/env python3
"""Satellite images of each glacier's terminus and gauge, with the stream reach from the NHD and the model's:
plot_proglacial.py <out.pdf> [domain ...] (default wolverine gulkana; also lemon_creek, on Sentinel-2 with a closer panel)

Esri World Imagery (WorldView-2: Wolverine 29 Sep 2025, Gulkana 22 Jul 2024), fetched in Alaska Albers (EPSG:3338; Lemon Creek in UTM) so the axes are in
metres; Wolverine in (a), Gulkana in (b). Drawn over them, in each panel, the ice front found from the ArcticDEM strips (nhd_reach.py), the NHD stream from it to the gauge (dark blue,
dashed where NHD does not map it), with the model's stream length (cases.yaml) in the legend, or a split domain's reach of each GRU.
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
from matplotlib import patheffects
from PIL import Image
from pyproj import Transformer

from domain_config import load_config
from nhd_reach import model_reach_length

NAVY = "#08306b"  # as plot_basin_setup.py
LIGHT = [patheffects.withStroke(linewidth=4.0, foreground="white", alpha=0.5)]  # the line stays visible on dark water
HERE = os.path.dirname(os.path.abspath(__file__))
EPSG = {"lemon_creek": 32608}  # a site drawn in its UTM zone, north up: Alaska Albers (3338), the default, is turned 15 degrees at Juneau
URL = ("https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?"
       "bbox={},{},{},{}&bboxSR={}&imageSR={}&size={},{}&format=png&f=image")
# domain, title, gauge (lon, lat), terminus (lon, lat), panel centre (lon, lat), half width (m), features (label, lon, lat)
SITES = [("wolverine", "Wolverine Glacier and USGS 15236900", (-148.896667, 60.370556), (-148.9170, 60.3805), (-148.9065, 60.3755), 1100,
          [("proglacial lake\n0.021 km$^2$", -148.9113, 60.3745), ("delta", -148.9160, 60.3772), ("bedrock gorge", -148.9200, 60.3792)]),
         ("gulkana", "Gulkana Glacier and USGS 15478040", (-145.468056, 63.240278), (-145.4260, 63.2586), (-145.4470, 63.2500), 2100,
          [("moraine and\nbraided outwash", -145.4420, 63.2470), ("Phelan Creek", -145.4640, 63.2440)])]
SITES.append(("lemon_creek", "Lemon Creek Glacier and USGS 15052000", (-134.4226873, 58.3915312), (-134.369, 58.4045), (-134.3935, 58.3955), 2550,
              [("Lake Thomas", -134.3850, 58.4090), ("lower lake", -134.3880, 58.4050), ("upper lake", -134.3815, 58.4135),
               ("Thomas Glacier", -134.3585, 58.4155), ("Ptarmigan Glacier", -134.3680, 58.3738), ("Lemon Creek\nGlacier", -134.3610, 58.3960)]))
# a domain drawn on a Sentinel-2 scene (item id, half width of a second, closer panel of it, its centre and features)
SCENES = {"lemon_creek": ("S2A_MSIL2A_20240818T201851_R071_T08VNK_20240819T014500", 1000, (-134.3745, 58.4080),
                          [("Lake Thomas", -134.3805, 58.4078), ("lower lake", -134.3835, 58.4025), ("upper lake", -134.3795, 58.4130)])}


def epsg(domain):
    return EPSG.get(domain, 3338)


def project(domain, lon, lat):
    return Transformer.from_crs(4326, epsg(domain), always_xy=True).transform(lon, lat)


def window(domain):
    """The area of a domain's image, as a (left, bottom, right, top) box in EPSG epsg(domain), or None."""
    for s in SITES:
        if s[0] == domain:
            x, y = project(domain, *s[4])
            return x - s[5], y - s[5], x + s[5], y + s[5]
    return None


def esri(cx, cy, half, code, n=1400):
    """Esri World Imagery around a point of EPSG code."""
    img = Image.open(io.BytesIO(urllib.request.urlopen(URL.format(cx - half, cy - half, cx + half, cy + half, code, code, n, n), timeout=120).read()))
    return np.asarray(img.convert("RGB"))


def sentinel2(item, cx, cy, half, code):
    """A Sentinel-2 L2A scene (Microsoft Planetary Computer) around a point of EPSG code, true colour at 10 m."""
    import planetary_computer
    import pystac_client
    from odc.geo.geobox import GeoBox
    from odc.stac import load
    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
    it = cat.get_collection("sentinel-2-l2a").get_item(item)
    ds = load([it], bands=["B04", "B03", "B02"], geobox=GeoBox.from_bbox((cx - half, cy - half, cx + half, cy + half), f"EPSG:{code}", resolution=10), resampling="cubic")
    off = 1000 if float(it.properties.get("s2:processing_baseline", "0")) >= 4 else 0
    rgb = np.dstack([ds[b].values[0].astype(float) for b in ("B04", "B03", "B02")]) - off
    return np.clip(rgb / 7000.0, 0, 1) ** 0.5


def main():
    out, names = sys.argv[1], sys.argv[2:] or ["wolverine", "gulkana"]
    panels = []
    for domain, title, gauge, term, centre, half, feats in (s for s in SITES if s[0] in names):
        if domain in SCENES:
            item, half2, centre2, feats2 = SCENES[domain]
            panels += [(domain, title, centre, half, feats, item, centre2, half2), (domain, "The lakes at the two glacier fronts", centre2, half2, feats2, None, None, None)]
        else:
            panels.append((domain, title, centre, half, feats, None, None, None))
    fig, axes = plt.subplots(1, len(panels), figsize=(6 * len(panels), 6.2), squeeze=False)
    for ax, letter, (domain, title, centre, half, feats, item, centre2, half2) in zip(axes[0], "abc", panels):
        c = load_config(os.path.join(HERE, "domains", f"{domain}.yaml"))
        code = epsg(domain)
        cx, cy = project(domain, *centre)
        ext = [-half / 1000, half / 1000, -half / 1000, half / 1000]
        ax.imshow(sentinel2(SCENES[domain][0], cx, cy, half, code) if domain in SCENES else esri(cx, cy, half, code), extent=ext)
        if centre2:  # the closer panel's area
            x2, y2 = project(domain, *centre2)
            ax.add_patch(plt.Rectangle(((x2 - half2 - cx) / 1000, (y2 - half2 - cy) / 1000), half2 / 500, half2 / 500, fill=False, ec="yellow", lw=1.4, ls="--", zorder=5))
        km = lambda lon, lat: tuple((v - o) / 1000 for v, o in zip(project(domain, lon, lat), (cx, cy)))
        glat, glon = (float(v) for v in c["pour_point"].split("/"))
        gx, gy = km(glon, glat)  # the pour point, where the NHD path ends
        nhd = os.path.join(c["project_dir"], "shapefiles", "nhd.gpkg")
        full = gpd.read_file(nhd, layer="reach").to_crs(code).geometry.iloc[0]
        mapped = gpd.read_file(nhd, layer="reach_mapped").to_crs(code).geometry.iloc[0]
        front = gpd.read_file(nhd, layer="terminus").to_crs(code).geometry.iloc[0]
        local = lambda g: ((np.array(g.xy[0]) - cx) / 1000, (np.array(g.xy[1]) - cy) / 1000)
        split = os.path.join(HERE, "domains", f"{domain}_grus.yaml")
        length = None if os.path.exists(split) else model_reach_length(c)
        if os.path.exists(split):  # a split domain's reaches, one per GRU, in place of the one from the ice front
            from add_stream_grus import reach_parts
            g = load_config(split)
            parts = [reach_parts(g, k) for k in range(1, len(g["grus"]) + 1)]
            named = "stream reach of each GRU ({} m; dashed: not on NHD)".format(", ".join(f"{x[0].length:.0f}" for x in parts))
            for _, on, off in parts:
                for geom, kw in ((on, dict(lw=3.0, label=named)), (off, dict(lw=3.0, ls=(0, (2.2, 0.9))))):
                    for q in getattr(geom, "geoms", [geom]):
                        if q.length > 0:
                            q = gpd.GeoSeries([q], crs=g["utm_crs"]).to_crs(code).iloc[0]
                            ax.plot(*local(q), color=NAVY, zorder=4, path_effects=LIGHT, **kw)
        if not os.path.exists(split):
            ax.plot(*local(full), color=NAVY, lw=3.0, ls=(0, (2.2, 0.9)), zorder=4, path_effects=LIGHT)
            ax.plot(*local(mapped), color=NAVY, lw=3.0, zorder=4, label=f"NHD stream, ice front to gauge, {full.length:.0f} m" + (f"\n(model reach {length:g} m; dashed: unmapped)" if length else " (dashed: unmapped)"))
        ax.plot(gx, gy, marker="^", ms=12, mfc="red", mec="white", mew=1.5, ls="none", zorder=6)
        ax.annotate("gauge", (gx, gy), xytext=(8, -14), textcoords="offset points", color="white", fontsize=10, weight="bold")
        fronts = [km(*q["reach"]["points"][0]) for q in g["grus"]] if os.path.exists(split) else [((front.x - cx) / 1000, (front.y - cy) / 1000)]
        for n, (tx, ty) in enumerate(fronts):
            if ext[0] < tx < ext[1] and ext[2] < ty < ext[3]:
                ax.plot(tx, ty, marker="o", ms=9, mfc="none", mec="yellow", mew=2, ls="none", zorder=6, label="recent ice front" if len(fronts) > 1 else None)
                if len(fronts) == 1:
                    ax.annotate("ice front", (tx, ty), xytext=(8, 6), textcoords="offset points", color="yellow", fontsize=10, weight="bold")
        for lab, lon, lat in feats:
            fx, fy = km(lon, lat)
            ax.annotate(lab, (fx, fy), color="white", fontsize=9, ha="center", va="center",
                        bbox=dict(boxstyle="round,pad=0.2", fc="black", alpha=0.35, lw=0))
        x0, y0 = ext[0] + (0.05 if centre2 else 0.72) * (ext[1] - ext[0]), ext[2] + 0.06 * (ext[3] - ext[2])
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
        if domain in SCENES:  # under the closer panel's partner, off the glacier
            if centre2:
                ax.legend(uniq.values(), uniq.keys(), loc="upper left", bbox_to_anchor=(0, -0.01), ncol=2, fontsize=8, frameon=False, labelcolor="black")
        else:
            ax.legend(uniq.values(), uniq.keys(), loc="upper right", fontsize=8, framealpha=0.85)
    fig.tight_layout()
    fig.savefig(out, dpi=200, bbox_inches="tight" if any(p[0] in SCENES for p in panels) else None, pad_inches=0.05)
    print("wrote", out)


if __name__ == "__main__":
    main()
