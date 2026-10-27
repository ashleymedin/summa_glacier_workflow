import sys, glob, netCDF4 as nc, numpy as np
for f in sys.argv[1:]:
    d = nc.Dataset(f)
    t = lambda v: (lambda a: ((a[:,2]*24+a[:,4])*60+a[:,5])*60+a[:,6]+a[:,7]/1e3)(np.array(d[v][:]).astype(float))
    dt = t('completion_time') - t('dispatch_time')
    dt[dt < 0] += 86400
    o = np.argsort(dt)[::-1]
    print(f.split('/')[-1], 'n=%d median=%.1f max=%.1f' % (len(dt), np.median(dt), dt.max()))
    print(' slowest idx/s:', [(int(i), round(dt[i],1)) for i in o[:3]], ' median idx:', int(o[len(o)//2]))
    if 'ksoil' in sys.argv[0] or True:
        try:
            names=[str(x) for x in d['param_name'][:]] if 'param_name' in d.variables else None
        except Exception: names=None
        print(' vars:', [v for v in d.variables][:30])
