import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing
import importlib

defaultGeometry = 'D110'
defaultTol      = 0.01
defaultGDML     = 0

# Setup options
options = VarParsing.VarParsing('standard')
options.register('geometry',
                 'D110',
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string,
                 f'The detector configuration name. Default is: {defaultGeometry}')
options.register('tol',
                 defaultTol,
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.float,
                 f'Overlap tolerance in mm. Default is: {defaultTol}')
options.register('resolution',
                 50000,
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.int,
                 'Number of random points sampled per volume. '
                 'Higher values find subtler overlaps.')
options.register('gdml',
                 defaultGDML,
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.int,
                 f'Set to 1 to export the geometry to a GDML file. Default is: {defaultGDML}')

options.parseArguments()

# Resolve geometry name
geomName  = 'Run4' + options.geometry

dictGeometry = importlib.import_module('Configuration.Geometry.dictRun4Geometry')
detectorVersionDict = {v: k for k, v in dictGeometry.detectorVersionDict.items()}

if options.geometry not in detectorVersionDict.keys():
    validGeometries = ", ".join(detectorVersionDict.keys())
    raise KeyError(f'Invalid geometry {geomName}. Must be one of: {validGeometries}')

# Resolve file and conditions
geomFile  = 'Configuration.Geometry.GeometryExtended' + geomName + 'Reco_cff'
baseName  = 'tracker' + geomName + 'DDD'

import Configuration.Geometry.defaultPhase2ConditionsEra_cff as _settings
GLOBAL_TAG, ERA = _settings.get_era_and_conditions(geomName)

print('Geometry Name:   ', geomName)
print('Geom file Name:  ', geomFile)
print('Base file Name:  ', baseName)
print('Global Tag Name: ', GLOBAL_TAG)
print('Era Name:        ', ERA)
print('Tolerance:       ', options.tol, 'mm')
print('Resolution:      ', options.resolution, 'points/volume')

process = cms.Process('TrackerOverlapCheck', ERA)

process.load(geomFile)
process.load('FWCore.MessageService.MessageLogger_cfi')

from SimG4Core.PrintGeomInfo.g4TestGeometry_cfi import *
process = checkOverlap(process)

# Geant4 overlap check configuration

process.g4SimHits.CheckGeometry = True

process.g4SimHits.G4CheckOverlap.OutputBaseName = cms.string(baseName)
process.g4SimHits.G4CheckOverlap.OverlapFlag    = cms.bool(True)
process.g4SimHits.G4CheckOverlap.Tolerance      = cms.double(options.tol)
process.g4SimHits.G4CheckOverlap.Resolution     = cms.int32(options.resolution)

# Check the full hierarchy so every tracker sub-volume is covered.
process.g4SimHits.G4CheckOverlap.Depth          = cms.int32(-1)

# NodeNames are G4Region names (RegionFlag=True). The tracker envelope regions are
# defined in Geometry/TrackerSimData/data/PhaseII/*/trackerProdCuts.xml and pixelProdCuts.xml:
#   TrackerDeadRegion      -> //Tracker (full tracker envelope)
#   TrackerOuterDeadRegion -> //Phase2OTBarrel, //Phase2OTForward
#   TrackerPixelDeadRegion -> //Phase2PixelBarrel, //Phase2PixelEndcap
# Sensor-level regions (TrackerOuterSensRegion, TrackerPixelSensRegion) are omitted
# to avoid writing thousands of per-sensor GDML files when gdml=1.
# When gdml=1, each matched physical volume is written to its own <pvname>.gdml file.
process.g4SimHits.G4CheckOverlap.RegionFlag     = cms.bool(True)
process.g4SimHits.G4CheckOverlap.NodeNames      = cms.vstring(
    'TrackerDeadRegion',
    'TrackerOuterDeadRegion',
    'TrackerPixelDeadRegion',
)

# Print detailed info for a specific physical or logical volume by name.
# Useful to cross-check a suspicious segment identified in the overlap log.
process.g4SimHits.G4CheckOverlap.PVname         = ''
process.g4SimHits.G4CheckOverlap.LVname         = ''

# Set gdml=1 to enable per-volume GDML export restricted to tracker envelope regions.
# Each matched physical volume is written to its own <pvname>.gdml file.
process.g4SimHits.G4CheckOverlap.gdmlFlag       = cms.bool(bool(options.gdml))

# Extra output files (empty string => disabled).
# Note: FileNameGDML is handled by G4CheckOverlap.gdmlFlag above, so leave this empty.
process.g4SimHits.FileNameField   = ''
process.g4SimHits.FileNameGDML    = ''
process.g4SimHits.FileNameRegions = ''
