# Summer melt deficit: cause and fix (17 Nov 2026)

Answer to `../paper1/melt_deficit_handoff.md`. All runs are default parameters from each case's spun-up
`coldState.nc`, 2004-10 to 2024-09, scored with `exp.py stakes` (stake_seasons.py's method). Run outputs in
`runs/` are not committed.

## Cause

The turbulent heat over glacier ice is too small, for two reasons in the code:

1. **Louis (1979) stable correction.** Over melting ice the air is always stable, and (1 + 4.7 Ri)^-2 cuts the
   flux hard. Because Ri ~ z dT / U^2, the 0.59 wind factor cuts sensible heat by about two-thirds, not 41 %.
   `siteb_closure.py`: Site B, ice exposed 19 Jul to 20 Aug 2024. The stake melt (136 W m-2) minus the AWS net
   shortwave (76) and LWnet (-5) needs 65 W m-2 of turbulent heat. A bulk flux from the AWS's own 2 m wind,
   temperature and humidity gives 38 with Louis, 52 with Mahrt (1987), 55 with no stability correction. This
   uses no glacier factors and no forcing wind.
2. **Measurement height on the glacier.** Glacier domains took the HRU's mHeight, set from vegetation. Since the
   WorldCover change (13 Nov) the lowest HRU has 3.5 m, so its glacier air sat 3.5 m up (more stable, smaller
   C_H). The glacier factors map the forcing to the on-ice air at Site B, measured at 2.0 m (T) and 2.3 m (wind)
   (campaign README).

These two account for most of the deficit. The wind and cooling factors themselves check out against the 2024 AWS
(`siteb_forcing.py`). Glacier air temperature is within 0.3 K in Jun–Aug. Wind times T above 0 °C is about
20 % low, though it varies month to month.

Albedo is a feedback, not a separate cause. With too little melt, Gulkana HRU 2 built up 1.5–2.4 m w.e. of
permanent firn, so its surface kept the snow albedo all summer (0.69–0.77 in Jul–Aug 2024 against 0.55–0.60 at
Site B). Once the melt is fixed, the HRU 2 firn melts out in most summers.

## Fix (SUMMA branches, not merged; worktrees beside summa)

- `glacier-meas-height` (0b318918, worktree `summa_measheight`): glacier domains use a 2 m measurement height.
- `glacier-mahrt` (bffb03b4, worktree `summa_mahrt`, on top of the first): the ground stability function is Mahrt (1987) for
  glacier and lake snow and ice (the surfaces that already take the Andreas scalar roughness). The case decision
  `astability` is unchanged, so upland snow is unaffected. Switching the decision to `mahrtexp` gives the same glacier
  result but moves upland melt-out by up to ~10 days.

## Summer balance bias, sim − obs (m w.e.), HRU 1 / 2 / 3

| run | Gulkana added | Wolverine added |
|---|---|---|
| base, WY2006–15 | +1.67 / +0.64 / +0.97 | +1.53 / +0.27 / +0.55 |
| fix, WY2006–15 | +0.73 / +0.26 / +0.85 | +0.20 / −0.04 / +0.36 |
| base, WY2016–24 | +0.80 / +0.54 / −0.16 | +1.97 / −0.47 / −0.17 |
| fix, WY2016–24 | −0.18 / +0.21 / −0.18 | +0.57 / −0.86 / −0.44 |

The winter balances do not change. HRU 1's stakes sit below its glacier domain (about 50 m at Gulkana, 150 m at
Wolverine), and stake_seasons.py does not carry the summer balance to the stake. That alone makes HRU 1 look about
0.35 m (Gulkana) and 0.7 m (Wolverine) short, so the fixed HRU 1 values are close to zero.

Sensitivities, one change each (`batch1.sh`, `batch2.sh`): albedoDecayRate 0.3e6 helps all HRUs (it overshoots HRU 2
when combined with the fix). albedoMinSpring 0.45 helps a little. albedoRefresh 10 makes the deficit worse.
glacierWindFactor 1 is about as strong as the fix but was not tried as one, per the handoff.

## What is left

- **Gulkana HRU 3 (+0.85 in calibration years):** summer snowfall. May–Sep glacier snowfall is 1.03 m w.e. at HRU 3
  and 0.50 at HRU 2, against a 1.27 winter balance at HRU 3. The stake-fitted frozenPrecipMultip (1.45 at HRU 3)
  multiplies summer snow, but not summer rain at the same site. Not touched.
- **Albedo decay:** the Site B daily albedo decays with an e-folding time of about 2–6 days after summer snowfalls
  (1.7–4.8e5 s), the low end of the search range (3e5). Gulkana's calibration sat near that end. A lower bound of
  1e5 is supported if the search needs it.
