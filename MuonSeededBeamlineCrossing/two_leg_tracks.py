#!/usr/bin/env python3
import argparse
from collections import Counter
import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libDataFormatsTrackReco")

HIT_PREFIX = {0: "pix", 4: "ph2"}

def get_algo(a):
    return str(ROOT.reco.TrackBase.algoName(a))

def get_layer_name(pfx, subdet, layer):
    if pfx == "ph2":
        return "OT-TB" if subdet == 5 else "OT-TEDD"
    elif subdet == 1:
        return "TBPX"
    else:
        return "TFPX" if layer <= 8 else "TEPX"

def hits_of(idxs, types):
    return [(HIT_PREFIX[t], h) for h, t in zip(idxs, types) if t in HIT_PREFIX]

def hit_owner(ev, pfx, h):
    sims = {ev.simhit_simTrkIdx[s] for s in getattr(ev, f"{pfx}_simHitIdx")[h]}
    return sims.pop() if len(sims) == 1 else None

def hit_label(ev, pfx, h):
    subdet, lay, z = (getattr(ev, f"{pfx}_{k}")[h] for k in ("subdet", "layer", "z"))
    return f"{get_layer_name(pfx, subdet, lay)}{lay}@z={z:+.1f}(sim{hit_owner(ev, pfx, h)})"

def print_muon(ev, i):
    trks = [(j, get_algo(ev.trk_algo[j])) for j in ev.sim_trkIdx[i]]
    vz = ev.simvtx_z[ev.sim_parentVtxIdx[i]]
    print(f"    sim[{i}] pdg={ev.sim_pdgId[i]:+3} pt={ev.sim_pt[i]:8.2f} eta={ev.sim_eta[i]:+6.3f} "
          f"phi={ev.sim_phi[i]:+6.3f} vz={vz:+6.2f} nSimHit={ev.sim_nValid[i]:2} matched={trks}")

def crossings(ev, hits):
    owned = [(p, h) for p, h in hits if hit_owner(ev, p, h) is not None]
    return [(hit_label(ev, *a), hit_label(ev, *b)) for a, b in zip(owned, owned[1:])
            if hit_owner(ev, *a) != hit_owner(ev, *b)]

def print_track(ev, j, ind="    "):
    print(f"{ind}trk[{j}] {get_algo(ev.trk_algo[j]):20} q={ev.trk_q[j]:+2} pt={ev.trk_pt[j]:8.2f} "
          f"eta={ev.trk_eta[j]:+6.3f} phi={ev.trk_phi[j]:+6.3f} dz={ev.trk_dz[j]:+6.2f} "
          f"nValid={ev.trk_nValid[j]:2} nPix={ev.trk_nPixel[j]:2} nOT={ev.trk_nStrip[j]:2} "
          f"matchedSim={list(ev.trk_simTrkIdx[j])}")

def scan(path, min_hits, eta_max):
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        return print(f"Cannot open {path}")

    t = f.Get("trackingNtuple/tree")
    if not t:
        return print(f"{path} missing trackingNtuple/tree")

    print("".join(["\n", "="*100, "\n\n", f"{path}: {t.GetEntries()} events"]))
    n_mu = n_lost = n_twoleg = 0

    for ev in t:
        # Find signal muons in acceptance
        mus = [i for i in range(ev.sim_pdgId.size())
               if abs(ev.sim_pdgId[i]) == 13 and ev.sim_bunchCrossing[i] == 0 
               and ev.sim_event[i] == 0 and abs(ev.sim_eta[i]) <= eta_max]
        n_mu += len(mus)

        for i in mus:
            if not ev.sim_trkIdx[i]:
                n_lost += 1

        for j in range(ev.trk_pt.size()):
            hits = hits_of(ev.trk_hitIdx[j], ev.trk_hitType[j])
            owners = Counter(hit_owner(ev, p, h) for p, h in hits)
            legs = [k for k in owners if k in mus and owners[k] >= min_hits]

            if len(legs) < 2:
                continue
            n_twoleg += 1

            print(f"\n  event {ev.event}: track from {len(legs)} muons")
            print_track(ev, j)
            print(f"    hits per sim: {dict(owners.most_common())}")
            for a, b in crossings(ev, hits):
                print(f"    crossing: {a} -> {b}")

            for l in legs:
                print_muon(ev, l)

            s = ev.trk_seedIdx[j]
            if s >= 0:
                shits = hits_of(ev.see_hitIdx[s], ev.see_hitType[s])
                slabs = [hit_label(ev, p, h) for p, h in shits]
                sown = {hit_owner(ev, p, h) for p, h in shits}
                print(f"    seed[{s}] {get_algo(ev.see_algo[s])} from sim{sorted(x for x in sown if x is not None)}: {' '.join(slabs)}")

            print("    track hits along the trajectory:")
            for p, h in hits:
                print(f"      {hit_label(ev, p, h)}")

            others = {j2 for i in legs for j2 in ev.sim_trkIdx[i]}
            if others:
                print("    other tracks matched to these muons:")
                for j2 in sorted(others): print_track(ev, j2, "      ")

    print(f"\n  muons (|eta| <= {eta_max}): {n_mu}, without a matched track: {n_lost}")
    print(f"  tracks with >= {min_hits} hits from two muons: {n_twoleg}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Find tracks built from the hits of two back-to-back muons.")
    p.add_argument("files", nargs="+")
    p.add_argument("--min-hits", type=int, default=4)
    p.add_argument("--eta-max", type=float, default=4.0)
    args = p.parse_args()

    for f in args.files:
        scan(f, args.min_hits, args.eta_max)