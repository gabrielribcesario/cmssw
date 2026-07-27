# Tracker Geometry Overlap Check

A `cmsRun` configuration script that validates the CMS Phase-2 tracker geometry by detecting overlapping volumes.

This tool samples random points throughout the tracker geometry and reports any physical volumes that occupy the same space, which would cause issues in particle simulation.

Uses the DDD (Detector Description Database) geometry format for Run 4 scenarios.

## Usage

```bash
cmsRun g4OverlapCheckRun4Tracker_cfg.py [geometry=<geom>] [tol=<tol>] [resolution=<res>] [gdml=<0|1>]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `geometry` | `D110` | Run 4 detector scenario. Supported values can be found at `$CMSSW_BASE/src/Configuration/Geometry/python/dictRun4Geometry.py`. |
| `tol` | `0.01` | Overlap tolerance in mm. |
| `resolution` | `50000` | Number of random points sampled per volume. |
| `gdml` | `0` | Set to `1` to export each matched tracker envelope physical volume to its own GDML file. |

## Examples

```bash
# Run with default options
cmsRun g4OverlapCheckRun4Tracker_cfg.py

# Check a specific scenario and export GDML
cmsRun g4OverlapCheckRun4Tracker_cfg.py geometry=D110 tol=0.01 gdml=1

# Run with a looser tolerance and lower resolution
cmsRun g4OverlapCheckRun4Tracker_cfg.py geometry=D114 tol=0.1 resolution=10000
```

## Tracker Envelopes

The check uses `RegionFlag=True` and is scoped to the tracker envelope G4Regions defined in
`$CMSSW_BASE/src/Geometry/TrackerSimData/data/PhaseII/*/trackerProdCuts.xml` and `pixelProdCuts.xml`:

| G4Region | Selector in XML | Contains |
|----------|----------------|----------|
| `TrackerDeadRegion` | `//Tracker` | Full tracker envelope |
| `TrackerOuterDeadRegion` | `//Phase2OTBarrel`, `//Phase2OTForward` | Outer tracker barrel and endcap envelopes |
| `TrackerPixelDeadRegion` | `//Phase2PixelBarrel`, `//Phase2PixelEndcap` | Inner tracker barrel and endcap envelopes |

> **Note:** The sensor-level regions (`TrackerOuterSensRegion`, `TrackerPixelSensRegion`) are excluded
> from the default `NodeNames` to avoid writing thousands of per-sensor GDML files when `gdml=1`.
> Add them to `NodeNames` in the script if you need sensor-level scoping.

To check a different scope, edit `RegionFlag` and `NodeNames` in the script.

## GDML Inspection in ROOT

When `gdml=1` is set, one GDML file is written per matched physical volume
(e.g. `Tracker.gdml`, `Phase2OTBarrel.gdml`, `Phase2PixelBarrel.gdml`, ...). Each can be loaded independently in ROOT:

```cpp
TGeoManager::Import("Tracker.gdml");
gGeoManager->GetTopVolume()->Draw("ogl");
gGeoManager->CheckOverlaps(0.01);
gGeoManager->PrintOverlaps();
```

For an isolated 3D view of just the offending volumes, use the `overlap_check.C`
macro in `../macro/`:

```bash
root -l '../macro/overlap_check.C("Tracker.gdml", 0.01, false)'
```

By default it runs ROOT's mesh-based `CheckOverlaps`, which covers both overlaps
and extrusions. Pass an optional fourth argument of the form `"s[n samples]"`
(e.g. `"s50000"`) to switch to a sampling-based check with that many sample
points per volume instead:

```bash
root -l '../macro/overlap_check.C("Tracker.gdml", 0.01, false, "s50000")'
```

> **Note:** The sampling-based check skips extrusions, so it will miss
> mother/daughter (container) overlaps that the default mesh-based check
> catches.

## Output Files

The base name of output files is `tracker<geometry>DDD`:

* `Geometry_tracker<geometry>DDD.txt` — Full geometry hierarchy and volume definitions
* `Materials_tracker<geometry>DDD.txt` — Material composition and properties
* `Overlaps_tracker<geometry>DDD.txt` — Overlap report
* `Tracker.gdml`, `Phase2OTBarrel.gdml`, `Phase2OTForward.gdml`, `Phase2PixelBarrel.gdml`, `Phase2PixelEndcap.gdml` — one GDML file per matched tracker envelope physical volume (only if `gdml=1`)

## Known Issues

### Fatal exception when running with `gdml=1` a second time

`G4GDMLWrite::Write()` raises a fatal exception and aborts the process if the output
file already exists — it will not overwrite it. Delete all GDML files in the working
directory before re-running with `gdml=1`:

```bash
rm -f *.gdml
cmsRun g4OverlapCheckRun4Tracker_cfg.py gdml=1
```

## Related Scripts

`g4OverlapCheckRun4Tracker_cfg.py` is adapted from the full-detector overlap
checkers in `SimG4Core/PrintGeomInfo/test/python/`, reusing the same
`checkOverlap`/`G4CheckOverlap` PSet and output-file conventions, but scoped
down to the tracker envelope G4Regions (see [Tracker Envelopes](#tracker-envelopes))
instead of checking the whole detector. It also adds the `resolution` and
`gdml` options, which the originals don't have.

| Script | Package | Scope | Format |
|--------|---------|-------|--------|
| `g4OverlapCheckRun4DDD_cfg.py` | `SimG4Core/PrintGeomInfo/test/python/` | Full detector | DDD |
| `g4OverlapCheckRun4DD4hep_cfg.py` | `SimG4Core/PrintGeomInfo/test/python/` | Full detector | DD4hep |
| `g4OverlapCheckRun4Tracker_cfg.py` | `tkLa-dev/TrackerOverlapCheck/python/` | Tracker | DDD |
