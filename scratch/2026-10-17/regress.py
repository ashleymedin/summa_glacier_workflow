"""Rerun lat_base and lat_lat_exp on the current wtl build into *_adv and compare every output variable."""
import os, shutil, subprocess, numpy as np, netCDF4 as nc
from pick import pick
S = os.path.dirname(os.path.abspath(__file__))
s, o, par = pick(f'{S}/cal_cor_1r/wolverine_calibration.nc')['bal']
procs = []
for name in ('lat_base', 'lat_lat_exp'):
    src, d = f'{S}/runs/{name}', f'{S}/runs/{name}_adv'
    shutil.rmtree(d, ignore_errors=True); os.makedirs(f'{d}/output')
    shutil.copytree(f'{src}/settings', f'{d}/settings'); shutil.copy(f'{src}/initial_state.nc', d)
    open(f'{d}/rerun.toml', 'w').write(open(f'{src}/rerun.toml').read().replace(src, d))
    args = [f'{S}/wtl/bin/summa_sundials_mizuroute.exe', '-c', f'{d}/rerun.toml'] + sum([['--param', k, repr(float(v))] for k, v in par.items()], [])
    procs.append((name, src, d, subprocess.Popen(args, cwd=d, stdout=open(f'{d}/rerun.log', 'w'), stderr=subprocess.STDOUT)))
for name, src, d, p in procs:
    print(name, 'exit', p.wait())
    for f in ('wolverine_timestep.nc', 'wolverine_day.nc'):
        a, b = nc.Dataset(f'{src}/output/{f}'), nc.Dataset(f'{d}/output/{f}')
        diff = [v for v in a.variables if v in b.variables and a[v].dtype.kind == 'f' and not np.array_equal(np.ma.filled(a[v][:], -1e30), np.ma.filled(b[v][:], -1e30))]
        print('  ', f, len(a.variables), 'variables; differing:', diff)
