# Gulkana runaway debris cover: diagnosis

**Short answer.** Debris spreads because the code lets debris emerge over almost the whole glacier, and
then any cell above 2 cm becomes debris. The emergence zone is every glacier cell below `2·ELA − top`. The
model's annual ELA sits at 2055–2426 m against a 2426 m top, so in 2009–2014 that zone covers 33–100% of the
glacier (100% in 2010). Melt-out then lays a thin veneer of debris everywhere. Lateral rockfall adds to it
along the margins, which in those years means the whole margin. Each cell crosses the 2 cm threshold
(`min_thickness`) after a few years. A
mass-balance lookup bug and a "debris > 0" switch in the flow model feed the process. The concentration
(debrisConc 9.1 in 451) sets how fast the veneer thickens, but not where it goes. At 1 kg m⁻³ with no rockfall
(G3), the share holds at 10% through 2014. But a 1–10 mm veneer has by then spread over 8.8 km² and keeps
thickening, so a lower value only delays the runaway (§4). So the cause is **physics/code, not parameters**. The October collapses
come from the quadrant-clearing rule, which is a bug: it clears the quadrant *upslope* of the failing cell,
not downslope.

With the fix (branch `debris-fix-clean`, commit `dc8f8910`, diff in §6), trial 451 keeps debris at
10% → 14% by 2015 (G2), against 10% → 75% without the fix (G0, which reproduces E6). Rockfall drives the
remaining growth. With wallErosionRate = 0 as well (G5), the debris stays at the mapped 1.75–1.76 km² (10%)
while the mapped debris thickens by emergence.

All experiments use the timing-diagnosis E6 setup: trial 451 pinned, polygon HRU areas, and the
gauge-corrected summer rain. They run 2009–2014 after the default-parameter spin-up over 2008. Outputs are in
`runs/gulkana_debris_diagnosis/exp/`; the scripts are `scripts/setup_exp.py`, `run.sh` and `summary.py`.
The diagnostic build (branch `debris-diag`, commit `61069e05`) prints a `DBRDIAG` budget per glacier and
year to run.log and dumps the 154×138 grid to `exp/<run>/grids/`. D0/D1 are the same as G0 with the inputs
of `calibration_rerun/sample_451` (identical results to 3 digits, so they already had the rain correction).

## 1. Mechanism, step by step (glacAreaChange.f90 at multi-calib 379fe0eb)

Once a year `glacAreaChange` fits mass change against elevation and runs `run_flowModel` over the year on
the 50 m grid. The debris steps are:

1. **ELA** (l. 240, 301). The clean-domain fit gives the ELA. When every clean domain loses mass, the ELA is
   extrapolated above the top domain, and l. 301 caps it at the glacier top. In 451, the top clean domain
   (2038 m) loses 0.1–1.4 m w.e. in every year, so the model ELA is 2055–2426 m.
2. **Emergence zone** (`static_emergElev_latRockfall`, l. 1151–1153). `emergenceElev = 2·ELA − top +
   latMoraineWidth·mean_slope`, capped at the ELA. The mask is *every glacier cell below it*: there is no
   source location and no lateral limit. This "symmetric trajectory about the ELA" rule breaks down as the ELA
   nears the top: the zone becomes the whole glacier.

   | Year (update) | ELA (m) | emergenceElev (m) | Emergence cells / glacier cells |
   |---|---|---|---|
   | spin-up 2008 (default params) | 1930 | 1470 | 827 / 6610 (13%) |
   | 2009 | 2286 | 2181 | 6082 / 6711 (91%) |
   | 2010 | 2426 (= top) | 2426 | 6706 / 6706 (100%) |
   | 2011 | 2268 | 2148 | 5906 / 6691 (88%) |
   | 2012 | 2055 | 1724 | 2232 / 6672 (33%) |
   | 2013 | 2290 | 2193 | 6109 / 6667 (92%) |
   | 2014 | 2144 | 1902 | 3740 / 6633 (56%) |

