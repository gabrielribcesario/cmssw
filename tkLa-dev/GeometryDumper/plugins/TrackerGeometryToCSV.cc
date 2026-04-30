#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/one/EDAnalyzer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "Geometry/Records/interface/TrackerDigiGeometryRecord.h"
#include "Geometry/TrackerGeometryBuilder/interface/TrackerGeometry.h"
#include "DataFormats/DetId/interface/DetId.h"

#include <iostream>
#include <fstream>
#include <string>

class TrackerGeometryToCSV : public edm::one::EDAnalyzer<> {
public:
  explicit TrackerGeometryToCSV(const edm::ParameterSet&);
  ~TrackerGeometryToCSV() override = default;

private:
  void analyze(const edm::Event&, const edm::EventSetup&) override;

  edm::ESGetToken<TrackerGeometry, TrackerDigiGeometryRecord> geomToken_;
  std::string outputFile_;
};

TrackerGeometryToCSV::TrackerGeometryToCSV(const edm::ParameterSet& iConfig)
    : geomToken_(esConsumes()), outputFile_(iConfig.getParameter<std::string>("outputFile")) {}

void TrackerGeometryToCSV::analyze(const edm::Event& iEvent, const edm::EventSetup& iSetup) {
  const auto& trackerGeom = iSetup.getData(geomToken_);

  std::ofstream csvFile(outputFile_);

  csvFile << "DetId,Subdetector,X,Y,Z,RotXX,RotXY,RotXZ,RotYX,RotYY,RotYZ,RotZX,RotZY,RotZZ\n";

  for (const auto& det : trackerGeom.dets()) {
    DetId detId = det->geographicalId();

    // Tracker-only components
    if (detId.det() != DetId::Tracker) continue;

    const auto& pos = det->position();
    const auto& rot = det->rotation();

    csvFile << detId.rawId() << "," << detId.subdetId() << ","
            << pos.x() << "," << pos.y() << "," << pos.z() << ","
    // Each column represents a local axis in global coordinates
            << rot.xx() << "," << rot.yx() << "," << rot.zx() << ","
            << rot.xy() << "," << rot.yy() << "," << rot.zy() << ","
            << rot.xz() << "," << rot.yz() << "," << rot.zz() << "\n";
  }
  csvFile.close();

  std::cout << "Geometry successfully dumped to " << outputFile_ << std::endl;
}

DEFINE_FWK_MODULE(TrackerGeometryToCSV);
