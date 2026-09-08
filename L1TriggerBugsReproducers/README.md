# Setting up the environment

```bash
# pwd = $CMSSW_BASE/src

git remote add gabe https://github.com/gabrielribcesario/cmssw.git

git fetch gabe

git switch -c local-l1trigger-bugs-reproducers gabe/l1trigger-bugs-reproducers

git cms-addpkg Configuration/AlCa Configuration/Geometry Configuration/PyReleaseValidation Configuration/StandardSequences \
               Geometry/TrackerCommonData Geometry/TrackerRecoData Geometry/CMSCommonData Geometry/TrackerSimData \
               L1Trigger/TrackFindingTracklet L1Trigger/TrackTrigger \
               tkLa-dev/DesignAlignment \
               L1TriggerBugsReproducers
```

# InputRouter.cc

This seed injection triggers the `InputRouter.cc` crash in step 2, on a TB2S-L5 module (T37, i.e. OT v8.0.6).

To trigger it, use the exact following `runTheMatrix.py` command on stock `CMSSW_20_0_0_patch1`:

```bash
runTheMatrix.py -w upgrade -l 30424 --nEvents 100 -t 16 -j 1 \
  --command "--customise L1TriggerBugsReproducers/InputRouter/injectSimHitsSeed.injectSimHitsSeed"
```

The mechanism seems to be the following, TL;DR at the bottom:

1. The tracker's `XY` plane is divided into 9 overlapping nonants. For the Outer Barrel L5, each nonant is divided into 4 sub-regions (`nbitsallstubs = 2`).
2. Every stub carries two digitized $\varphi$ words: `phi_` and the bend-corrected `phicorr_`. Both are initialized to the same value in `Stub.cc:67-68`.
3. `phicorr_` is shifted by the bend correction only in the barrel, when projecting the stub towards the barrel layer's nominal radius (`Sector.cc:71-78`, `Stub.cc:141-149`).
4. `InputRouter` routes on `phicorr_` (`InputRouter.cc:64-67`).
5. The wiring is built from the uncorrected geometric span: TrackletConfigBuilder::setDTCphirange computes each DTC's $\varphi$ range as the union over its modules' geometric $\varphi$ spans.
6. `TrackletConfigBuilder.cc:1428-1452` instantiates memory only for sub-regions that overlap this span, i.e. only the uncorrected region is guaranteed to be served.

TL;DR: `InputRouter` routes stubs by bend-corrected (`phicorr`), but the DTC -> InputLink wiring is built from the module's raw geometric $\varphi$ span, with no margin for that correction. A low-pT stub landing 0.326° above a $\varphi$-region boundary is bend-corrected 0.332° downward, ending up 0.006° below it - in a sub-region for which its DTC has no InputLink memory. `iadd == 0`, so `assert(false)` at `InputRouter.cc:82` fires.

Crash log at `L1TriggerBugsReproducers/InputRouter/step2_TTbar_13+Run4D112.log`.

Debugging info log at `L1TriggerBugsReproducers/InputRouter/debugging_info_step2_TTbar_13+Run4D112.log`.

Temporary fix:

```cpp
@@ -75,6 +75,19 @@ void InputRouter::execute() {
       }
     }
     if (not settings_.reduced()) {
+      // Fallback: If bend correction pushes a stub into an unwired phi region, route 
+      // using the uncorrected raw phi (which is always wired) to avoid dropping it
+      if (iadd == 0) {
+        const FPGAWord& iphiUncorr = stub->phi();
+        unsigned int iphiposUncorr = iphiUncorr.value() >> (iphiUncorr.nbits() - settings_.nbitsallstubs(layerdisk));
+        std::pair<unsigned int, unsigned int> layerphiregUncorr(layerdisk, iphiposUncorr);
+        for (auto& irstubmem : irstubs_) {
+          if (layerphiregUncorr == irstubmem.first) {
+            irstubmem.second->addStub(stub);
+            iadd++;
+          }
+        }
+      }
       // Verbose error message to debug crash.
       if (iadd != 1) {
         edm::LogError("Tracklet") << "Executing " << name_ << " : region (layer,phi) = (" << layerdisk << ", "
```

# SensorModule.cc

Run the following `runTheMatrix.py` workflow from `edfe8f0`. It uses a new Outer Tracker geometry OT v8.0.7.

```bash
runTheMatrix.py -w upgrade -l 38824 --nEvents 100 -t 16 -j 1
```

OT v8.0.7 is like OT v8.0.6 but with fixed module orientation in TB2S and TBPS (flat and tilted sections). For more details see https://indico.cern.ch/event/1668858/contributions/7094641/attachments/3275772/5852749/mersi_20251104_tklayout_updates%20(1).pdf, slides 32-44.

1. `signRow_` is derived from the geometry (`SensorModule.cc:62`, `plane.rotation().x()`) and so already tracks a 180° in-plane yaw.
2. `signCol_` and `signBend_` are hardcoded (`SensorModule.cc:63-66`).
3. A yaw reverses both row and column, so on a yawed module `signCol_` is left stale.
4. The column coordinate is reversed -> `d_ = r + y*sinTilt` gets the wrong slope.
5. On tilted modules that shifts the digitized $\varphi$ by ~5–10 mrad, which is greater than the 1 mrad tolerance (`MatchProcessor.cc:519`).
6. Flat modules pass because `sinTilt = 0`.

Crash log at `L1TriggerBugsReproducers/SensorModule/step2_TTbar_13+Run4D112.log`.

Debugging info log at `L1TriggerBugsReproducers/SensorModule/debugging_info_step2_TTbar_13+Run4D112.log`.

Temporary fix:

```cpp
@@ -60,10 +60,12 @@ namespace tt {
     layerId_ = layer + setup->offsetLayerId() + (barrel_ ? 0 : setup->offsetLayerDisks());
     // TTStub row needs flip of sign
     signRow_ = std::signbit(deltaPhi(plane.rotation().x().phi() - pos0.phi()));
+    // A 180 deg in-plane (yaw) flip reverses local row and column
+    const bool barrelYawFlipped = barrel_ && (signRow_ != flipped_);
     // TTStub col needs flip of sign
-    signCol_ = !barrel_ && !side_;
+    signCol_ = (!barrel_ && !side_) != barrelYawFlipped;
     // TTStub bend needs flip of sign
-    signBend_ = barrel_ || (!barrel_ && side_);
+    signBend_ = (barrel_ || (!barrel_ && side_)) != barrelYawFlipped;
     // determing sensor type
     if (barrel_ && psModule_)
       type_ = BarrelPS;
```