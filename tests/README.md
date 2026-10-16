# Glacier calibration tests

Short calibrations of each glacier, built by `../build_cases.py ../cases.yaml gulkana_test wolverine_test`.
They exercise the calibration on the glacier domains; the paper's calibrations are the full runs in `../runs`.
The scores below come from the setup they were last measured on; the cold start and debris layering have
changed since (16 Oct), so rerun before quoting them.

## `test_calibration_gulkana.sh`

Gulkana, discharge (KGE, as the GRU's routed runoff times its area) and the glacier-wide seasonal mass
balance (RMSE), 2009–2012 after a spin-up over 2008, over the common parameters and the glacier and snow
ones. `gulkana/README.md` says how the domain and observations were built.

```bash
./test_calibration_gulkana.sh [population] [generations] [n_ranks]   # defaults: 8, 4, 5
```

## `test_calibration_wolverine.sh`

A glacier calibration routed by mizuRoute, scoring discharge (KGE) and water temperature (RMSE, degC)
at USGS 15236900, and the glacier-wide seasonal mass balance (RMSE), on the bundled `wolverine/`
domain: three glacier land HRUs and a stream HRU for the one reach. It spins up over 2016 and scores
2017–2019, over the common parameters and the glacier and snow ones. `aquiferBaseflowRate` has a
lower bound of 10⁻⁸ m s⁻¹ in `wolverine/` and `gulkana/` so it can be searched on a log scale. Under
`deepTherml = bedrockLyrs` the groundwater leaves at the bedrock base, whose temperature no parameter
sets; with `deepTherml = airTempGW` the search would add `C_ATGW` and `gwTempWindow`. The stream width
is left at the gauge's: searching `streamWidthMultip` instead gives about the same temperature and a
worse mass balance.
`hypFrac` and `hypLag` are left at their defaults: the hyporheic proxy damps the daily swing, which a
daily-mean target cannot see, and halving `hypLag` leaves the RMSE unchanged.

```bash
./test_calibration_wolverine.sh [population] [generations] [n_ranks]   # defaults: 8, 4, 5
```

It needs summa's `bin/summa_sundials_mizuroute_opt.exe`. At the defaults it takes about 10 minutes, and every
trial runs. The front runs from KGE 0.88 at 0.78 degC and 602 mm, through KGE 0.81 at 0.84 degC and
248 mm, to 0.71 degC at KGE 0.67 and 1,557 mm. Every trial runs 0.5–1 degC cold from July to
September. Glacier runoff enters the reach at freezing; the water
warms from the groundwater of the unglaciated third of the basin, which leaves at the bedrock's
starting temperature, and from the heat friction dissipates down the reach.
`wolverine/README.md` says how the domain and observations were built.
