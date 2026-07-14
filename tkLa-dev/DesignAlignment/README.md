# DesignAlignment

A CMSSW configuration that generates a design tracker alignment payload — `TrackerAlignmentRcd`
and `TrackerAlignmentErrorExtendedRcd` — directly from the ideal Phase-2 XML geometry, for any
Run4 detector configuration (`D110`, `D112`, `D126`, ...). This gives each tracker version its
own design-alignment tag instead of borrowing another version's constants.

The translations/rotations in `TrackerAlignmentRcd` are confirmed zero-movement: `NoMovementsScenario`
(see the "why" section) defines no per-subdetector shift/rotation blocks, so every module keeps
its ideal-geometry placement. The APE values in `TrackerAlignmentErrorExtendedRcd` are *not*
independently confirmed to be zero — see the caveat below before treating them as reference-zero.

## Prerequisites

- A working CMSSW environment (tested on Phase-2 `CMSSW_16_1_X` releases).
- Standard CMS software dependencies (`scram`, `cmsRun`, `conddb`).

## Usage

The job is driven by a single Python configuration file (`createDesignAlignment_cfg.py`). It lets
you pick the target geometry from the command line and automatically looks up the corresponding
tracker version from the CMSSW detector version dictionary to name the output DB file and tags.

1. `cd src/tkLa-dev/DesignAlignment`

2. Run the payload-generation job, passing your desired geometry scenario as an argument:
   ```bash
   cmsRun python/createDesignAlignment_cfg.py geometry=D126
   ```
   Produces `TrackerAlignment_Upgrade2026_T40_design_v1.db` in the current directory (tracker version `T40`
   is looked up from `geometry=D126`; omit the argument to fall back to the script's default).

3. Check the payload was written (`conddb list` requires the tag name as an argument):
   ```bash
   conddb --db TrackerAlignment_Upgrade2026_T40_design_v1.db list TrackerAlignment_Upgrade2026_T40_design_v1
   conddb --db TrackerAlignment_Upgrade2026_T40_design_v1.db list TrackerAlignmentErrorsExtended_Upgrade2026_T40_design_v1
   ```
   Each should show one IOV.

4. Cross-check the constants against the ideal geometry for the same scenario:
   ```bash
   cd ../GeometryDumper/python
   cmsRun dumpGeom_cfg.py geometry=D126
   ```
   Diff a few DetId positions from the resulting CSV against the payload from step 2/3 — they
   should match, and should differ from a dump of any other tracker version (proves the payload
   isn't reusing another geometry's constants).

The resulting `.db` file is for local testing only (e.g. pointing a `cmsRun` job's `PoolDBESSource`
at `sqlite_file:TrackerAlignment_Upgrade2026_T40_design_v1.db` for the two records above) — it is not uploaded
to the shared conditions DB.

---

**Why these specific choices** (skip if you just want the steps above):
- The `geometry=` -> tracker-version lookup mirrors `GeometryDumper/python/dumpGeom_cfg.py`, via
  `Configuration/Geometry/python/dictRun4Geometry.py`.
- `NoMovementsScenario` (from `Alignment/TrackerAlignment/python/Scenarios_cff.py`) is used
  instead of the phase-0 scenarios/examples (e.g. `Alignment/LaserAlignment/test/createScenario.py`)
  because those hardcode phase-0 subdetector names (`TIB`, `TOB`, `TEC`) that don't exist in
  the Phase-2 tracker.
- `NoMovementsScenario` = `MisalignmentScenarioSettings` (`setRotations=True`, `setTranslations=True`,
  `distribution='gaussian'`, `setError=True`) with no subdetector-specific blocks added, so no
  shifts/rotations are ever applied — this is why translations/rotations are verified zero-movement.
  `setError=True` + `distribution='gaussian'` are still active globally, though, so whether the
  APE record comes out exactly zero (vs. some nonzero gaussian-derived value) isn't confirmed by
  the scenario definition alone. Check step 3's output before treating it as reference-zero.
- Note the current script names the two output tags inconsistently: the alignment tag
  (`TrackerAlignment_{tracker_version}_design_v1`) omits the `Upgrade2026` infix that the APE tag
  (`TrackerAlignmentErrorsExtended_Upgrade2026_{tracker_version}_design_v1`) has. Worth aligning
  the two if you touch this script again.