3. **Emergence rate** (l. 1066–1069). The added thickness is `−m_dot·debrisConc / (soil_dens_intr·(1 − theta_sat))`,
   applied uniformly to every cell in the mask. With 451's values (9.12 kg m⁻³, 2600 kg m⁻³, and the
   *calibrated soil* porosity 0.593), that is 8.6 mm of debris per m w.e. of melt. m_dot is water equivalent
   but debrisConc is per m³ of ice (a 9% underestimate). Where m_dot > 0 inside the mask, the term goes
   negative and removes debris.
4. **Rockfall** (l. 1200–1265). A band `latMoraineWidth` = 160 m wide along every margin below the ELA gets
   `rockface_len·wallErosionRate/latMoraineWidth`. With the ELA near the top, that is 714–1370 cells
   (1.8–3.5 km²) at 2.7–3.6 mm/yr. The rock-face height is `2·(S − B_neighbour)` from the single 50 m
   off-glacier neighbour cell. It is counted only where the ice stands *above* the neighbour, but at 59% of the
   margin cells below the ELA the neighbour is higher (a wall). So the source has no relation to real headwalls.
5. **Feedback in the flow model's mass balance** (`massBalance`, l. 1004–1010).
   - Any cell with `debris > 0` uses the debris-domain curve, but SUMMA builds its domains with
     `debris >= 2 cm` (l. 328–329). After one year in 2009, 14.2 km² carry a 1–5 mm veneer, so they switch
     curves.
   - **The segment lookup is off by one.** The fit numbers segment *i* as joining points *i − 1* and *i*,
     with segment 1 extrapolating above and *nPts + 1* below. The lookup returns *i* for a cell between points
     *i* and *i + 1*, and *nPts + 1* (the *below-terminus* extrapolation) for a cell above the highest point.
     So cells above the top debris domain get the terminus value. With the 2009 clean curve, 2400 m gets
     +1583 instead of +434 kg m⁻², and 1700 m gets −2175 instead of −1881. Cells below the lowest debris
     point (1369 m) get the inverted interior segment: +1034 kg m⁻² at 1250 m, under the thickest debris.
6. **Threshold** (l. 64, 328–329). Every cell with `debris >= 0.02 m` joins the debris domain, whatever its
   elevation or the mapped extent. New debris cells are 2–6 cm thick (p10/p50/p90 0.021/0.032/0.064 m in
   2013). It is the veneer crossing the threshold, not advected moraine. And it is spread evenly with
   distance from the margin. By the end of 2013, 0–60 m from the edge: 1.83 of 2.68 km²; 60–160 m: 4.08 of
   5.45; 160–300 m: 3.76 of 4.59; more than 300 m: 3.65 of 4.16.
7. **Advection** (`advection_MUSCL`) is conservative and does not cause the growth. It smears trace amounts
   (more than 0 but under 1 mm) onto neighbours, which matters only through step 5.
8. **Yield-stress rule** (l. 740–760), see §3.

Which step makes the 10% → 90%? Steps 2 and 6 together. In G0, the main-glacier emergence volume is
36 000 → 160 000 → 126 000 m³ per year in 2009–2011, against 11 000 m³ of rockfall. The thickness histogram
moves from 10 km² at 1–5 mm (end of 2009) to 8 km² at 1–2 cm (2010), then over 2 cm (5.4 km² at 2–4 cm in
2011). The debris share jumps 20% → 48% in the 2011 update and 47% → 75% in 2013, the two years when the
emergence zone covers 88–92% of the glacier. Without rockfall (D1), the veneer thickens more slowly: 12.4 km²
at 0.5–1 cm in 2011–2012 and 5.1 km² at 1–2 cm by the end of 2013. It is the same runaway, two to three years
later.

## 2. Physics or parameters?

**Physics.** No single parameter value removes the mechanism. Under the current code, any debrisConc > 0
eventually pushes every cell below `2·ELA − top` past 2 cm. The rate is `c·Σmelt/(ρ_s(1 − φ))`, so a lower c
only stretches the time. In G3 (c = 1, no rockfall), the veneer reaches 0.5–1 cm on 1.1 km² after six years. Only
debrisConc = wallErosionRate = 0 (E1) freezes the debris at the mapped 10%.

