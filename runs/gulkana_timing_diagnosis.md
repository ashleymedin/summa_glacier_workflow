# Gulkana discharge: why the model peaks in June and misses the late-summer floods

Diagnosis only; nothing was recalibrated. Analysis scripts, figures and short experiments are in
`runs/gulkana_timing_diagnosis/`. The scripts are in `scripts/` and the SUMMA experiments in `exp/`.

**Inputs used.** Everything here uses the **old** inputs, HRUarea summing to 26.62 km². These are the daily
reruns `gulkana_corrected/calibration_rerun/sample_{451,411}` and `gulkana_raw/pilot_rerun/sample_189`. The
experiments in `exp/` copy the pinned `sample_451_settings` (old `attributes.nc` and `coldState.nc`) and use
the frozen executable `summa_frozen_cal_20261016`. They run with a 2008 spin-up over 2009–2014 and are scored
over 2010–2014. E0 reproduces the rerun of 451 exactly over 2010–2014. Where I write "×1.156", I have scaled
the simulated flow by the area fix (30.77/26.62) after the run.

## Summary, ranked by evidence

| # | Mechanism | Evidence | Share of the problem |
|---|---|---|---|
| 1 | **Summer rain is missing from the forcing.** The station correction scales only snowfall, so June–September precipitation is raw ERA5. ERA5 has no elevation gradient across the HRUs and is about half the gauged rain. | On days both gauges report, July–August precipitation is 413 mm at the 1480 m gauge and 545 mm at the 1725 m gauge, against 235 mm in the forcing (raw = corrected). On 2–7 Aug 2018 the gauges record 198–326 mm and the forcing has 78 mm. In experiment E3 (June–September precipitation ×1.9) the July–August ratios rise from 0.80/0.68 to 0.88/0.80, September from 0.65 to 0.92, KGE from 0.63 to 0.74, and Bw from 727 to 838 mm (850 observed). | All of the missing rain floods. About half the July–August volume gap. With the area fix as well, the monthly ratios are 1.03 / 1.02 / 0.92 for June / July / August. |
| 2 | **The search compensates in the albedo.** Snow is made too dark and bare ice is too bright, so melt arrives as early snowmelt instead of late ice melt. | albedoMax is 0.71 in trial 451; fresh snow at Site B measures 0.85–0.90. albedoDecayRate sits at its 1.2 d lower bound, while Site B snow stays at 0.61–0.70 until ice exposure about 20 July. Ice albedo is fixed at 0.50 broadband (default albedoFrznWat 0.6/0.4); Site B ice measures 0.41–0.52, and ice lower down is darker. In the model, exposing ice drops albedo by about 0.05; on the glacier the drop is about 0.2. Model glacier mass change by month: Jun −548, Jul −689, Aug −385, Sep +24 mm. | Sets the June/July–August split. E2 (darker ice) lifts July–August. E4 (darker ice plus default snow albedo) swings the ratio to Jun/JA 0.55, too late, and the volume falls. |
| 3 | **Debris cover runs away.** The debris domain grows from 10% of the glacier to 86–97%. | The debris domain is 1.76 km² at the start and 13–16 km² by 2013–2016 (trial 411 reaches 78% by 2021). In July–August, melt under debris is 15–22 mm/d against 25–37 mm/d on the clean domains. E1 (no debris evolution): June 0.93 → 0.85, August 0.68 → 0.74, Jun/JA 1.26 → 1.10, but Bs −1839 → −2033 mm. | Moderate timing effect. It also biases every calibrated melt parameter. |
| 4 | **The routing compensates, and wrongly.** It delays the upland water by about 1.5 months. | routingGammaScale is 2.0–2.7e6 s with shape 2.0–2.07, so the mean delay is 47–64 days. The 83-day histogram (nTimeDelay = 2000 h) is cut off and renormalised: trial 451 keeps only 73% of the distribution, and run.log prints the WARNING. The search does not sharpen the routing. It smears upland snowmelt from June into July–September. Glacier runoff bypasses this routing (qGlacier). | Hides some of the June excess. With physical routing (under a day for 31 km²), June would be worse. |
| 5 | **No slow storage.** | Winter flow from November to April is 0.10–0.19 m³/s observed and 0.01–0.08 simulated (ratio 0.1–0.4). aquiferBaseflowRate is 1e-8 to 1.5e-3, and k_soil is near its lower bound. | Small: about 2% of the volume. It is a structural signal, not the timing cause. |

