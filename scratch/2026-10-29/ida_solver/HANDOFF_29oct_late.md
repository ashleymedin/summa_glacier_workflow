# Handoff, 29 Oct 2026 (late): debris baseflow fix and psi = 0 smoothing

Scratchpad worktrees (session 013bfce6, may be cleared): S=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/013bfce6-1e93-4f31-97f7-8d26c282aa89/scratchpad
Branches live in the summa repo, so they survive the scratchpad.

## Done
- **Dry-debris BE abort: fixed**, branch `debris-baseflow`, commit f2cd9285 (off multi-calib 97f7a3af).
  groundwatr.f90 used fieldCapacity_use = 0 over glacier ice, so lateral flow drained soil below theta_res;
  VG cannot release that water, so the solver took it from the storage term and psi ran to -1e7 m.
  Threshold is now theta_res per layer. No changelog entry (post-V3 glacier code).
  - Wolverine BE 8 trials: pass; CPU 1221 s vs 1211 s (multi-calib). Discharge obj <= 1.4e-4, stream temp ~0.01, MB 0.06/~900.
  - Wolverine IDA 8 trials: pass; CPU 3507 s vs 3367 s (+4%, machine shared with another session's benchmarks; recheck quiet).
  - Min head in the 2 cm debris layers: -5e7 m -> -7 m.
  - The retention-curve dry-end extension is not needed (not built).
- **Bow BE trial 15 was a smoothing-branch bug, not the scalar fallback** (baseline passes those exact params).
  opSplittin.f90:823 turns soil states into iname_lmpLayer in the mass split, so the lmpLayer branches are live.
  Fix on `psi-smooth` ff3212d5: liquid head = unsmoothHead(VG^-1(Se_liq)); lmp effSat = volFracTot(psiLiq,a,0,1,n,m);
  dIce/dPsiLiq = availPore^2/(liq-res)*dVolFracTot_dPsi(psiLiq,a,0,1). FD check all ratios 1 (scratchpad fdchk.f90). Trial 15 now passes.
- Combined branch `psi-smooth2` = f2cd9285 + 92ccc687 (smoothing) + 15511ef7 (liquid-head fix); convertEnthalpyTemp conflict with
  97f7a3af resolved (volFracWat0 else-branch uses volFracTot; diff_H_soil takes volFracWat from vec(10)).

## Open
1. **psi-smooth2 Wolverine IDA calibration run (sm2_wol) ran 88 CPU-min per rank without finishing a trial; killed.**
   Rank logs are 4 KB-buffered, so "2016-04-15" in them means nothing. Single-process default spinup to 2016-04-20
   passes in 85 s (same as bf). Running when stopped: spinrun.py bfy / sm2y to 2016-10-01 (spin_bfy, spin_sm2y here) to see
   whether the stall is later in the spinup or in the trials. If the spinup passes, rerun the trial params (spinup restart
   with -r e, then trial params) to find the stalling trial. Suspect the new liquid-head definition under IDA (liquidHeadPrime).
2. queue_sm2.sh continues with sm2_wol_be, then Bow BE/IDA b0 vs sm2 (48 trials). Compare with cmp_objectives.py
   (use /Users/amedin/miniconda3/envs/glacier/bin/python).
3. Put f2cd9285 on multi-calib after a quiet-machine IDA CPU check (bf_wol vs b0_wol).
4. Then psi-smooth2 onto multi-calib with a "-" changelog entry (changes BE solution).
5. Handoff items 2-4 from the plan doc (freezing-onset smoothing, energy relTol 0, sampled first generation at absTol 1e-4) untouched.
6. Old worktrees wroot/wadapt/wbrent (session b2242790) still need `git worktree remove --force` by the user.