- **General (ERA5) cases:** the summer deficit is only at HRU 1 there. HRU 2–3 already melt too much, with winter
  balances far off (Gulkana general 0.4–0.5 m low, Wolverine general HRU 1 +1.1 m). The fix brings HRU 1 within
  ~0.9–1.1 m, partly the stake-elevation artefact. Their problem is the snowfall distribution, which the calibration
  searches.
- Gulkana HRU 3's 2016–24 winter value (+1.5) is an artefact. The 2024 firn-to-ice conversion of 20 m w.e. breaks
  the counter differencing, so ignore that cell.

## Follow-up on what is left (batch7.sh)

Summer balance bias with the fix (`gmahrt`), m w.e., HRU 1 / 2 / 3:

| run | Gulkana WY06–15 | Gulkana WY16–24 | Wolverine WY06–15 | Wolverine WY16–24 |
|---|---|---|---|---|
| fix | +0.73 / +0.26 / +0.85 | −0.18 / +0.21 / −0.18 | +0.20 / −0.04 / +0.36 | +0.57 / −0.86 / −0.44 |
| + glacier multiplier off May–Aug | +0.83 / +0.18 / +0.62 | −0.12 / +0.16 / −0.21 | +0.20 / −0.13 / +0.09 | +0.56 / −0.97 / −0.70 |
| + albedoDecayRate 5e5 | +0.56 / −0.13 / +0.68 | −0.35 / −0.03 / −0.22 | +0.05 / −0.26 / +0.14 | +0.41 / −1.04 / −0.65 |
| + albedoDecayRate 2e5 | +0.35 / −0.58 / +0.43 | −0.57 / −0.31 / −0.28 | −0.14 / −0.51 / −0.13 | +0.25 / −1.25 / −0.87 |

- **Summer glacier snowfall multiplier.** The stake ratio is fitted on fall-to-spring snowfall only (stake weight 0 in
  May–Aug in corrections.csv), but as frozenPrecipMultip it multiplies glacier snow in every month. The multiplier
  adds 319 mm/yr of May–Sep snowfall at Gulkana HRU 3 and 366 at Wolverine HRU 3. A throwaway build that applied it
  only in Sep–Apr (`merge(1, frozenPrecipMultip, is_glac .and. jm>=5 .and. jm<=8)` in derivforce; worktree
  removed) moves Gulkana HRU 3 only 0.23 m, and makes Wolverine worse in the held-out years. So it is not the main
  cause of the HRU 3 residual. The rain–snow phase is not the cause either: it is already taken from the uncooled
  forcing air, and the JJA lapse rate (−7.3 to −7.9 K/km between stations) matches ERA5's free air.
- **Albedo decay.** At 2e5 s the model reproduces the July–August 2024 Site B albedo (0.57 against 0.58/0.59;
  `siteb_run.py`). At 1e6 s it stays at 0.69–0.74. But at 2e5 the HRU 2 stakes over-melt by 0.3–0.6 m (Gulkana) and
  0.5–1.25 m (Wolverine), so another error is being offset at that HRU. The Site B data support a search lower bound
  of 2e5 (now 3e5). I would widen it rather than fix a value.
- **Discharge at calibrated trial 450 (gulkana_added), fixed binary, parameters unchanged**
  (`runs/gulkana_added/calibration_rerun/sample_450_fix`): r 0.90→0.91, α 0.76→0.82, β 0.78→0.84, KGE about
  0.66→0.74. About a quarter of the volume deficit closes before any recalibration.
- **General cases: the cause is the precipitation gradient, not melt.** Oct–Apr glacier snowfall from HRU 1 to HRU 3
  rises ×1.2 (Gulkana general, 359→433 mm) and ×1.3 (Wolverine general, 2088→2703). The stakes rise ×2.6 and ×3.3,
  and the added cases ×2.4 and ×3.0. CHELSA's precipElevGrad (0.000202, 0.000076 m-1) is about a tenth of the stake
  fit (0.0019, 0.00175). One frozenPrecipMultip@glacier cannot fix the shape: Wolverine general's HRU 1 winter is
  +1.1 m and Gulkana general's HRU 2–3 are −0.6 to −0.9 m. The HRU 2–3 summer over-melt follows from the thin
  winter snow. The general setup needs a better global gradient than CHELSA's at this scale. Searching
  precipElevGrad is the decision already taken against.
- **2024 at Site B is still short** even with decay 2e5 (B −2.0 against −3.8 m w.e.). The HRU 2 domain sits at 1770 m,
  between B (1682) and D (1843), and starts 2024 with firn under the snow. One summer is not enough to diagnose
  this further.

## Files

- `exp.py`: one-change experiment driver (params, attributes, decisions, forcing; `SUMMA_DIR` picks the binary).
- `siteb_forcing.py`, `siteb_closure.py`, `siteb_run.py`: Site B 2024 checks.
- `batch1.sh` … `batch6.sh`: the runs above.
