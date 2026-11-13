#!/bin/zsh
# Wolverine trial 459 on wolverine_stream_delta with the reach falling today's 206 m from the ice front to the gauge
# (terminus_length.py) over the whole run, not the modelled front's fall: what the delta and lake reach once the retreat
# is right. topology.nc slope is set to 206/2100 for the run and put back after. Needs SUMMA_DIR set to a build of wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
c=wolverine_stream_delta
cp $c/topology.nc $c/topology_keep.nc
$PY -c "
import netCDF4 as n
d = n.Dataset('$c/topology.nc', 'a'); d['slope'][:] = 206/2100; d.close()"
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarStreamLatInflowTemp
   --extra scalarWetlandFullArea --extra basin__TerminusElev --extra wetlandChainFlow)
$PY rerun_trials.py $c calibration_added 459 $X --set reachOutletElev=0 --label delta_drop > ../scratch/2026-11-13/w_delta_drop.log 2>&1
mv $c/topology_keep.nc $c/topology.nc
