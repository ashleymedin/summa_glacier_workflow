# Precipitation rise above the gauges: decisions, 26 Nov 2026 (Ashley)

Two uses of the stakes' gradient (precipElevGrad) above the highest gauge were questioned:
- **Item 1, rain:** `rain_grad` in the domain yaml, multiplied into the station-corrected forcing (since 18 Nov, so in round 9).
- **Item 4, upland snow:** `upland_snow_grad` in cases.yaml (new in round 10).

The gradient is fitted to winter balances on the glaciers. SNOTEL and snow courses have no off-glacier site above the gauges to test it: at Wolverine (gauge 990 m)
seven sites at 567-1052 m give about 0.0003 per m (1 May, 2019-26, against 0.00175); at Gulkana (gauge 1725 m) one pair up to 1536 m, two years, gives 0.0023-0.0025;
at Lemon a pair at 372-539 m gives 0.0024 (phase and melt mixed in). The old courses on the glaciers do not count.

| Glacier | Item 1, rain | Item 4, upland snow |
|---|---|---|
| Wolverine, Gulkana (added-data) | dropped in round 10b | dropped in round 10b |
| Lemon | **kept**: the gauge is at sea level (6 m, Juneau Airport), all of the basin is far above it, and its precipitation is probably just really wrong | **undecided**: from the paired run on the advective-heat code |

Round 10 runs with both, round 10b with neither, on the same code, so their difference is items 1 and 4 together; round 9 had item 1, the old code, and no item 4.
10b is therefore not a physics-only comparison with round 9. General cases have neither, and round 10's stand.

Lemon so far (old code, cheap 12 x 8 searches, one seed each): flat upland multiplier 4.8-5.0 (limit 5), with the rise 1.67-1.92 (limit 2); evaluation KGE (WY2016-20) of
balanced trials 0.79 flat against 0.71-0.72, not like for like because the flat case's calibration years include WY2016-20. Lemon wants much more upland snow than the airport
gives; the rise supplies part of it without improving the fit. Item 1 is in both cases, so Lemon does not test it. Paired run: `lemon_grus` and `lemon_grus_snow`,
`cheap_adv`, scratch/2026-11-25/lemon_pair_adv.sh, queued behind round 10. No upland snow note goes in glacier_forcing_runs.tex until it is decided.

After 10b, if adopted: rebuild `wolverine_stream_delta` and `gulkana_stream` (they inherit the key), and take the rise (eq. uplandsnow, the rain sentence, the
forcing-table entry, the 0.4-4 range) out of glacier.tex.
