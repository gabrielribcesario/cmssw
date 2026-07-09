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

outputFile = "".join([geom_suffix, args.geometry, "_", tracker_version, ".csv"])

process = cms.Process("GEOMDUMP")

# Load the ideal Phase-2 XML Geometry
geometryExtended = "".join(["Configuration.Geometry.GeometryExtended", geom_suffix, args.geometry, "_cff"])
process.load(geometryExtended) 

# Load the Reconstruction Geometry (builds the C++ TrackerGeometry objects)
geometryExtendedReco = "".join(["Configuration.Geometry.GeometryExtended", geom_suffix, args.geometry, "Reco_cff"])
process.load(geometryExtendedReco)

# Use zero-state alignment
process.load("Alignment.CommonAlignmentProducer.FakeAlignmentSource_cfi")
process.preferFakeAlign = cms.ESPrefer("FakeAlignmentSource")

# Single null event
process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(1))

# Call the TrackerGeometryToCSV plugin
process.geomDumper = cms.EDAnalyzer("TrackerGeometryToCSV", outputFile=cms.string(outputFile))

process.p = cms.Path(process.geomDumper)