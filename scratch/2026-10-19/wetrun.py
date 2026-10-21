import subprocess, sys
from pick import pick
S='/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/e7b19ecd-74a9-45a0-aca9-42b7b0e01d99/scratchpad'
d=sys.argv[1]; extra=dict(a.split('=') for a in sys.argv[2:])
s,o,par=pick(f'{S}/cal_cor_lat/wolverine_calibration.nc')['bal']; par=dict(par); par.update({k:float(v) for k,v in extra.items()})
args=[f'{S}/wtw/bin/summa_sundials_mizuroute.exe','-c',f'{d}/rerun.toml']+sum([['--param',k,repr(float(v))] for k,v in par.items()],[])
r=subprocess.run(args,cwd=d,stdout=open(f'{d}/rerun.log','w'),stderr=subprocess.STDOUT); print(d,'exit',r.returncode)
