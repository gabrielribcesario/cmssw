/* overlap_check.C --- Filter and visually highlight geometry overlaps

   DESCRIPTION:

   The `overlap_check` macro reads a geometry file compatible with the
   ROOT TGeoManager infrastructure, evaluates geometric overlaps, filters 
   out structural/service components, and exports an isolated view of the
   problematic areas.

   Specifically, it executes the following operations:
     1. Imports the geometry and executes `TGeoManager::CheckOverlaps`.
     2. Filters out volumes matching "service" or "support" patterns unless
        explicitly instructed otherwise.
     3. Isolates and highlights offending volumes using the color scheme:
          - Extruding daughters and overlapping siblings: Green (Opaque)
          - Container volumes (mother of an extrusion):   Blue (Translucent)
     4. Transforms local overlap points into global coordinates.
     5. Saves the resulting filtered geometry tree and global overlap markers
        into a self-contained ROOT file for interactive viewing.

   SYNTAX:

     root -l 'overlap_check.C("GEOM", OVLP, KEEP_SERVICES, "SAMPLING")'

   ARGUMENTS:

     GEOM            Path to the geometry file (e.g., "detector.gdml").
     OVLP            Overlap tolerance threshold in centimeters.
                     Default value is 0.01 cm.
     KEEP_SERVICES   Boolean flag. If true, preserves volumes containing
                     "service" or "support" in their names. Default is false.
     SAMPLING        Optional sampling directive of the form "s[n samples]",
                     e.g. "s10000". Forwarded verbatim as the `option`
                     argument of TGeoManager::CheckOverlaps, switching it
                     from the default mesh-based check to a sampling-based
                     one with the given number of sample points. Empty by
                     default (mesh-based check).

   EXAMPLES:

     Run a default overlap check with 100 micron tolerance:
       $ root -l 'overlap_check.C("detector.gdml")'

     Run with a strict 10 micron tolerance and preserve service structures:
       $ root -l 'overlap_check.C("detector.gdml", 0.001, true)'

     Run with 100 micron tolerance and a sampling-based check using
     50000 sample points per volume:
       $ root -l 'overlap_check.C("detector.gdml", 0.01, false, "s50000")'

   OUTPUT AND VIEWING:

     The macro produces a file named `overlap_scene.root`. To view the output,
     upload this file to the online JSROOT browser (https://root.cern/js/). 
     You can interact with the objects as follows:
       - Expand `filtered_geometry` to browse the isolated 3D layout.
       - Select `Overlaps` to evaluate individual intersections.
     Alternatively:
       - Right-click `filtered_geometry` and choose `Draw` to draw all problematic volumes.
       - Right-click `overlap_markers` and choose `Superimpose` to project
         the red overlap markers onto the geometry. */

#include <cstdio>
#include <cstddef>
#include <set>
#include <map>
#include <vector>
#include <array>

#include "TString.h"
#include "TGeoManager.h"
#include "TGeoVolume.h"
#include "TGeoNode.h"
#include "TGeoOverlap.h"
#include "TObjArray.h"
#include "TIterator.h"
#include "TPolyMarker3D.h" 
#include "TGeoMatrix.h" 