**Short answer.** The early peak is mostly the calibration's response to missing water. The forcing has about
half the gauged summer rain, and the basin area is 13.5% short. The only levers that add runoff are melt
parameters. The search darkens snow (albedoMax 0.71, fastest decay) and cuts snowfall. That adds water, but in
June, because the model's bare ice is barely darker than its old snow. The runaway debris cover then suppresses
July–August ice melt. Fix the summer precipitation and the area first: in E3 they bring the monthly volumes to
within about 10% without retuning. Then recalibrate with albedo bounds tied to the Site B record.

## 1. Which flux is early?

Trial 451, monthly means over gauged days 2009–2022, in m³/s, before the area fix. The glacier columns are
unrouted inputs; "glacier routed" is the output of the three linear reservoirs.

| Month | Gauge | Sim | Sim ×1.156 | Glacier routed | Upland routed | Glacier melt, snow-covered domains | Glacier melt, bare domains | Upland snowmelt (est.) | Rain, glacier | Rain, upland |
|---|---|---|---|---|---|---|---|---|---|---|
| May | 0.86 | 0.83 | 0.96 | 0.72 | 0.11 | 0.95 | 0.00 | 0.86 | 0.10 | 0.08 |
| Jun | 5.20 | 5.50 | **6.36** | 4.88 | 0.62 | **3.95** | 0.27 | 1.19 | 0.53 | 0.33 |
| Jul | 10.32 | 6.79 | **7.85** | 5.69 | 1.10 | 3.01 | 1.91 | 0.25 | 0.63 | 0.36 |
| Aug | 8.55 | 4.72 | **5.46** | 3.87 | 0.85 | 1.94 | 1.26 | 0.03 | 0.72 | 0.44 |
| Sep | 2.46 | 1.73 | 2.00 | 1.31 | 0.42 | 0.84 | 0.14 | 0.08 | 0.53 | 0.35 |
| Year | 2.43 | 1.71 | 1.98 | 1.40 (82%) | 0.31 | 0.90 | 0.30 | 0.25 | 0.23 | 0.15 |

Trials 411 and 189 have the same shape (scripts/monthly.py prints all three).

- **June excess** (+1.2 m³/s after the area fix). The early flux is **snowmelt**. Melt from snow-covered
  glacier domains peaks in June at 3.95 m³/s, and upland snowmelt adds 1.19 m³/s. Bare-ice melt is only
  0.27 m³/s in June.
- **July–August deficit** (−2.5 and −3.1 m³/s after the area fix). Bare-ice melt peaks at only 1.9 m³/s in
  July. Rain over the whole basin is about 1.0–1.2 m³/s. The gap is about the size of the missing rain (§3)
  plus the weak ice melt.
- **Glacier balances.** Over 2009–2022, the model's winter balance is too small: 638 / 714 / 414 mm for
  451 / 411 / 189, against 855 mm observed. The summer balance is about right: −1718 / −1803 / −1548 mm,
  against −1819 mm observed. So the total melt is right, but it comes about a month early. Monthly glacier mass
  change for 451 is May −114, Jun −548, Jul −689, Aug −385, Sep +24 mm. The September gain is too early.
- **Snow-off dates.** Debris and upland domains become snow-free between late May (HRU 1) and July (HRU 2).
  The clean domains (types 2 and 3) are never snow-free: they keep 1–5 mm of SWE all summer, even at 1346 m.
  Their melt therefore always goes into the snow reservoir (k_snow 80–105 h), not the ice reservoir (11 h).
  Because SUMMA sets `scalarGroundSnowFraction` to 1 whenever a snow layer exists, the clean ice there may also
  keep the snow albedo.

Figure: `runs/gulkana_timing_diagnosis/monthly_sources_451.png`.

## 2. Melt energy or storage?

Mostly **melt energy**, plus the missing rain. It is not routing.

- **Albedo.** Site B (1682 m, Wilson et al. 2024 daily albedo, `Wilson_gulkana_2024_data/5_albedo`) measures:
  - snow at 0.73–0.90 in May and 0.61–0.70 from mid-June to 20 July;
  - ice from 20 July onwards at 0.41–0.55, with fresh-snow resets to 0.75–0.88.

  The model, by comparison:
  - snow decays from albedoMax 0.71 (451) toward albedoMinSpring 0.55 with a 1.2-day time constant, so it
    sits near 0.55 through June, about 0.1 too dark;
  - ice is 0.5·0.60 + 0.5·0.40 = 0.50, so exposing ice adds almost no energy.

  This is why June runs high and July–August low, even though the summer balance matches.
