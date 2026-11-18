#!/bin/zsh
# The delta case with bedrock layers, as the other stream cases: the decision flipped in its round-3 inputs (a rebuild would
# take the parent's round-4 inputs), spun up again from its cold state, and trial 405 rerun; the bedrock-off run is kept.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
export OMPI_MCA_mpi_yield_when_idle=1
set -e
C=wolverine_stream_delta
sed -i '' 's/^deepTherml\( *\)none           /deepTherml\1bedrockLyrs    /' $C/summa_inputs/modelDecisions.txt
grep -q '^deepTherml *bedrockLyrs' $C/summa_inputs/modelDecisions.txt
R=$C/calibration_r3_rerun
[[ -d $R/sample_405_delta_nobedrock ]] || { mv $R/sample_405_delta $R/sample_405_delta_nobedrock; mv $R/sample_405_delta_settings $R/sample_405_delta_nobedrock_settings; }
$PY spinup.py $C > logs/spinup_${C}_bedrock.log 2>&1
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow)
$PY rerun_trials.py $C calibration_r3 405 $X --label delta > ../scratch/2026-11-19/w_delta_bedrock.log 2>&1
echo done
