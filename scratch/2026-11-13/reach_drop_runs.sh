#!/bin/zsh
# The reach falling as far as the stream now does from the ice front to the gauge (terminus_length.py): Wolverine 206 m
# (the front above the lake since 2016) and Gulkana 100 m (2005-2016), against 63 and 36 m in the stream cases, so the
# friction heat is the drop's. The cases' topology.nc slope is set to 0.098 and 0.083 over the same lengths for these runs
# and put back after. Wolverine as the settling lake with fetch roughness, Gulkana as the fan whose area follows its flow.
# Needs SUMMA_DIR set to a build of wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
for c in wolverine_stream gulkana_stream; do cp $c/topology.nc $c/topology_slope003.nc; done
$PY -c "
import netCDF4 as n
for c, s in (('wolverine_stream', 206/2100), ('gulkana_stream', 100/1200)):
    d = n.Dataset(c + '/topology.nc', 'a'); d['slope'][:] = s; d.close()"
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarWetlandFullArea)
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set wetlandSedConc=0.00075 --set wetlandSettleVel=0.00001 --set lakeFetch=200 --label drop > ../scratch/2026-11-13/w_drop.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_added 451 $X --set wetlandMaxArea=40000 --set wetlandFlatArea=53000 --label drop > ../scratch/2026-11-13/g_drop.log 2>&1 &
wait
for c in wolverine_stream gulkana_stream; do mv $c/topology_slope003.nc $c/topology.nc; done
