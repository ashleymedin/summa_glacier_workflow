#!/bin/bash
# Round 10b: wolverine_added_10b and gulkana_added_10b (no rain rise, no upland snow rise; prep.sh) on round 10's code (summa_r10, 9f34c049), seeds 42 and 43, 32 x 15, then each evaluated.
# Starts once round 10 has only its added cases left: no general calibration runs, nor (for up to 2 h after) a general post_merge.
cd "$(dirname "$0")/../../../runs"
export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python; export PY L=logs/2026-11-26r10b
up() { ps -axo command | grep -E "^[^ ]*(python|Python)[^ ]* $1" > /dev/null; }
while up 'calibrate\.py calibrate (wolverine|gulkana)_general '; do sleep 120; done
for i in $(seq 60); do up '[^ ]*post_merge\.py (wolverine|gulkana)_general ' || break; sleep 120; done
echo "start $(date)"
for c in wolverine_added_10b gulkana_added_10b; do $PY spinup.py $c > $L/spin_$c.log 2>&1 < /dev/null && touch $L/ready_$c || echo "$c spin-up failed"; done
calibrate() {
  [ -e $L/ready_$1 ] || return
  case $2 in 42) n=calibration;; *) n=calibration_s$2;; esac
  $PY calibrate.py calibrate $1 --search domain --population 32 --generations 15 --ranks 4 --seed $2 --name $n < /dev/null > $L/calibrate_$1_$n.log 2>&1 || { echo "$1 $n calibration exited $?"; return; }
  $PY calibrate.py evaluate $1 --name $n --ranks 2 --jobs 2 < /dev/null > $L/evaluate_$1_$n.log 2>&1 || echo "$1 $n evaluation exited $?"
  echo "$1 $n done $(date)"
}
export -f calibrate
printf "%s\n" "wolverine_added_10b 42" "gulkana_added_10b 42" "wolverine_added_10b 43" "gulkana_added_10b 43" | xargs -P 2 -L 1 bash -c 'calibrate $0 $1'
echo "round 10b done $(date)"
