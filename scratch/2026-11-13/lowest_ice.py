"""The lowest ice cell of each glacier grid every other year (surface, thickness, debris), from a rerun annual file and the case bed."""
import netCDF4 as n, numpy as np, glob
for c,s in (('wolverine_stream_delta','459_delta'),('gulkana_stream','451_front')):
    a=n.Dataset(f'{c}/summa_inputs/attributes.nc'); 
    bed=np.ma.filled(a['bed_elev'][:].astype(float),np.nan); print(c,'bed',a['bed_elev'].dimensions,bed.shape, 'wetlandMask' in a.variables)
    wm=np.ma.filled(a['wetlandMask'][:].astype(float),0) if 'wetlandMask' in a.variables else None
    d=n.Dataset(glob.glob(f'{c}/calibration_added_rerun/sample_{s}/output/*sample000001_annual.nc')[0])
    z=np.ma.filled(d['surface_elev'][:].astype(float),np.nan); deb=np.ma.filled(d['debris_thick'][:].astype(float),0)
    t=n.num2date(d['time'][:],d['time'].units)
    print(' wm shape', None if wm is None else wm.shape, 'z', z.shape)
    for i in range(0,len(t),2):
        for g in range(z.shape[3]):
            zz=z[i,:,:,g,0]; b=bed[:,:,g,0]
            if b is None: print('bed shape?'); break
            h=zz-b; ice=h>1.0
            if not ice.any(): continue
            k=np.nanargmin(np.where(ice,zz,np.inf)); r,cc=np.unravel_index(k,zz.shape)
            lowcells=np.sort(np.where(ice,zz,np.nan).ravel()); lowcells=lowcells[np.isfinite(lowcells)][:5]
            print(f'  {t[i].year} grid{g}: lowest ice z {zz[r,cc]:.0f} h {h[r,cc]:.1f} deb {deb[i,r,cc,g,0]:.2f} at ({r},{cc}) ice cells {ice.sum()} next lows {np.round(lowcells).tolist()}')
