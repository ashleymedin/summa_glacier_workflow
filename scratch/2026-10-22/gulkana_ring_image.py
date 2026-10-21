"""Sentinel-2 true colour of Gulkana's tongue with the USGS outlines, to see what the dropped strips are."""
import sys
import numpy as np, geopandas as gpd, rasterio, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from rasterio.windows import from_bounds
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
u = gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp')
g = u[u.Glacier == 'Gulkana Glacier'].to_crs(32606).set_index('Year').geometry
x0, y0, x1, y1 = 577300, 7014000, 580300, 7017600  # the tongue
for url in sys.argv[1:]:
    with rasterio.open(url) as s:
        w = from_bounds(x0, y0, x1, y1, s.transform)
        im = s.read((1, 2, 3), window=w).transpose(1, 2, 0)
    fig, ax = plt.subplots(figsize=(9, 11 * (y1 - y0) / (x1 - x0)))
    ax.imshow(im, extent=(x0, x1, y0, y1))
    for yr, c in ((1993, 'k'), (2005, 'm'), (2014, 'c'), (2016, 'y'), (2021, 'r')):
        gpd.GeoSeries([g[yr].boundary]).plot(ax=ax, color=c, lw=1.2, label=str(yr))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.legend(loc='upper left'); ax.set_title(url.split('/')[-2])
    fig.savefig(f'{WF}/scratch/2026-10-22/tongue_{url.split("/")[-2]}.png', dpi=110, bbox_inches='tight')