- **Transient snowline.** Each domain is snow-covered or bare as a whole: there is no fractional snow cover, and
  a domain loses its snow only when its whole snowpack melts. With three HRUs, each with up to three glacier
  domains, the model's ice exposure is lumpy. In 2013+ it is almost entirely the debris domain.
- **Storage and routing.** Glacier water already passes through three linear reservoirs (qGlacier: ice
  11–12 h, snow 3.3–4.4 d, firn 26–31 d calibrated). In the Aug 2018 events, the simulated peaks fall on the
  same days as the observed peaks (`aug2018_event.png`), so the timing of the response is fine; the magnitude
  is not. Longer reservoirs cannot produce the July–August volume, because the June surplus (about
  +1.2 m³/s for a month) is less than half the July–August deficit (about −2.8 m³/s for two months).
- **Upland routing.** As table row 4 shows, the search delays the upland water 47–64 days with a truncated
  histogram. Physical routing would make June worse, not better.

## 3. Why the August rain floods are missing

The forcing has a fraction of the rain. Precipitation from the USGS tipping-bucket gauges (Precip_TPG in
`Input_Gulkana_Daily_Weather.csv`) against forcing, on days both gauges report (2011–2022):

| | 1480 m gauge | 1725 m gauge | Forcing HRU 1 / 3 / 2 (raw) | Forcing HRU 1 / 3 / 2 (corrected) |
|---|---|---|---|---|
| Jun–Sep (mm per season) | 617 | 725 | 382 / 385 / 382 | 389 / 452 / 484 |
| Jul–Aug (mm per season) | 413 | 545 | 234 / 235 / 234 | 234 / 236 / 235 |
| Oct–May (mm) | 460 | 426 | 301 | 401 / 732 / 782 |
| Jun–Sep 99th-percentile day (mm) | 46.9 | 64.7 | 21.3 | 21.3 / 28.2 / 32.0 |

| Event | 1480 m | 1725 m | Forcing (any HRU) | Gauge peak | Sim peak (451, ×1.156) |
|---|---|---|---|---|---|
| 2–7 Aug 2018 | 198 mm | 326 mm | 78 mm | 69.9 m³/s (6 Aug) | 12.7 m³/s |
| 12–16 Aug 2018 | 146 | 206 | 56 | 28.6 | 8.9 |
| 20–24 Aug 2018 | 118 | 205 | 68 | 38.2 | 9.8 |
| 18–21 Aug 2013 | 186 | n/a | 76 | 26.4 | 6.5 |
| 22–25 Jul 2016 | 103 | 120 | 32 | 28.3 | 6.5 |

- About 300 mm of runoff over the basin is needed to make the 5–7 Aug 2018 hydrograph. The 1725 m gauge
  caught 326 mm. The forcing gives 78 mm, so the model cannot make that flood.
- **The correction leaves summer alone.** Raw and corrected summer precipitation are identical except in stake
  intervals that reach into September. The correction moves snow into the winter at HRUs 2 and 3, which is
  then partly undone by frozenPrecipMultip 0.69. ERA5 carries no orographic gradient: raw HRUs 1, 2 and 3 are
  equal.
- **Rain/snow partition.** It is not the issue. During 2–6 Aug 2018 the hourly air temperature was 3.4 / 5.3 /
  8.7 °C (HRU 2 / 3 / 1, minimum 1.7 °C), and tempCritRain is −0.75 °C, so all of it fell as rain.
- **Rain on ice and firn.** On bare ice, rain is part of `scalarGlacierMelt` and goes through the ice
  reservoir (k about 11 h) to the stream; nothing refreezes. On snow-covered glacier domains it drains through
  the snowpack into the snow reservoir (3–4 d). In the accumulation fraction it enters the firn reservoir
  (about 30 d), which damps it. The clean domains always keep a residual snow layer (§1), so their rain always
  takes the 3–4 d path. These effects damp the peaks somewhat, but the volume is missing either way.
- **Experiment E3.** June–September precipitation ×1.9 everywhere (`exp/forcing_JJAS_x1.9`):

