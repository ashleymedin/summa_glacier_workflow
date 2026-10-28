#!/bin/bash
# run experiments with the diagnostic worktree build (EXE overridable)
EXE=${EXE:-/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/f086393c-9d14-4737-9891-bc36408ba0a4/scratchpad/wtd/bin/summa_sundials_mizuroute_opt.exe}
cd "$(dirname "$0")/../exp"
for e in "$@"; do
  ( SUMMA_DEBRIS_DIAG=$PWD/$e/grids mpirun -np 2 $EXE -c $PWD/$e/config.toml > $e/run.log 2>&1; echo "$e exit $?" ) &
done
wait
