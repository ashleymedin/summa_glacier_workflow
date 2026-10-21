import numpy as np, rasterio, sys
SP='/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/0145f8cb-2306-44c4-a47c-a55707ead47a/scratchpad'
for g,G in [('wolverine','Wolverine'),('gulkana','Gulkana')]:
    d=f'data/domain_{G}/attributes/'
    dem=rasterio.open(d+f'elevation/dem/domain_{G}_elv.tif').read(1).astype(float)
    old=rasterio.open(d+f'elevation/dem/domain_{G}_glacier_elv.tif').read(1).astype(float)
    new=rasterio.open(f'{SP}/rast_{g}/domain_{G}_glacier_elv.tif').read(1).astype(float)
    rid=rasterio.open(f'{SP}/rast_{g}/domain_{G}_rgi_id.tif').read(1)
    ice=rid>0
    tid=np.bincount(rid[(np.abs(old-dem)>0.01)&ice]).argmax(); m=rid==tid
    print(f'== {G}: target glacier cells {m.sum()}, changed vs old {(np.abs(new-old)>0.01)[m].sum()}, max |new-old| {np.abs(new-old)[m].max():.1f}, other glaciers changed {(np.abs(new-old)>0.01)[ice&~m].sum()}')
    for name,z in [('old',old),('new',new)]:
        dz=[]
        for a,b in [((slice(None,-1),slice(None)),(slice(1,None),slice(None))),((slice(None),slice(None,-1)),(slice(None),slice(1,None)))]:
            both=m[a]&m[b]; dz.append(np.abs(z[a]-z[b])[both])
        dz=np.concatenate(dz)
        # excess over the fill DEM's own step
        de=[]
        for a,b in [((slice(None,-1),slice(None)),(slice(1,None),slice(None))),((slice(None),slice(None,-1)),(slice(None),slice(1,None)))]:
            both=m[a]&m[b]; de.append(np.abs((z-dem)[a]-(z-dem)[b])[both])
        de=np.concatenate(de)
        print(f'  {name}: neighbour |dz| median {np.median(dz):.1f} p99 {np.percentile(dz,99):.1f} max {dz.max():.1f}; |d(surface-DEM)| between neighbours: >25 m {int((de>25).sum())}, >50 m {int((de>50).sum())}, max {de.max():.1f}')
    print('  mean surface on target old/new %.1f %.1f' % (old[m].mean(), new[m].mean()))
print('--- Wolverine remaining jumps')
G='Wolverine'; d=f'data/domain_{G}/attributes/'
dem=rasterio.open(d+f'elevation/dem/domain_{G}_elv.tif').read(1).astype(float)
old=rasterio.open(d+f'elevation/dem/domain_{G}_glacier_elv.tif').read(1).astype(float)
new=rasterio.open(f'{SP}/rast_wolverine/domain_{G}_glacier_elv.tif').read(1).astype(float)
rid=rasterio.open(f'{SP}/rast_wolverine/domain_{G}_rgi_id.tif').read(1); m=rid==109162
same=np.abs(new-old)<0.01
for a,b in [((slice(None,-1),slice(None)),(slice(1,None),slice(None))),((slice(None),slice(None,-1)),(slice(None),slice(1,None)))]:
    both=m[a]&m[b]; j=np.abs((new-dem)[a]-(new-dem)[b])
    sel=both&(j>25)
    print('jumps>25:', sel.sum(), 'both survey cells', (sel&same[a]&same[b]).sum(), 'one filled', (sel&(same[a]!=same[b])).sum(), 'both filled', (sel&~same[a]&~same[b]).sum())
