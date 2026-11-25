#!/bin/bash
# After lemon_snow.sh and stream_kge75.sh end: multi-calib fd892832 (advective heat) built in summa_adv, lemon_grus_snow rebuilt and spun up with it (old inputs kept as summa_inputs_bf5ddb11).
cd "$(dirname "$0")/../.."; W=$PWD; S=$(cd ..; pwd); L=$W/runs/logs/2026-11-25; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH
while pgrep -f "scratch/2026-11-25/lemon_snow.sh|scratch/2026-11-25/stream_kge75.sh" > /dev/null; do sleep 60; done
echo "start $(date)"
[ -d $S/summa_adv ] || git -C $S/summa worktree add --detach $S/summa_adv fd892832 > $L/adv_worktree.log 2>&1 || { echo "worktree failed"; exit 1; }
rsync -a $S/summa_next/external/ $S/summa_adv/external/
cd $S/summa_adv && mkdir -p build/cmake_build_mizu && (nice -n 5 env FC=/opt/local/bin/gfortran LIBRARY_LINKS=-llapack SUNDIALS_DIR=$S/sundials/instdir/ cmake -S build -B build/cmake_build_mizu -DUSE_SUNDIALS=ON -DUSE_MIZUROUTE=ON -DUSE_MPI=ON -DUSE_TOML=ON -DCMAKE_BUILD_TYPE=Release &&
  nice -n 5 env FC=/opt/local/bin/gfortran LIBRARY_LINKS=-llapack SUNDIALS_DIR=$S/sundials/instdir/ cmake --build build/cmake_build_mizu --target all -j 4) > $L/adv_build.log 2>&1 || { echo "build failed"; exit 1; }
[ -x bin/summa_sundials_mizuroute_opt.exe ] && [ -x bin/summa_sundials_mizuroute.exe ] || { echo "no executable"; exit 1; }
cd $W; cp -Rp runs/lemon_grus_snow/summa_inputs runs/lemon_grus_snow/summa_inputs_bf5ddb11
python build_cases.py cases.yaml lemon_grus_snow > $L/adv_build_case.log 2>&1 || { echo "case build failed"; exit 1; }
cd runs; SUMMA_DIR=$S/summa_adv OMPI_MCA_mpi_yield_when_idle=1 nice -n 5 python spinup.py lemon_grus_snow > $L/adv_spinup.log 2>&1 || { echo "spin-up failed"; exit 1; }
echo "lemon_adv done $(date)"
