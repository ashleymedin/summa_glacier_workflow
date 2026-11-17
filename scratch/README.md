# scratch

One-off analysis scripts, kept as run, by date. Not maintained; scripts move into the workflow proper when the analysis is written up. Paths into `/private/tmp/...` point at session build trees that may no longer exist.

`unused_tools/` holds workflow scripts the setup does not run (17 Nov 2026): `make_fake_well.py`, a synthetic well record
from a reference run for testing a well target, and `acquire_groundwater_level.py`, USGS groundwater levels for a well
target no domain has yet. Both import `observation_netcdf.py` from the workflow folder.
