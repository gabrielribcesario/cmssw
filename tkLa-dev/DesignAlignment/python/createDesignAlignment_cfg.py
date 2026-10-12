import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing
import importlib
import os

default_geometry = "D112"

args = VarParsing.VarParsing("standard")
args.register(
    "geometry",
    default_geometry,
    VarParsing.VarParsing.multiplicity.singleton,
    VarParsing.VarParsing.varType.string,
    f"The detector configuration name. Default is: {default_geometry}"
)
args.parseArguments()

# (Attempt at) Backward compatibility with older CMSSW versions
cmssw_version = os.environ["CMSSW_VERSION"]
major_version = int(cmssw_version.split("_")[1])
geom_suffix = "2026" if major_version < 14 else "Run4"

# Load the detector geometry dictionaries
dictGeometry = importlib.import_module(f"Configuration.Geometry.dict{geom_suffix}Geometry")

# Swap keys and values
detectorVersionDict = {v: k for k, v in dictGeometry.detectorVersionDict.items()}

try:
    tracker_version = detectorVersionDict[args.geometry][1]
except KeyError:
    valid_geometries = ", ".join(detectorVersionDict.keys())
    raise KeyError(f"Invalid geometry '{args.geometry}'. Must be one of: {valid_geometries}")

TrackerAlignmentRcd = f"TrackerAlignment_Upgrade2026_{tracker_version}_design_v1"
TrackerAlignmentErrorExtendedRcd = f"TrackerAlignmentErrorsExtended_Upgrade2026_{tracker_version}_design_v1"

process = cms.Process(f"createDesignAlignment{tracker_version}")

# Load the ideal Phase-2 XML Geometry
process.load(f"Configuration.Geometry.GeometryExtended{geom_suffix}{args.geometry}_cff")

# Load the Reconstruction Geometry (builds the C++ TrackerGeometry objects)
process.load(f"Configuration.Geometry.GeometryExtended{geom_suffix}{args.geometry}Reco_cff")

process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(1))

process.load("CondCore.CondDB.CondDB_cfi")
process.CondDB.connect = f"sqlite_file:{TrackerAlignmentRcd}.db"

process.PoolDBOutputService = cms.Service(
    "PoolDBOutputService",
    process.CondDB,
    toPut = cms.VPSet(
        cms.PSet(
            record = cms.string("TrackerAlignmentRcd"),
            tag = cms.string(TrackerAlignmentRcd),
        ),
        cms.PSet(
            record = cms.string("TrackerAlignmentErrorExtendedRcd"),
            tag = cms.string(TrackerAlignmentErrorExtendedRcd),
        ),
    ),
)

process.load("Alignment.TrackerAlignment.MisalignedTracker_cfi")
process.MisalignedTracker.saveToDbase = cms.untracked.bool(True)
process.esPreferMisalignedTracker = cms.ESPrefer("MisalignedTrackerESProducer", "MisalignedTracker")

# Forces the ESProducer above to actually run (and thus write to the DB) by
# requesting its product; nothing else in this process consumes TrackerGeometry.
process.get = cms.EDAnalyzer(
    "EventSetupRecordDataGetter",
    toGet = cms.VPSet(
        cms.PSet(
            record = cms.string("TrackerDigiGeometryRecord"),
            data = cms.vstring("TrackerGeometry"),
        )
    ),
    verbose = cms.untracked.bool(True),
)
process.p = cms.Path(process.get)
