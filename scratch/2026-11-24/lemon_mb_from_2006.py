#!/usr/bin/env python3
"""lemoncreek_mass_balance_seasonal.nc without the summer ending 10 Oct 2005, which a run from 1 Oct 2005 scores against its first days."""
import os, netCDF4 as nc, numpy as np, datetime as dt, sys
W = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")); sys.path.insert(0, W)
from observation_netcdf import write_observations
D = W + "/data/domain_LemonCreek/observations/calibration/"
o = nc.Dataset(D + "lemoncreek_mass_balance_seasonal.nc"); ref = dt.datetime(1950, 1, 1)
b = [[ref + dt.timedelta(minutes=int(x)) for x in r] for r in o["time_bnds"][:]]; v = np.ma.filled(o["mb_obs"][:], np.nan)
k = [i for i in range(len(v)) if b[i][0] >= dt.datetime(2005, 10, 1)]
write_observations(D + "lemoncreek_mass_balance_seasonal_2006.nc", [b[i][0] for i in k], [b[i][1] for i in k], v[k], "mb_obs", "mm", o["mb_obs"].long_name,
                   attrs={"title": o.title, "source": o.source, "comment": "balances from winter 2006 on, so each starts inside a run from 1 Oct 2005"}, time_zone="dates only", cell_methods="time: sum")
print(len(k), "balances from", b[k[0]])