**The parameter range is also too high for a clean glacier.** debrisConc is kg of rock per m³ of ice; dividing
by 2650 kg m⁻³ gives the volume fraction.

| Source | Englacial debris | In model units |
|---|---|---|
| Zmuttgletscher (debris-covered, Alps), measured | 0–0.041 vol% | 0–1.1 kg m⁻³ |
| Khumbu, borehole televiewer (Miles et al. 2021), mid-to-upper ablation zone | ≤ 0.7 vol% | ≤ 19 kg m⁻³ |
| Khumbu, near the terminus | 6.4 vol% | 170 kg m⁻³ |
| Mayer & Licciulli (2021), idealised debris-covered glaciers over 6000 yr | 0.5–1 vol% (uniform) | 13–26 kg m⁻³ |
| SUMMA range (all cases) | 0–10 kg m⁻³ | 0–0.38 vol% |
| Trials 451 / 189 / 411 | 9.12 / 9.83 / 3.85 kg m⁻³ | 0.34 / 0.37 / 0.15 vol% |

The calibrated values are Himalayan, debris-covered-glacier concentrations applied to the whole of a clean
Alaskan glacier with 10% medial-moraine cover. On clean glaciers, debris travels in thin septa below medial
moraines and in discrete bands (Kirkbride & Deline 2013; Anderson & Anderson 2016 feed it from a headwall
point source). Bulk ice away from the septa is near zero. Treated as a concentration *in the septa*, a few
kg m⁻³ is plausible, but only where the septa crop out, which on Gulkana is the mapped debris. The search
drives debrisConc to its upper bound because the debris domain melts more slowly in July–August, which
suppresses ice melt (timing diagnosis, mechanism 3). It is fitting a timing error, not debris physics.

Two smaller parameter problems:
- **Debris porosity is the calibrated soil `theta_sat`** (run_oneGRU.f90:640). Trials put it at 0.56–0.60
  for the upland soil hydrology. That makes debris 41% solid, so every kg of debris becomes 1.7× the
  thickness it would at a debris porosity of 0.3.
- **`wallErosionRate` (8 mm/yr default, not calibrated) and `latMoraineWidth` (160 m)** produce rockfall of
  about the same size as emergence once emergence is restricted (G1/G2: 9 000–11 600 m³/yr rockfall against
  3 000–18 000 m³/yr emergence). They drive all of the remaining growth to 14%.

## 3. The quadrant-clearing rule (l. 740–760) is a bug

Mayer & Licciulli (2021) model a 1-D flowline. When the driving stress of the debris layer passes the yield
stress, debris *downstream* of that node (the terminal wedge) is removed. The 2-D port has four errors:

1. **Wrong direction.** `slope_k = ∂S/∂x`. If slope_k > 0, the surface rises with i, so downslope is
   *smaller* i. The code zeroes `debris(i:nx, …)`, which is upslope. The l-direction is the same. In effect,
   when one cell near the terminus or a steep margin fails, the rule wipes the quadrant **upslope** of it,
   which is most of the glacier.
2. **Dead and duplicate branches.** The third test, `slope_l<0 .and. slope_k>0`, repeats the second, so the
   (k < 0, l > 0) quadrant can never take its own branch. The fourth tests `slope_k<0 .and. slope_k<0`, so it
   fires for any slope_k < 0, whatever the sign of slope_l.
3. **`exit` leaves only the inner i loop.** Every row j can clear another quadrant in the same step.
4. **The stress needs about 8 m of debris to trip** (80 kPa / (2600·0.41·9.81·sinα), with sinα ≈ 1 at
   margins where the neighbour is bare bed). Debris piles up only where ice velocity goes to zero. So the rule
   fires rarely, but catastrophically. In every trial, the HRU 3 debris area drops to the same 1.47–1.48 km²
   in one update: 451 in Oct 2022 (9.20 → 1.48), 411 in Oct 2022 (8.19 → 1.47), and 455 in Oct 2021
   (8.81 → 1.48). Wolverine shows the same drops: 84% → 7% in 2019–2020 (sample 187) and 98% → 34% in
   2020–2021 (sample 185).

