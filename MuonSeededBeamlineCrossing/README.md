# Muon-seeded tracks built across the beamline

A μ⁺μ⁻ pair with the same pT, back to back from one vertex, is reconstructed as one track spanning
the detector, matched to neither muon, and both muons are lost. In workflow 30410.0 with a smeared
vertex this is an efficiency dip at $2.4<|\eta|<2.6$; the same mechanism also fires at $|\eta|\approx0.3$.

# Setting up the environment

```bash
# pwd = $CMSSW_BASE/src

git remote add gabe https://github.com/gabrielribcesario/cmssw.git

git fetch gabe

git switch -c local-muon-seeded-beamline-cross gabe/muon-seeded-beamline-cross

git cms-addpkg RecoTracker/CkfPattern \
               RecoTracker/IterativeTracking \
               Validation/RecoTrack

git apply MuonSeededBeamlineCrossing/muonSeeded_no_beamline_crossing.patch
```

The Phase-2 `trackingNtuple.clusterMasks` update and the T36, T37 & T38 aligmment payload fix are already on the branch.

# muonSeededStepInOut / muonSeededStepOutIn

1. Opposite charge w/ same momentum and origin creates two legs that look like a single, continuous helix.

2. `initialStep` reconstructs both muons correctly, each track carrying only its own muon's hits
   (from `customiseTrackingNtupleMergeIters`).

3. `MuonReSeeder` seeds from a muon's own tracker track, keeping its innermost 5 layers
   (`inOutSeedsFromTrackerMuons_cfi.py:8`). `GroupedCkfTrajectoryBuilder` builds outward and then also
   inward of the seed (`MuonSeededStep_cff.py:76`: `minNrOfHitsForRebuild = 2`,
   `requireSeedHitsInRebuild = True`, `keepOriginalIfRebuildFails = True`).

4. The inward search continues beyond the point of closest approach with small $\chi^2$ onto the partner's
   hits because they are on the same helix. Barrel layers span ±z, so they bridge the two Z halves. In the 
   endcap cases the bridge is TBPX-L1; at central $\eta$ it is the innermost OT barrel layer.

5. `--beamspot NoSmear` -> $v_z=0$: the legs are mirror images and there is no bridge. $v_z\neq0$ breaks the symmetry.

TL;DR: the muon-seeded steps extend a candidate backwards through its own point of closest approach to
the beamline, onto the partner of a back-to-back pair, which lies on the same helix. Barrel layers span
both z sides and provide the crossing point. The resulting two-muon track is matched to neither muon and
outscores both correct `initialStep` tracks in the duplicate removal, so both muons count as lost.

# Reproducing

1000 events of the four-muon gun, Phase-2 D112. The commands are in each variant's `cmdLog`, run from
its own directory; the two differ only in step1's `--beamspot`, `HLLHC` against `NoSmear`. Step3 carries
`--customise Validation/RecoTrack/customiseTrackingNtuple.customiseTrackingNtuple`, which drops every
output module, so it writes only `trackingNtuple.root`.

Then:

```bash
python3 two_leg_tracks.py <dir>/trackingNtuple.root [more.root ...] [--min-hits N] [--max-eta E]
```

It reports every track whose hits come from two signal muons (`--min-hits N`, default 4), e.g.:

```
event 691: track from 2 muons
    trk[2] muonSeededStepInOut  q=-1 pt=  136.87 eta=+2.575 ... nValid=34 ... matchedSim=[]
    hits per sim: {2: 18, 3: 16}
    crossing: TBPX1@z=-19.4(sim2) -> TFPX1@z=+24.2(sim3)
    sim[2] pdg=-13 pt=  130.68 eta=-2.575 phi=-2.337 vz=+1.81 nSimHit=18 matched=[]
    sim[3] pdg=+13 pt=  130.68 eta=+2.575 phi=+0.805 vz=+1.81 nSimHit=16 matched=[]
    seed[72] muonSeededStepInOut from sim[3]: TFPX1@z=+24.2(sim3) ...
    track hits along the trajectory:
      OT-TEDD5@z=-264.4(sim2)
      ...
      OT-TEDD5@z=+262.9(sim3)
```

- `nValid=34`: about twice a muon's hit count, split `{2: 18, 3: 16}` between two `TrackingParticles`;
- `matchedSim=[]` on the track and `matched=[]` on both muons: one track, two lost muons;
- the two muons are a pair: same $p_T$, opposite $\eta$, $\varphi$ differing by $\pi$, same $v_z$;
- `crossing:` is where the owning particle changes; in the hit list z then runs from one end of the
  detector to the other.
