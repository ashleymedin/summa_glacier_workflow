"""Rerun the latflow balanced trial with glacier runoff diverted through the terminus-zone soil."""
import os, shutil, subprocess
from pick import pick
S = os.path.dirname(os.path.abspath(__file__))
EXE = f'{S}/wtg/bin/summa_sundials_mizuroute.exe'
src = f'{S}/runs/cor_lat_bal'
s, o, par = pick(f'{S}/cal_cor_lat/wolverine_calibration.nc')['bal']
OUT = open(f'{src}/settings/outputControl.txt').read() + "mLayerTemp | 24\nmLayerHeight | 24\nmLayerColumnOutflow | 24\nmLayerColumnInflow | 24\nmLayerLatInflowNrgFlux | 24\nmLayerSoilAdvNrgFlux | 24\nnumFluxCalls | 1\n"
procs = []
for f in (0.0, 0.1, 0.2, 0.4):
    d = f'{S}/runs/gadv_{f:.1f}'
    shutil.rmtree(d, ignore_errors=True); os.makedirs(f'{d}/output')
    shutil.copytree(f'{src}/settings', f'{d}/settings'); shutil.copy(f'{src}/initial_state.nc', d)
    open(f'{d}/settings/outputControl.txt', 'w').write(OUT)
    open(f'{d}/rerun.toml', 'w').write(open(f'{src}/rerun.toml').read().replace(src, d))
    p = dict(par); p['glacSoilFrac'] = f
    args = [EXE, '-c', f'{d}/rerun.toml'] + sum([['--param', k, repr(float(v))] for k, v in p.items()], [])
    procs.append((f, subprocess.Popen(args, cwd=d, stdout=open(f'{d}/rerun.log', 'w'), stderr=subprocess.STDOUT)))
for f, p in procs: print(f, p.wait(), flush=True)
