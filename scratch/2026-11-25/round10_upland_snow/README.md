# Upland snow with elevation, for a round 10 of Wolverine and Gulkana

The station correction raises rain above the highest gauge (`rain_multiplier_above_gauges` in `corrections.csv`) and glacier snow by the
stakes, but not upland snow. `upland_snow_grad: [lower, upper]` in a case of `cases.yaml` writes the rain's rise into
`frozenPrecipMultip` of the upland domains (`build_cases.set_glacier_snowfall`), and `frozenPrecipMultip@upland` becomes a multiplier of
it searched in those bounds (`runs/calibrate.py`). The code is on `main`; no case of Wolverine or Gulkana has the key yet.

| Case | Upland factor by HRU | Round 9 front's `frozenPrecipMultip@upland` |
|---|---|---|
| `wolverine_added` | 1, 1.264, 1.737 | 1.75-2.23 |
| `gulkana_added` | 1, 1, 1.604 | 2.63-3.38 |

To port: `git apply scratch/2026-11-25/round10_upland_snow/cases.patch`, then per case `build_cases.py cases.yaml <case>`,
`runs/spinup.py <case>` (the snow changes the cold state), and calibrate as `scratch/2026-11-24/r9/run.sh` after its round 9 folders are renamed.

- The stream cases inherit the key from their parent, so rebuild and spin those up too. A round 9 trial must not be pinned on them:
  its value is the flat snowfall, here it is a multiplier.
- `wolverine_general` and `gulkana_general` (raw ERA5) have no gauge correction: leave them, the key does nothing there but set the bounds.
- Bounds 0.4-4 hold the flat values of round 9 (up to 3.4); Lemon uses 0.4-2. Lemon's evaluation (`lemon_grus_snow`) decides whether the fix stays.
- Rounds 1-9 searched 0.2-5 on the flat value, so the two parameters are not comparable.
