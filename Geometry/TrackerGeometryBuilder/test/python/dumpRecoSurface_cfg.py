import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing

# Dump the reco Surface (post-alignment) position + rotation for every tracker
# DetId, as CSV. Run once per geometry export; diff the two CSVs by rawId.
#
# Examples:
#   # broken export (HEAD / OT807), T40 alignment applied:
#   cmsRun dumpRecoSurface_cfg.py out=surf_OT807.csv
#
#   # good export (b0e9b11 / OT806) -- run in that checkout/area:
#   cmsRun dumpRecoSurface_cfg.py out=surf_OT806.csv
#
#   # ideal-geometry discriminator: same broken export, alignment DISABLED
#   cmsRun dumpRecoSurface_cfg.py out=surf_OT807_ideal.csv applyAlignment=False

options = VarParsing.VarParsing()
options.register('out', 'RecoSurfaceDump.csv',
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string, "output CSV file name")
options.register('applyAlignment', True,
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.bool,
                 "apply TrackerAlignment payload from the GT (False = ideal geometry)")
options.register('geom', 'ExtendedRun4D126',
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string,
                 "geometry scenario tag (matches Geometry<tag>Reco_cff)")
options.register('dd4hep', False,
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.bool,
                 "use the DD4hep geometry cff (GeometryDD4hep<tag>Reco_cff) instead of DDD")
options.register('gt', 'auto:phase2_realistic_T40',
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string, "GlobalTag")
options.register('unitsOnly', False,
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.bool,
                 "dump only DetUnits (skip Glued/Stack composites)")
options.register('sqliteFile', '',
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string,
                 "Absolute path to a local SQLite file to override GT alignment")
options.parseArguments()

from Configuration.Eras.Era_Phase2C17I13M9_cff import Phase2C17I13M9
process = cms.Process("RecoSurfaceDump", Phase2C17I13M9)

# Geometry (DB path) + conditions.
# XYZPosAlgo is an OT placement algorithm in the geometry description, so the
# DDD vs DD4hep path can matter -- pick it explicitly to match the export built.
_prefix = 'DD4hep' if options.dd4hep else ''
process.load('Configuration.Geometry.Geometry%s%sReco_cff' % (_prefix, options.geom))
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_cff')
process.load('FWCore.MessageService.MessageLogger_cfi')

from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, options.gt, '')

if options.sqliteFile:
    import os
    # CMSSW requires absolute paths for sqlite_file connections
    abs_db_path = os.path.abspath(options.sqliteFile) 
    process.GlobalTag.toGet.extend([
        cms.PSet(
            record = cms.string('TrackerAlignmentRcd'),
            tag = cms.string('TrackerAlignment_Upgrade2026_T40_design_v1'),
            connect = cms.string('sqlite_file:' + abs_db_path)
        ),
        cms.PSet(
            record = cms.string('TrackerAlignmentErrorExtendedRcd'),
            tag = cms.string('TrackerAlignmentErrorsExtended_Upgrade2026_T40_design_v1'),
            connect = cms.string('sqlite_file:' + abs_db_path)
        )
    ])

# Toggle whether the TrackerAlignment payload is applied to the reco geometry.
# applyAlignment=False -> ideal geometry (built from XML/GeometricDet only).
# The Reco cff instantiates the TrackerDigiGeometryESModule under the label
# 'trackerGeometry' (see Configuration/Geometry/python/Geometry*Run4D126Reco_cff.py).
process.trackerGeometry.applyAlignment = cms.bool(options.applyAlignment)

process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(1))

process.dump = cms.EDAnalyzer("RecoSurfaceDump",
                              outFileName=cms.untracked.string(options.out),
                              unitsOnly=cms.untracked.bool(options.unitsOnly))

process.p = cms.Path(process.dump)
