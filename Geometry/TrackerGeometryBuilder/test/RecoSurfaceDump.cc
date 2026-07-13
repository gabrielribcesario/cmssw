// -*- C++ -*-
//
// Package:    Geometry/TrackerGeometryBuilder
// Class:      RecoSurfaceDump
//
/*
 Description:
   Dumps, for EVERY tracker DetId in the reconstruction geometry
   (TrackerDigiGeometryRecord -> TrackerGeometry), the *reco Surface*
   global position and 3x3 rotation matrix, as CSV, one row per DetId,
   sorted by rawId.

   Unlike Geometry/TrackerGeometryBuilder/test/ModuleInfo, this reads the
   position/rotation from det->surface() (i.e. AFTER alignment has been
   applied by TrackerDigiGeometryESModule), and is subdetector-agnostic
   (works for Phase-2 OT/pixel DetIds too). This makes the two CSV files
   trivially diff-able by rawId to localize where two geometry exports
   place the same module differently.

 Usage:
   see test/python/dumpRecoSurface_cfg.py
*/
//
// Author:  (generated for OT807 vs OT806 reco-surface diff)
//

#include <fstream>
#include <iomanip>
#include <string>
#include <vector>
#include <algorithm>

#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/one/EDAnalyzer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"

#include "Geometry/Records/interface/TrackerDigiGeometryRecord.h"
#include "Geometry/TrackerGeometryBuilder/interface/TrackerGeometry.h"
#include "Geometry/CommonDetUnit/interface/GeomDet.h"
#include "DataFormats/GeometrySurface/interface/Surface.h"
#include "DataFormats/DetId/interface/DetId.h"

class RecoSurfaceDump : public edm::one::EDAnalyzer<> {
public:
  explicit RecoSurfaceDump(const edm::ParameterSet&);
  void analyze(edm::Event const&, edm::EventSetup const&) override;

private:
  const std::string outFileName_;
  const bool unitsOnly_;  // if true, dump only DetUnits; else all dets (incl. Glued/Stack composites)
  edm::ESGetToken<TrackerGeometry, TrackerDigiGeometryRecord> geomToken_;
};

RecoSurfaceDump::RecoSurfaceDump(const edm::ParameterSet& ps)
    : outFileName_(ps.getUntrackedParameter<std::string>("outFileName", "RecoSurfaceDump.csv")),
      unitsOnly_(ps.getUntrackedParameter<bool>("unitsOnly", false)),
      geomToken_(esConsumes()) {}

void RecoSurfaceDump::analyze(const edm::Event&, const edm::EventSetup& iSetup) {
  const TrackerGeometry& geom = iSetup.getData(geomToken_);

  const auto& dets = unitsOnly_ ? geom.detUnits() : geom.dets();

  // collect (rawId, det*) so we can sort by rawId for a stable, diff-able order
  std::vector<std::pair<uint32_t, const GeomDet*> > entries;
  entries.reserve(dets.size());
  for (const auto* det : dets) {
    entries.emplace_back(det->geographicalId().rawId(), det);
  }
  std::sort(entries.begin(), entries.end(),
            [](auto const& a, auto const& b) { return a.first < b.first; });

  std::ofstream out(outFileName_, std::ios::out);
  out << std::setprecision(9);  // ~nm precision on cm-scale positions
  // header
  out << "rawid,subdet,x,y,z,r11,r12,r13,r21,r22,r23,r31,r32,r33\n";

  for (const auto& e : entries) {
    const GeomDet* det = e.second;
    const auto& surf = det->surface();
    const auto& p = surf.position();
    const auto& r = surf.rotation();

    out << e.first << ',' << det->geographicalId().subdetId() << ',' << p.x() << ',' << p.y() << ',' << p.z() << ','
        << r.xx() << ',' << r.xy() << ',' << r.xz() << ',' << r.yx() << ',' << r.yy() << ',' << r.yz() << ',' << r.zx()
        << ',' << r.zy() << ',' << r.zz() << '\n';
  }
  out.close();

  edm::LogInfo("RecoSurfaceDump") << "Wrote " << entries.size() << " DetId rows to " << outFileName_;
}

DEFINE_FWK_MODULE(RecoSurfaceDump);
