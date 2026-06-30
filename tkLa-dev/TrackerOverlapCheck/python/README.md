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

## Output Files

The base name of output files is `tracker<geometry>DDD`:

* `Geometry_tracker<geometry>DDD.txt` — Full geometry hierarchy and volume definitions
* `Materials_tracker<geometry>DDD.txt` — Material composition and properties
* `Overlaps_tracker<geometry>DDD.txt` — **Overlap report** (key validation output)
* `Tracker.gdml`, `Phase2OTBarrel.gdml`, `Phase2OTForward.gdml`, `Phase2PixelBarrel.gdml`, `Phase2PixelEndcap.gdml` — one GDML file per matched tracker envelope physical volume (only if `gdml=1`)

## Known Issues

### Fatal exception when running with `gdml=1` a second time

`G4GDMLWrite::Write()` raises a fatal exception and aborts the process if the output
file already exists — it will not overwrite it. Delete all GDML files in `pwd` before
re-running with `gdml=1`:

```bash
rm -f *.gdml
cmsRun g4OverlapCheckRun4Tracker_cfg.py gdml=1
```

## Related Scripts

| Script | Scope | Format |
|--------|-------|--------|
| `g4OverlapCheckRun4DDD_cfg.py` | Full detector | DDD |
| `g4OverlapCheckRun4DD4hep_cfg.py` | Full detector | DD4hep |
| `g4OverlapCheckRun4Tracker_cfg.py` | Tracker | DDD |
