import numpy as np, rasterio, pandas as pd
from scipy import ndimage
w = np.load("wall_slope.npz")
s30, z, glacier = w["s30"], w["z"], w["glacier"]
img = "/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data/domain_Gulkana/observations/imagery/imagery_landsat_2009-08-03.tif"
cls = rasterio.open(img).read(1)
assert cls.shape == s30.shape, (cls.shape, s30.shape)
st = np.array([[0,1,0],[1,1,1],[0,1,0]], bool)
margin = glacier & ndimage.binary_dilation(~glacier, st)
deb = cls == 2
# debris on the ice at the margin: debris in the margin cell or the next two inward
debris_near = ndimage.binary_dilation(deb & glacier, st, iterations=2) & margin
for zmax in (1800, 2000):
    m = margin & (z < zmax)
    rows = []
    for reach in (60, 150):
        k = int(reach / 30)
        outside = (~glacier).astype(float)
        # steepest and mean slope of the ground just outside each margin cell
        sm = np.where(~glacier, s30, -1)
        mx = ndimage.maximum_filter(sm, size=2 * k + 1)
        hs = ndimage.uniform_filter(np.where(~glacier, s30, 0), 2 * k + 1) / np.maximum(ndimage.uniform_filter(outside, 2 * k + 1), 1e-9)
        zr = ndimage.maximum_filter(np.where(~glacier, z, -1e9), size=2 * k + 1) - z
        for lab, v in ((f"max slope within {reach} m", mx), (f"mean slope within {reach} m", hs)):
            bins = np.arange(0, 60, 5)
            idx = np.digitize(v[m], bins) - 1
            t = pd.DataFrame({"bin": idx, "deb": debris_near[m]}).groupby("bin").deb.agg(["size", "mean"])
            t.index = [f"{bins[i]}-{bins[i]+5}" for i in t.index]
            print(f"\nmargin cells below {zmax} m: {m.sum()}, debris at margin {debris_near[m].mean():.2f}; {lab}")
            print(t.round(2).T.to_string())