| Run (2010–2014) | All | May | Jun | Jul | Aug | Sep | Jun/JA | KGE | Bw (obs 850) | Bs (obs −1740) |
|---|---|---|---|---|---|---|---|---|---|---|
| E0 baseline 451 | 0.75 | 0.73 | 0.93 | 0.80 | 0.68 | 0.65 | 1.26 | 0.63 | 727 | −1839 |
| E0 ×1.156 | 0.87 | 0.84 | 1.08 | 0.92 | 0.79 | 0.75 | | | | |
| E3 JJAS P ×1.9 | 0.86 | 0.67 | 0.89 | 0.88 | 0.80 | 0.92 | 1.06 | 0.74 | 838 | −1764 |
| E3 ×1.156 | **0.99** | 0.77 | **1.03** | **1.02** | **0.92** | **1.06** | | | | |

  With the area fix and a station-level summer rain, trial 451's parameters give the right volume and nearly
  the right seasonal shape. Both glacier balances also move toward the observations, because the late-summer
  snowfall at HRU 2 adds to Bw.

## 4. Structural gaps in the glacier model

Code: `summa/build/source/engine/qTimeDelay.f90` (qGlacier), `run_oneGRU.f90` lines 566–580 (reservoir
assignment) and `glacAreaChange.f90`.

- **A fast/slow glacier reservoir already exists.** qGlacier is a three-reservoir linear model (ice, snow,
  firn), as in Hock & Jansson (2005). Melt from the accumulation fraction (1 − ablFrac) goes to the firn
  reservoir. Melt from the ablation fraction goes to the snow reservoir if `scalarSnowDepth > 0`, otherwise to
  the ice reservoir. Glacier runoff bypasses the gamma routing. This structure is not what is missing.
- **Snow cover is all-or-nothing per domain.** `vegPhenlgy.f90` sets scalarGroundSnowFraction to 1 if
  nSnow > 0, so there is no subgrid snowline. Clean domains keep 1–5 mm of SWE all summer. Their melt and rain
  therefore never use the ice reservoir, and they may keep snow albedo. This is worth checking: is it a
  persistent thin layer from refrozen melt or summer snowfall, and should it count as snow for the reservoir
  switch and the albedo?
- **Bare-ice albedo is a constant shared with lake ice.** It is albedoFrznWatVisible/NearIR, uncalibrated, at
  0.6/0.4. There is no glacier-ice albedo parameter, and no dependence on dust or meltwater.
- **Debris evolution runs away** (`debris_area.png`):

| Trial | Debris domain, share of glacier (start → 2013 → 2016 → 2021) |
|---|---|
| 451 (debrisConc 9.1) | 10% → 74% → 88% → 97% |
| 411 (debrisConc 3.8) | 10% → 22% → 42% → 78% |
| 189 (debrisConc 9.8) | 10% → 86% → 95% → 97% |

  Every cell with at least 2 cm of debris (`min_thickness`) becomes a debris domain. With debrisConc up to
  10 kg m⁻³, emergence covers most of the ablation zone within 2–3 years. In HRU 2 (mean 2025 m) it even
  covers the accumulation area. Gulkana has only medial moraines. In October 2022 the share collapses
  (97% → 47% in 189, 78% → 36% in 411). That is probably the yield-stress rule in `run_flowModel`, which zeroes
  debris in a whole quadrant downslope of the first cell over `debrisCritStress`. It looks like a bug, not
  physics.
- **No liquid-water storage in firn or snow beyond Fcapil.** Fcapil is 0.017–0.049 and k_snow 0.043, near its
  upper bound. Meltwater leaves the snowpack quickly, and the firn reservoir is the only delay. Firn retention
  would delay June runoff, but it is second-order next to items 1–3.
- **Upland routing.** The bounds allow routingGammaScale up to 5e6 s, beyond nTimeDelay. The truncation only
  prints a WARNING and the histogram is renormalised.

## Other experiments (2010–2014, trial 451, old inputs)