The fix replaces the rule with per-cell removal: `where(drivingStress > debrisCritStress) debris = 0`. That
removes the failing layer (Mayer & Licciulli's "collapses and is eliminated") without touching anything
upslope. A per-cell transfer to the downslope neighbour (their "continuous displacement") would be the next
step if terminal debris unloading matters.

## 4. Experiments (trial 451, E6 inputs, 2009–2014)

Debris domain share of the glacier on 1 January. 2015 is the end state, 31 Dec 2014:

| Run | Code | Change | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 |
|---|---|---|---|---|---|---|---|---|
| G0_old | multi-calib + prints | none (= E6) | 0.10 | 0.20 | 0.48 | 0.47 | 0.75 | 0.75 |
| D1_noRockfall | multi-calib + prints | wallErosionRate 0 (2009–13) | 0.10 | 0.16 | 0.16 | 0.16 | 0.16 | – |
| G3_old_conc1_noRock | multi-calib + prints | debrisConc 1, wallErosionRate 0 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 |
| G1_fix1 | fix without the lookup fix | none | 0.10 | 0.11 | 0.12 | 0.12 | 0.14 | 0.14 |
| G2_fix2 | full fix (`dc8f8910`) | none | 0.10 | 0.11 | 0.12 | 0.12 | 0.13 | 0.14 |
| G4_fix2_conc1 | full fix | debrisConc 1 | 0.10 | 0.11 | 0.12 | 0.12 | 0.13 | 0.14 |
| G5_fix2_noRock | full fix | wallErosionRate 0 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 | 0.10 |

- G3 holds the share at 10% through 2014, but only for now. By the end of 2014, the old emergence rule has
  laid a veneer over 8.8 km²: 7.7 km² at 1–5 mm and 1.1 km² at 5–10 mm, still thickening by about 1 mm/yr.
  It would cross 2 cm a few years into the 2016–2022 evaluation period. The parameters can buy time for the
  calibration window, not fix it.
- With the fix, the emergence volume falls from 36 000–160 000 to 3 000–10 000 m³/yr (G2). Changing
  debrisConc from 9.1 to 1 (G4) cuts it about 9×, from 2 600–10 400 to 400–1 200 m³/yr, and leaves the area
  identical. So with the fix, debrisConc only sets the thickness of the mapped debris, and the area is set by
  rockfall and advection.
- **The fix changes the water budget.** The basin-mean glacier mass change for 2011–2014 is 15–30% more
  negative than in G0, because less of the glacier is insulated: −2.83 → −3.67 ×10⁻⁵ in 2014. The lookup
  fix alone (G1 → G2) shrinks the glacier slightly faster (17.24 → 17.19 km² by the end of 2014) and halves
  the emergence. So the code fix must come **before** the recalibration, not after.

A full 2009–2022 diagnostic run (G0_old_full) was started to catch the yield events, then stopped to stay
within 4 cores. No yield event fires in any run up to 2014: vClear is 0 in every budget. So the collapse
evidence is the code reading in §3 plus the identical 1.47–1.48 km² remnant across trials.

## 5. Wolverine

Wolverine runs away the same way, from about 1% (mapped) to 84–98%, and also collapses:

| Sample | Debris share 2009 → 2014 → 2016 → 2019 → 2020 → 2022-end |
|---|---|
| wolverine_corrected 187 (debrisConc 8.8) | 0.01 → 0.28 → 0.76 → 0.84 → 0.07 → 0.43 |
| wolverine_raw 185 (debrisConc 8.3) | 0.01 → 0.26 → 0.70 → 0.98 → 0.98 → 0.46 |

The code and the parameter ranges are shared (debrisConc 0–10; latMoraineWidth default 50 m there), so the
same fix and bounds apply.

## 6. Recommended fixes, in priority order

1. **Code (required before recalibrating).** Branch `debris-fix-clean` (commit `dc8f8910`, from
   multi-calib 379fe0eb, not merged), file `build/source/engine/glacAreaChange.f90`:
   - l. 1153: emergence only under existing debris (≥ `min_thickness`), i.e. where the debris septa crop out.
     The mask becomes `S<emergenceElev .and. S>B .and. debris>=min_thickness`, with `debris` passed into
     `static_emergElev_latRockfall` (l. 648, 1103, 1107). The debris footprint can then grow only by
     advection. That is the "restrict to where mapped debris exists" option, with no new state variable.
   - l. 1004: the flow model uses the debris mass-balance curve only for `debris >= min_thickness`, the same
     test SUMMA uses to build the domains.
   - l. 1006–1008: segment lookup `ind = 1`, then `ind = i+1` for each point above the cell. l. 470: for a
     single point, `intercept(1:2) = massChange(1)`, so the below-extrapolation is defined.
   - l. 1066: emergence from melt only, converted to ice:
     `max(-m_dot,0)·iden_water/iden_ice·debrisConc`.
   - l. 745–760: per-cell yield removal instead of the quadrant rule.

   The diff (96 lines) is in `debris_fix.diff`, beside this file. The full fix was built and run as G2/G4 from
   branch `debris-fix` (`cc834d1f`, the same code plus the DIAG prints). The clean branch is the same edits
   without the prints and was not built separately.

   This changes backward-euler solutions, so it needs a `-` entry in `docs/assets/changes_fromV3Summa.txt`
   when merged.
2. **Parameters for the recalibration** (in `runs/{gulkana,wolverine}_{corrected,raw}/summa_inputs/basinParamInfo.txt`):
   - `wallErosionRate`: **pin 0** (`0.0 | 0.0 | 0.0`). The rockfall source geometry is not physical (step 4)
     and, after the fix, drives all the remaining area growth.
   - `debrisConc`: **remove from `PARAMS` in calibrate.py and pin**, at `1.0 | 1.0 | 1.0` kg m⁻³ (about 0.04
     vol%, the Zmutt range). If it stays calibrated, bound it at **0–2**. With the fix it only thickens the
     mapped debris, and no calibration target constrains debris thickness.
   - `debrisCritStress`: pin at the default `80000 | 80000 | 80000` Pa (Mayer & Licciulli use 60–100 kPa).
   - `latMoraineWidth`: no effect on rockfall once wallErosionRate = 0. It still shifts `emergenceElev` by
     W·slope (+37 m on Gulkana), so pin it at its default: Gulkana 160, Wolverine 50.
   - `theta_sat` (localParamInfo.txt) doubles as the debris porosity. If it stays calibrated for soil, cap its
     upper bound at about 0.45. Otherwise the code needs a separate debris porosity.
3. **If the code fix cannot go in first**, pin `debrisConc` = 0 and `wallErosionRate` = 0, as in E1.
   Not debrisConc = 1: in G3 that only postpones the runaway past 2014. The
   debris then stays at the mapped 10% (1.76 km²), and the mass-balance lookup bug stays in the clean-glacier
   geometry.
4. **Later.** Base the emergence elevation on a long-term ELA instead of the annual one. Replace the
   neighbour-cell rock face with a DEM headwall height above the glacier. Model terminal debris unloading as
   a downslope transfer.

## Sources

- Mayer, C. & Licciulli, C. (2021). The concept of steady state, cyclicity and debris unloading of
  debris-covered glaciers. *Front. Earth Sci.* 9:710276. https://www.frontiersin.org/journals/earth-science/articles/10.3389/feart.2021.710276/pdf
- Miles, K. E. et al. (2021). Continuous borehole optical televiewing reveals variable englacial debris
  concentrations at Khumbu Glacier, Nepal. *Commun. Earth Environ.* https://eprints.whiterose.ac.uk/170201/7/s43247-020-00070-x.pdf
- Zmuttgletscher englacial debris concentrations (0–0.041 vol%): https://lean-gate.geo.uzh.ch/typo3conf/ext/qfq/Classes/Api/download.php/mastersThesis/1218
- Anderson, L. S. & Anderson, R. S. (2016). Modeled response of debris-covered glaciers to climate change.
  *The Cryosphere* 10, 1105–1124. Kirkbride, M. P. & Deline, P. (2013). The formation of supraglacial debris
  covers by primary dispersal from transverse englacial debris bands. *ESPL* 38. These two are cited for
  the source geometry only, not for numbers.
