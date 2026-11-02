# Handoff, 2 Nov 2026: psi-smooth2 IDA stall found and fixed (branch psi-smooth3)

Worktree (session 57e7be7a, may be cleared): S=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/57e7be7a-58e3-446d-b540-98d5dbb59ca8/scratchpad/wsm3
Branch `psi-smooth3` lives in the summa repo = psi-smooth2 (15511ef7) + e81c8aba.

## Done
- **Cause of the sm2 Wolverine IDA stall.** It isn't a hang. From about 2016-07-18, IDA steps in the glacier-ice
  domain of hru 5 and 6 (dom 3) go from ~700/day to >100k/day; other domains unchanged. Those soil layers are ice
  (ice fraction 0.90-0.98, no liquid), total head 80-1500 m in both bf and sm2. With the hyperbolic smoothing,
  theta(psi) at those heads differs from theta_sat by ~1e-15 (6 distinct floats over psi = 80-100 m), and the liquid
  head from unsmoothHead amplified that round-off into metre-scale jumps.
- Compact smoothing alone made it worse: the liquid head was pinned at s above s, so there was no restoring force and
  heads in ice drifted to 1.2e6 m (stall by 2015-10-10).
- **Fix e81c8aba** "Compact psi = 0 smoothing; liquid head tracks the total head above psiSmooth":
  smoothHead exactly psi below -s, 0 above s, quadratic between; liquid head = unsmoothHead(VG^-1(Se)) + max(psi-s,0);
  lmp reconstruction sets total = liquid head when the liquid head >= psiSmooth (updatDiagn, updatDiagnWithPrime,
  eval8summa imposeConstraints). FD check (fdchk.f90 in the session scratchpad): all ratios 1.
- Wolverine default IDA spinup to 2016-10-01, one process: sm3 148 s = bf 148 s (sm2 > 1500 s). Steps 3,129,088 vs
  3,129,808, every domain within 0.3%; glacier-domain heads, runoff, SWE and glacier storage match bf.
- Scripts: spinrun.py (2026-10-29) paths moved to gulkana_wolverine_run, optional 5th arg `diag` writes hourly
  per-domain steps and soil states (use the non-opt exe; _opt needs >= 2 ranks). tolall.py (2026-10-28) Wolverine
  now uses tolall_bf_wol/config.toml, because wolverine_run was removed and gulkana_wolverine_run is a different calibration.

## sm3 calibration comparison (queue_sm3.sh, 0 failed in all four)
- Wolverine IDA 8 trials: CPU 3285 s vs bf_wol 3507 s; discharge <= 1e-7, stream temp <= 2e-6, mass balance <= 4e-5.
- Wolverine BE 8 trials: 1145 s vs bf_wol_be 1221 s; discharge <= 6e-7, mass balance <= 2e-3.
- Bow BE 48: 318 s vs b0 319 / sm2 326; vs b0 median 0, max 6e-5; vs sm2 max 8e-4.
- Bow IDA 48: 519 s vs b0 522 / sm2 516; vs b0 identical (47 shared); vs sm2 max 0.012.
- Baselines are from 29 Oct, so CPU is not a paired measurement.

## Open
1. Done (above).
2. Put f2cd9285 on multi-calib after a quiet-machine IDA CPU check (bf_wol vs b0_wol).
3. Then psi-smooth3 (92ccc687 + 15511ef7 + e81c8aba) onto multi-calib with one "-" changelog entry.
4. Plan-doc items untouched: freezing-onset smoothing, energy relTol 0, sampled first generation at absTol 1e-4.
5. Old worktrees wroot/wadapt/wbrent (session b2242790) still need `git worktree remove --force` by the user.
