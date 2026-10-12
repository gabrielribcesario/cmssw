# DesignAlignment

A CMSSW configuration designed to generate a design tracker alignment payload — `TrackerAlignmentRcd` and `TrackerAlignmentErrorExtendedRcd` — directly from the ideal Phase-2 XML geometry, for any Run4 detector configuration (`D110`, `D111`, `D112`, ...).

This tool is primarily built to give each tracker version its own design-alignment tag, instead of borrowing another version's constants.

## Prerequisites

- A working CMSSW environment (tested on Phase-2 `CMSSW_16_1_X` releases).
- Standard CMS software dependencies (`scram`, `cmsRun`, `conddb`).

## Installation

This package ships only a Python configuration file — there is no plugin to compile.

## Usage

The execution is handled by a dynamic Python configuration file (`createDesignAlignment_cfg.py`). It lets you specify the target geometry scenario directly from the command line, and it automatically looks up the correct Tracker version from the CMSSW detector version dictionary to name the output database file and its tags.

1. Place `createDesignAlignment_cfg.py` in your working directory.

2. Run the configuration file via `cmsRun`, passing your desired geometry scenario as an argument:

    ```bash
    cmsRun createDesignAlignment_cfg.py geometry=D112
    ```

3. The script will successfully write an SQLite database into your current directory named automatically based on the Tracker version (e.g., `TrackerAlignment_Upgrade2026_T37_design_v1.db`, since `geometry=D112` resolves to `T37`).

4. Check that both payloads were written (`conddb list` takes the tag name as an argument):

    ```bash
    conddb --db TrackerAlignment_Upgrade2026_T37_design_v1.db list TrackerAlignment_Upgrade2026_T37_design_v1
    conddb --db TrackerAlignment_Upgrade2026_T37_design_v1.db list TrackerAlignmentErrorsExtended_Upgrade2026_T37_design_v1
    ```

    Each should show one IOV.


The generated database contains the following two tags, both written by the `PoolDBOutputService`:

* `TrackerAlignment_Upgrade2026_<TrackerVersion>_design_v1` (record `TrackerAlignmentRcd`): the per-module translations and rotations. These are zero-movement, i.e. every module keeps its ideal (generally from XML) placement.
* `TrackerAlignmentErrorsExtended_Upgrade2026_<TrackerVersion>_design_v1` (record `TrackerAlignmentErrorExtendedRcd`): the alignment position errors (APEs). These are also zero — see the notes below for why `setError=True` does not produce a nonzero APE here.

The resulting `.db` file is intended for local testing only — it is not uploaded to the shared conditions database.

## Picking up the payload

To make a `cmsRun` job actually read the new constants, point the corresponding entries of `Configuration/AlCa/python/autoCondPhase2.py` at the local SQLite file. Both the `TkAlignment` and the `TkAPE` entry read from the *same* `.db`, since the job writes both records into it:

``` python
allTags["TkAlignment"] = {
    ...
    '<TrackerVersion>' : ( ','.join( [ 'TrackerAlignment_Upgrade2026_<TrackerVersion>_design_v1' ,TkAlRecord, 'sqlite_file:/absolute/path/to/TrackerAlignment_Upgrade2026_<TrackerVersion>_design_v1.db', "", ""] ), ),
}

allTags["TkAPE"] = {
    ...
    '<TrackerVersion>' : ( ','.join( [ 'TrackerAlignmentErrorsExtended_Upgrade2026_<TrackerVersion>_design_v1' ,TkAPERecord, 'sqlite_file:/absolute/path/to/TrackerAlignment_Upgrade2026_<TrackerVersion>_design_v1.db', "", ""] ), ),
}
```

The joined fields are `tag, record, connection, label, snapshotTime` (see `Configuration/AlCa/python/GlobalTag.py`). Two details matter:

* The third field replaces the default `connectionString` — that is the Frontier connection of the global tag, so it must be swapped for `sqlite_file:` followed by an **absolute** path, otherwise the payload is still taken from the central database.
* The fifth field, the snapshot time, must be emptied (`""`). The stock entries pin a snapshot date, which would hide a freshly written IOV.

Finally, make sure the Tracker version is listed in `activeDets` further down the same file — a key that is absent there never makes it into `phase2GTs`, and the entries above are silently ignored.

## Notes

* Releases older than `CMSSW_14` are served the `2026` geometry naming (`dict2026Geometry`, `GeometryExtended2026<D>_cff`) instead of the `Run4` one.
* `NoMovementsScenario` (from `Alignment/TrackerAlignment/python/Scenarios_cff.py`) is used instead of the phase-0 scenarios and examples (e.g. `Alignment/LaserAlignment/test/createScenario.py`), because those hardcode phase-0 subdetector names (`TIB`, `TOB`, `TEC`) that do not exist in the Phase-2 Tracker.
* `NoMovementsScenario` is `MisalignmentScenarioSettings` (`setRotations=True`, `setTranslations=True`, `distribution='gaussian'`, `setError=True`) with no subdetector-specific blocks added, so no shifts or rotations are ever applied.
* `setError=True` and `distribution='gaussian'` do not by themselves produce a nonzero APE. In `AlignableModifier::modify()` (`Alignment/CommonAlignment/src/AlignableModifier.cc`) every `addAlignmentPositionError*` call sits behind a guard on the displacement or rotation magnitude, e.g. `if (std::abs(dX_) + std::abs(dY_) + std::abs(dZ_) > 0 && setTranslations_)`. With no subdetector blocks, `dX_`, `dY_`, `dZ_` and the `phi*_` angles keep their `init_()` defaults of `0.`, so every one of those branches is skipped. `setError` and `distribution` only decide *how* an error would be derived from a movement — they never create one.
* `MisalignedTrackerESProducer::produce()` is where both `writeOneIOV` calls happen (`Alignment/TrackerAlignment/plugins/MisalignedTrackerESProducer.cc`). Like any `ESProducer`, it only runs when its product is actually requested, and nothing else in this process consumes `TrackerGeometry` — hence the `EventSetupRecordDataGetter` requesting `TrackerDigiGeometryRecord` to trigger the write.
