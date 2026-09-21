# Setting up the environment

```bash
# pwd = $CMSSW_BASE/src

git remote add gabe https://github.com/gabrielribcesario/cmssw.git

git fetch gabe

git switch -c local-ticl-vector-bug-reproducer gabe/ticl-vector-bug-reproducer

git cms-addpkg RecoHGCal/TICL \
               TICLCandidateProducerBugReproducer

# Apply tmp fix
git apply TICLCandidateProducerBugReproducer/ticl-oob.patch
```

# TICLCandidateProducer.cc

This out-of-bounds read triggers the `TICLCandidateProducer.cc` crash in step 3, on any sample where the muon interpretation pass consumes tracksters (T37, i.e. `ExtendedRun4D112`).

To trigger it, use the exact following `runTheMatrix.py` command on stock `CMSSW_20_1_0_pre3`:

```bash
runTheMatrix.py -w upgrade -l 30410 --nEvents 100 -t 16 -j 1 --maxSteps 4
```

It's post-[#51725](https://github.com/cms-sw/cmssw/pull/51725), so it won't crash on `CMSSW_20_0_X`: `linkedResultTracksters` is declared but never indexed and never `put` into the event, so no OOB access.

TL;DR at the bottom:

1. `TICLCandidateProducer` keeps `resultTracksters` and `linkedResultTracksters` index-parallel: entry $i$ of the latter lists the input tracksters merged into output trackster $i$ of the former.

2. The producer emits the `linkedTracksters` product by indexing `linkedResultTracksters` with a `resultTracksters` index (`TICLCandidateProducer.cc:445,458`), over a range set by `maskTracksters.size() == resultTracksters->size()` (`TICLCandidateProducer.cc:413,453`).

3. The muon pass runs first (`TICLCandidateProducer.cc:379-380`). `MuonInterpretationAlgo::makeCandidates` appends to `resultTracksters` (`MuonInterpretationAlgo.cc:99`) but never writes its `linkedResultTracksters` parameter, i.e.:

    ```cpp
    resultTracksters.size() == M
    linkedResultTracksters.size() == 0
    ```

4. The general pass double-pushes for a track with exactly one linked trackster: inside the `size() == 1` branch (`GeneralInterpretationAlgo.cc:383`) and again after the `if`/`else` that already covers both (`GeneralInterpretationAlgo.cc:403`), i.e. per such track:

    ```cpp
    resultTracksters.size() += 1
    linkedResultTracksters.size() += 2
    ```

5. With $G$ general tracksters the sizes are $M + G$ vs. $G + S$, so `std::vector::operator[]` reads past the end whenever $M > S$.

6. `(*linkedResultTracksters)[i]` returns a reference to what it assumes is a `std::vector` (`{begin, end, end_of_capacity}` header), but the OOB read feeds `push_back` 24 bytes of garbage as if it were a live vector. The copy ctor takes `n = (end - begin) / sizeof(unsigned int)`: since `begin` and `end` are garbage one of two things happen, depending on the stream:

    1. Huge `n` -> huge allocation -> `std::bad_alloc`.
    
    2. `begin` is not mapped -> faults in `memmove` -> `SIGSEGV`.

TL;DR: `TICLCandidateProducer` indexes `linkedResultTracksters` with `resultTracksters` indices, which requires the two to be index-parallel. `MuonInterpretationAlgo` appends to `resultTracksters` without ever filling its `linkedResultTracksters` parameter, and `GeneralInterpretationAlgo` double-pushes for single-trackster tracks, so they never are. The unchecked `operator[]` then yields a garbage `std::vector` header, whose bogus size throws `std::bad_alloc` and whose bogus pointer segfaults in `memmove` at `TICLCandidateProducer.cc:458`. The entries are also misaligned by $M$, so the emitted product is wrong even when it doesn't crash.

Crash log at `TICLCandidateProducerBugReproducer/step3_FourMuExtendedPt1_200+Run4D112.log`.

Temporary fix:

```cpp
@@ -97,6 +97,8 @@ void MuonInterpretationAlgo::makeCandidates(const Inputs &input,
       }
       resultCandidate[iTrack] = static_cast<int>(resultTracksters.size());
       resultTracksters.push_back(muonTrackster);
+      // Keep linkedResultTracksters index-parallel to resultTracksters
+      linkedResultTracksters.push_back(nearby);
     } else {
       resultCandidate[iTrack] = -1;  // muon with no HGCAL deposit: track-only candidate
     }
```

```cpp
@@ -380,7 +380,6 @@ void GeneralInterpretationAlgo::makeCandidates(const Inputs &input,
         auto tracksterId = trackstersInTrackIndices[iTrack][0];
         resultCandidate[iTrack] = resultTracksters.size();
         resultTracksters.push_back(input.tracksters[tracksterId]);
-        linkedResultTracksters.push_back(trackstersInTrackIndices[iTrack]);
       } else {
         // in this case mergeTracksters() clears the pid probabilities and the regressed energy is not set
         // TODO: fix probabilities when CNN will be splitted
```

```cpp
@@ -426,6 +426,11 @@ void TICLCandidateProducer::produce(edm::Event &evt, const edm::EventSetup &es)
     if (tracksterId >= 0) {
       tracksterPtr = edm::Ptr<Trackster>(resultTracksters_h, tracksterId);
       maskTracksters[tracksterId] = false;
+      // Keep the linkedTracksters product parallel to resultCandidates
+      linkedTracksters->push_back((*linkedResultTracksters)[tracksterId]);
+    } else {
+      // track-only muon: no HGCAL deposit to link
+      linkedTracksters->emplace_back();
     }
     TICLCandidate muonCandidate(trackPtr, tracksterPtr);
     muonCandidate.setPdgId(13 * tk.charge());
```