void overlap_check(const char* geom, double ovlp = 0.01, bool keep_services = false, const char* sampling = "") {
  TGeoManager* geo = TGeoManager::Import(geom);
  if (!geo) {
    std::printf("Could not import %s\n", geom);
    return;
  }

  // Draw every visible volume (not leaves-only)
  geo->SetVisOption(0);

  // Let ROOT find the overlaps itself. The mesh-based check (no sampling option)
  // covers both overlaps and extrusions; the sampling option "sN" skips
  // extrusions, which would miss every mother-volume overlap.
  geo->CheckOverlaps(ovlp, sampling);
  geo->PrintOverlaps();

  // Create a master 3D marker object to hold the overlap points
  TPolyMarker3D* ov_markers = new TPolyMarker3D();
  ov_markers->SetMarkerColor(kRed);
  ov_markers->SetMarkerStyle(kFullCircle);
  ov_markers->SetMarkerSize(0.5);

  // Map to store overlap points in the local coordinate system of the first volume
  std::map<TGeoVolume*, std::vector<std::array<double, 3>>> local_ov_pts;

  // Collect the volumes involved, splitting offenders from containers.
  std::set<TString> offenders;    // extruding daughter / overlapping siblings
  std::set<TString> containers;   // mother of an extrusion
  TObjArray* ovs = geo->GetListOfOverlaps();
  TIter next(ovs);
  TGeoOverlap* ov;
  int kept = 0;

  auto is_service = [](const TString& n) -> bool {
    // Service/support can appear anywhere in the name and in any case
    return n.Contains("service", TString::kIgnoreCase) ||
           n.Contains("support", TString::kIgnoreCase);
  };

  while ((ov = (TGeoOverlap*) next())) {
    TGeoVolume* v1 = ov->GetFirstVolume();
    TGeoVolume* v2 = ov->GetSecondVolume();
    if (!v1 || !v2) continue;

    TString n1 = v1->GetName();
    TString n2 = v2->GetName();
    if (!keep_services && (is_service(n1) || is_service(n2))) continue;
    ++kept;

    // Convert overlap points from the mother's frame into v1's local frame
    if (TPolyMarker3D* pm = ov->GetPolyMarker()) {
      Double_t pt[3], loc[3]; 
      const TGeoMatrix* m1 = ov->GetFirstMatrix();
      for (int i = 0; i < pm->Size(); ++i) {
        pm->GetPoint(i, pt[0], pt[1], pt[2]);
        if (m1) {
          m1->MasterToLocal(pt, loc); // Inverts the matrix: Master (Mother) -> Local (v1)
          local_ov_pts[v1].push_back({loc[0], loc[1], loc[2]});
        }
      }
    }

    if (ov->IsExtrusion()) {  // "v1 extruded by: .../v2"  -> v1 is the container
      containers.insert(n1);
      offenders.insert(n2);
    } else {                  // "v1 overlapping v2"       -> both offenders
      offenders.insert(n1);
      offenders.insert(n2);
    }
  }

  std::printf("Overlaps kept after service/support filter: %d  (offenders=%zu containers=%zu)\n",
    kept, offenders.size(), containers.size());

  // Show ONLY the overlap volumes; hide everything else explicitly
  TIter it(geo->GetListOfVolumes());
  TGeoVolume* v;
  while ((v = (TGeoVolume*) it())) {
    TString name = v->GetName();
    if (offenders.count(name)) {
      v->SetVisibility(kTRUE);
      v->SetLineColor(kGreen);
      v->SetTransparency(0);
    } else if (containers.count(name)) {
      v->SetVisibility(kTRUE);
      v->SetLineColor(kAzure-4);
      v->SetTransparency(80);
    } else {
      v->SetVisibility(kFALSE);
    }
  }

  TGeoVolume* top = geo->GetTopVolume(); 

  // Manually add markers for the Top Volume (since the iterator skips it)
  if (local_ov_pts.count(top)) {
    for (const auto& pt : local_ov_pts[top]) {
      ov_markers->SetNextPoint(pt[0], pt[1], pt[2]);
    }
  }

  // Iterate through all nodes. Convert local markers to global
  TGeoIterator nit(top); 
  TGeoNode* nd;
  while ((nd = nit.Next())) {
    TGeoVolume* node_vol = nd->GetVolume();

    // If this node corresponds to a volume with overlaps, apply its global matrix
    if (local_ov_pts.count(node_vol)) {
      const TGeoMatrix* gmat = nit.GetCurrentMatrix();
      Double_t loc[3], glob[3];
      for (const auto& pt : local_ov_pts[node_vol]) {
        loc[0] = pt[0]; loc[1] = pt[1]; loc[2] = pt[2];
        gmat->LocalToMaster(loc, glob); // Applies the global transformation path
        ov_markers->SetNextPoint(glob[0], glob[1], glob[2]);
      }
    }
  }

  // Hide the enclosing shell
  top->SetVisibility(kFALSE);

  TCanvas* c1 = new TCanvas("c1", "Overlap Viewer", 2048, 2048);
  top->Draw("");

  // Overlay the properly aligned global markers
  if (ov_markers->Size() > 0) {
    ov_markers->Draw("same");
  }

  TFile* fOut = new TFile("overlap_scene.root", "RECREATE");
  geo->Write("filtered_geometry");
  ov_markers->Write("overlap_markers");
  fOut->Close();

  std::printf("Scene saved to 'overlap_scene.root'.\n");
}