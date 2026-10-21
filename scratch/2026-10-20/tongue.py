import geopandas as gpd, pandas as pd, numpy as np, rasterio
WF = '/Users/amedin/Research/SummaSundials/summa_glacier_workflow'
def sample(path, x, y, crs_pts=32606):
    with rasterio.open(path) as s:
        xx, yy = gpd.GeoSeries(gpd.points_from_xy(x, y), crs=crs_pts).to_crs(s.crs).pipe(lambda g: (g.x.values, g.y.values))
        v = np.array([a[0] for a in s.sample(zip(xx, yy))], float)
        inb = (xx > s.bounds.left) & (xx < s.bounds.right) & (yy > s.bounds.bottom) & (yy < s.bounds.top)
        if s.nodata is not None:
            v[v == s.nodata] = np.nan
        v[~inb] = np.nan
    return v
u=gpd.read_file(f'{WF}/GlacierDEM/USGS_Glacier_Boundaries_shp/USGS_Glacier_Boundaries.shp'); g=u[u.Glacier=='Gulkana Glacier'].to_crs(32606)
r=pd.read_csv(f'{WF}/GlacierDEM/GulkanaRadarDepth/Gulkana_2024_radar_interpretations.csv').dropna(subset=['srf_bed_thick'])
p=gpd.GeoDataFrame(r,geometry=gpd.points_from_xy(r.utm6n_x,r.utm6n_y),crs=32606)
o21=g[g.Year==2021].union_all(); p['d']=p.geometry.distance(o21.boundary)
D=f'{WF}/data/domain_Gulkana/attributes'
p['mod']=sample(D+'/elevation/dem/domain_Gulkana_glacier_elv.tif',p.utm6n_x,p.utm6n_y)-sample(D+'/elevation/dem/domain_Gulkana_bedrock_elv.tif',p.utm6n_x,p.utm6n_y)
for lo,hi in ((1400,1500),(1500,1600),(1600,1700)):
  s=p[(p.srf_elev>=lo)&(p.srf_elev<hi)]
  if len(s): print(f'{lo}-{hi} m: n {len(s)}, distance to 2021 edge median {s.d.median():.0f}, radar 2024 {s.srf_bed_thick.median():.0f} m, model 2007 {s["mod"].median():.0f} m')
