"""lat_exp with a faster conductivity decay and more lateral anisotropy."""
import os, shutil, subprocess
from pick import pick
S = os.path.dirname(os.path.abspath(__file__))
EXE = f'{S}/wtl/bin/summa_sundials_mizuroute.exe'
s, o, par = pick(f'{S}/cal_cor_1r/wolverine_calibration.nc')['bal']
procs = []
for name, extra in (('f6', {'f_hydCond': 6.0, 'kAnisotropic': 10.0}), ('f10', {'f_hydCond': 10.0, 'kAnisotropic': 10.0})):
    src, d = f'{S}/runs/lat_lat_exp', f'{S}/runs/lat_{name}'
    shutil.rmtree(d, ignore_errors=True); os.makedirs(f'{d}/output')
    shutil.copytree(f'{src}/settings', f'{d}/settings'); shutil.copy(f'{src}/initial_state.nc', d)
    open(f'{d}/rerun.toml', 'w').write(open(f'{src}/rerun.toml').read().replace(src, d))
    p = dict(par); p.update(extra)
    args = [EXE, '-c', f'{d}/rerun.toml'] + sum([['--param', k, repr(float(v))] for k, v in p.items()], [])
    procs.append((name, subprocess.Popen(args, cwd=d, stdout=open(f'{d}/rerun.log', 'w'), stderr=subprocess.STDOUT)))
for name, p in procs: print(name, p.wait(), flush=True)
