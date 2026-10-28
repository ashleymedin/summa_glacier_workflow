Row 2 (Mualem K near saturation) and row 7 (macropore ramp) ensembles and the glacier-areas profile, summa solver slowdown plan, 29 Oct 2026.

- ensemble.py   perturbed single-process Wolverine runs; reports CPU time (wall time is wrong when the Mac suspends jobs). EXTRA=name=val,... adds --param overrides
- queue_row7.sh, queue_row2_7.sh, queue_air.sh   the variant queues (paths point at the session scratchpad worktrees wbase and wair)
- profile.py    periodic `sample` of a running case, inclusive samples per libsumma routine
- daytimes.py   seconds per simulated day; run the case with GFORTRAN_UNBUFFERED_ALL=y or the log is block-buffered
- wolida4/, tol_t4j/   case config, cold state and inputs copied from the 27 Oct scratch
