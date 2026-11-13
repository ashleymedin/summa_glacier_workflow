#!/bin/zsh
# Wolverine trial 459 on wolverine_stream_delta with the reach falling today's 206 m (as delta_drop_run.sh) and the groundwater
# reaching the channel at the aquifer store's own temperature (deepTherml aquiferTemp), mixed toward its recharge's,
# instead of the base of the soil column: whether the warm October-November stream is the groundwater's temperature.
# The case's inputs are copied with that decision; topology.nc slope is set to 206/2100 for the run and put back after.
# Needs SUMMA_DIR set to a build of wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
c=wolverine_stream_delta
rm -rf $c/summa_inputs_aqT; cp -R $c/summa_inputs $c/summa_inputs_aqT
sed -i '' 's/^deepTherml  *none/deepTherml                      aquiferTemp/' $c/summa_inputs_aqT/modelDecisions.txt
grep -q "^deepTherml  *aquiferTemp" $c/summa_inputs_aqT/modelDecisions.txt || { echo "decision not set"; exit 1; }
cp $c/topology.nc $c/topology_keep.nc
$PY -c "
import netCDF4 as n
d = n.Dataset('$c/topology.nc', 'a'); d['slope'][:] = 206/2100; d.close()"
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarStreamLatInflowTemp
   --extra scalarWetlandFullArea --extra basin__TerminusElev --extra wetlandChainFlow --extra scalarAquiferTemp)
$PY rerun_trials.py $c calibration_added 459 $X --set reachOutletElev=0 --inputs $c/summa_inputs_aqT --label aqT > ../scratch/2026-11-13/w_aqT.log 2>&1
mv $c/topology_keep.nc $c/topology.nc
