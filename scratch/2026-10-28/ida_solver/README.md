IDA solver slowdown tests (summa plan "SUMMA solver slowdown plan"), 28 Oct 2026.

- plainrun.py   single-process gulkana_wolverine run with sampled parameter values via --param (reproduces calibration traps in 3-10 min; derived-parameter handling may differ slightly from a calibration trial)
- ensemble.py   perturbed copies (k_soil x 1 +/- 1e-4..2e-3) of sampled parameter sets, CPU-time cap; run under caffeinate -i
- tolrun.py     calibration first generation (16 trials, 5 ranks) at a given absTol for Matric, Aquifr, WatVeg
- runvar.py, tolarg.py   run variants with edited localParamInfo rows (12-character column format)
- rank_trials.py   rank calibration trials by dispatch/completion time
- fd_iceimpede.py  60-digit check of the ice-impedance derivative
- diag3.patch   temporary diagnostics for build/source/engine/summaSolv4ida.f90 (IDADIAG, IDAWIN, YSEQ, COEFNL); apply to a copy, never commit
Paths inside refer to the session scratchpad and need editing before reuse. The Mac suspends idle jobs: use caffeinate -i and judge cost by CPU time or step counts.