| Run | Change | All | Jun | Jul | Aug | Sep | Jun/JA | KGE | Bw | Bs | Debris % (end) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E0 | none | 0.75 | 0.93 | 0.80 | 0.68 | 0.65 | 1.26 | 0.63 | 727 | −1839 | 86 |
| E1 | debrisConc = wallErosionRate = 0 | 0.76 | 0.85 | 0.80 | 0.74 | 0.69 | 1.10 | 0.63 | 698 | −2033 | 10 |
| E2 | ice albedo 0.45/0.25 (0.35 broadband) | 0.80 | 0.94 | 0.86 | 0.75 | 0.72 | 1.17 | 0.70 | 725 | −2044 | 83 |
| E3 | JJAS precipitation ×1.9 | 0.86 | 0.89 | 0.88 | 0.80 | 0.92 | 1.06 | 0.74 | 838 | −1764 | 70 |
| E4 | E2 + albedoMax 0.84, albedoDecayRate 1e6 s | 0.59 | 0.36 | 0.59 | 0.71 | 0.84 | 0.55 | 0.41 | 768 | −1358 | 38 |
| E5 | E1 + E3 + E4 | 0.67 | 0.33 | 0.61 | 0.79 | 1.12 | 0.47 | 0.48 | 873 | −1175 | 10 |

- E1 and E2 move water from June toward August but over-melt the glacier with 451's other parameters. A
  recalibration would take that back through the snow parameters, which is the point.
- E4 and E5 show that with realistic snow albedo, the June/July–August split flips to too late. Snow albedo
  is the dominant control on the seasonal shape. The search pushed it dark because there was no other way to
  make volume.
- None of these is a fit; each changes one thing and holds the other 29 parameters at 451's values.

## Recommended fixes, in priority order

1. **Forcing: correct summer liquid precipitation.** Extend `correct_forcing_to_station.py` to rain. The 1480
   and 1725 m tipping-bucket gauges give July–August ratios of about 1.8 and 2.3 against ERA5, with an
   elevation gradient. Use a monthly or event ratio per HRU for June–September, the same way snowfall is
   scaled to the stakes. Check gauge undercatch and data gaps first: Precip_TPG is missing on some days, and the two
   gauges differ by up to 35% in a season. This is the only fix that produces the rain floods.
2. **Rebuild with the polygon areas** (in progress), then recalibrate after fix 1. Expect frozenPrecipMultip
   to return toward 1 and albedoDecayRate to leave its bound.
3. **Tie the albedo parameters to the Site B record.** Narrow albedoMax to about 0.80–0.90 and albedoDecayRate
   to at least about 3e5 s. Set or calibrate the bare-ice albedo near 0.35–0.45 broadband through
   albedoFrznWatVisible/NearIR, or better a separate glacier-ice albedo parameter. Score the Site B daily albedo
   in 2024, or the snowline date, as a check. glacierTempReduction should be held near the measured 1.3 K
   instead of left free down to 0.
4. **Stop the debris runaway for Gulkana.** Either pin debrisConc and wallErosionRate near 0, or cap
   debrisConc at about 1–2 and raise `min_thickness`. Fix the quadrant-zeroing rule in `run_flowModel` that
   collapses the debris area in October 2022. Without this, every calibrated melt parameter absorbs a
   nonexistent debris insulation that grows each year.
5. **Bound the upland routing.** Cap routingGammaScale at about 2e5 s (mean delay ≤ about 5 d), and make the
   nTimeDelay truncation fatal in calibration. Otherwise the search keeps using a 50-day delay to move June
   snowmelt into July–August.
6. **Structural, after 1–5.** Add fractional snow cover on glacier domains, or treat residual SWE of a few mm
   as bare for albedo and the reservoir switch. Optionally add liquid-water retention in firn. Allow a real
   slow reservoir (aquifer) for the 0.1–0.2 m³/s winter flow.

## Files

- `runs/gulkana_timing_diagnosis/monthly_sources_451.png`: monthly gauge against simulation and source split.
- `runs/gulkana_timing_diagnosis/aug2018_event.png`: August 2018 station against forcing precipitation, and
  discharge.
- `runs/gulkana_timing_diagnosis/debris_area.png`: debris-domain share of the glacier in the three trials.
- `runs/gulkana_timing_diagnosis/scripts/`: `monthly.py`, `mb.py`, `snowoff.py`, `yearly.py`,
  `precip_cmp.py`, `plots.py`, `setup_exp.py`, `exp_cmp.py`.
- `runs/gulkana_timing_diagnosis/exp/E*`: experiment runs (2009–2014, 2 MPI ranks each), and
  `forcing_JJAS_x1.9/`, the scaled forcing through 2014.
