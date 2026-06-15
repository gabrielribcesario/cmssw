# Beampipe Geometry Overlap Check

A `cmsRun` configuration script that validates the CMS beampipe geometry by detecting overlapping volumes.

This tool samples random points throughout the beampipe geometry and reports any physical volumes that occupy the same space, which would cause issues in particle simulation.

Uses the DDD (Detector Description Database) geometry format for Run 4 scenarios.

## Usage

```bash
cmsRun g4OverlapCheckRun4Beampipe_cfg.py [geometry=<geom>] [tol=<tol>] [resolution=<res>] [gdml=<0|1>]
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `geometry` | `D110` | Run 4 detector scenario. Supported values can be found at "$CMSSW_BASE/src/Configuration/Geometry/python/dictRun4Geometry.py". |
| `tol` | `0.01` | Overlap tolerance in mm. |
| `resolution` | `50000` | Number of random points sampled per volume. |
| `gdml` | `0` | Set to `1` to export each matched beampipe physical volume to its own GDML file (e.g. `BEAM.gdml`, `BeamTube1.gdml`, ...). |

## Examples

```bash
# Run with default options
cmsRun g4OverlapCheckRun4Beampipe_cfg.py

# Check a specific scenario and export GDML
cmsRun g4OverlapCheckRun4Beampipe_cfg.py geometry=D110 tol=0.01 gdml=1

# Run with a looser tolerance and lower resolution
cmsRun g4OverlapCheckRun4Beampipe_cfg.py geometry=D114 tol=0.1 resolution=10000
```

## Beampipe Envelopes

The check uses `RegionFlag=True` and is scoped to the three G4Regions defined in
`$CMSSW_BASE/src/Geometry/TrackerSimData/data/trackerProdCutsBEAM.xml`:

| G4Region | Volumes matched |
|----------|----------------|
| `BeamPipe` | `BeamTube1` |
| `BeamPipeOutside` | `BEAM`, `BEAM1`, `BEAM2`, `BEAM3`, `BEAM4` |
| `BeamPipeVacuum` | `BeamVacuum1`, `BeamVacuum2`, ... |

To check a different scope, edit `RegionFlag` and `NodeNames` in the script.

## GDML Inspection in ROOT

When `gdml=1` is set, one GDML file is written per matched physical volume (e.g. `BEAM.gdml`, `BeamTube1.gdml`, `BeamVacuum1.gdml`, ...). Each can be loaded independently in ROOT:

```cpp
TGeoManager::Import("BEAM.gdml");
gGeoManager->GetTopVolume()->Draw("ogl");
gGeoManager->CheckOverlaps(0.01);
gGeoManager->PrintOverlaps();
```

## Output Files

The base name of output files is `beampipe<geometry>DDD`:

* `Geometry_beampipe<geometry>DDD.txt` — Full geometry hierarchy and volume definitions
* `Materials_beampipe<geometry>DDD.txt` — Material composition and properties
* `Overlaps_beampipe<geometry>DDD.txt` — **Overlap report** (key validation output)
* `BEAM.gdml`, `BEAM1.gdml`, ..., `BeamTube1.gdml`, `BeamVacuum1.gdml`, ... — one GDML file per matched beampipe physical volume (only if `gdml=1`)
* `beampipe<geometry>DDD.gdml` - Full geometry in GDML format (only if `gdml=1`)

## Known Issues

### Fatal exception when running with `gdml=1` a second time

`G4GDMLWrite::Write()` raises a fatal exception and aborts the process if the output
file already exists — it will not overwrite it. Since one GDML file is written per
matched physical volume, any file left from a previous run will trigger this. Delete
all GDML files in `pwd` before re-running with `gdml=1`:

```bash
rm -f *.gdml
cmsRun g4OverlapCheckRun4Beampipe_cfg.py gdml=1
```

## Related Scripts

| Script | Format |
|--------|--------|
| `g4OverlapCheckRun4DDD_cfg.py` | DDD | 
| `g4OverlapCheckRun4DD4hep_cfg.py` | DD4hep |
| `g4OverlapCheckRun4Beampipe_cfg.py` | DDD |
