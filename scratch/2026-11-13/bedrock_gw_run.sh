#!/bin/zsh
# Wolverine trial 459 on wolverine_stream_delta with thermal-only bedrock below the soil (deepTherml bedrockLyrs, to 30 m),
# so groundwater reaches the channel at the bedrock base's temperature instead of the shallow soil base's, which is
# 4-5 °C in October-November. On the attributes of sample_459_delta (before the WorldCover vegetation of 13 Nov), with
# the connected-body front. Needs SUMMA_DIR set to a build of wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
c=wolverine_stream_delta
rm -rf $c/summa_inputs_bedrock; cp -R $c/summa_inputs $c/summa_inputs_bedrock
cp $c/calibration_added_rerun/sample_459_delta_settings/attributes.nc $c/summa_inputs_bedrock/
sed -i '' 's/^deepTherml  *none/deepTherml                      bedrockLyrs/' $c/summa_inputs_bedrock/modelDecisions.txt
grep -q "^deepTherml  *bedrockLyrs" $c/summa_inputs_bedrock/modelDecisions.txt || { echo "decision not set"; exit 1; }
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarStreamLatInflowTemp
   --extra scalarWetlandFullArea --extra basin__TerminusElev --extra wetlandChainFlow --extra scalarAquiferBaseflow)
$PY rerun_trials.py $c calibration_added 459 $X --inputs $c/summa_inputs_bedrock --label bedrock > ../scratch/2026-11-13/w_bedrock.log 2>&1
rm -rf $c/summa_inputs_bedrock
