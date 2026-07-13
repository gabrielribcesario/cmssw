#!/usr/bin/env python3
"""Diff two RecoSurfaceDump CSVs by rawId.

For each DetId present in both files, compare the reco Surface position (x,y,z)
and 3x3 rotation matrix. Report every DetId whose position or orientation
differs beyond tolerance -- that set is exactly where reco can lose hits.

Also prints a per-subdetector breakdown so you can confirm the prediction:
    endcap surfaces match; pixel-barrel / OT surfaces differ.

Phase-2 subdetId() meaning (DetId.subdetId(), 1-based):
    1 = P2 Pixel Barrel   2 = P2 Pixel Endcap
    4 = P2 OT Endcap (TID slot)   5 = P2 OT Barrel (TOB slot)

Usage:
    diffRecoSurface.py surf_OT806.csv surf_OT807.csv [--postol 1e-4] [--rottol 1e-6]
"""
import argparse
import csv
import math

SUBDET_NAME = {1: "P2PXB", 2: "P2PXEC", 3: "sub3", 4: "P2OTEC", 5: "P2OTB", 6: "sub6"}


def load(path):
    rows = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            rows[int(row["rawid"])] = row
    return rows


def fdiff(a, b, keys):
    return max(abs(float(a[k]) - float(b[k])) for k in keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("good", help="reference CSV (e.g. OT806/good export)")
    ap.add_argument("bad", help="CSV under test (e.g. OT807/broken export)")
    ap.add_argument("--postol", type=float, default=1e-4, help="position tol [cm] (default 1um)")
    ap.add_argument("--rottol", type=float, default=1e-6, help="rotation matrix element tol")
    ap.add_argument("--list", action="store_true", help="print every differing rawId")
    args = ap.parse_args()

    g, b = load(args.good), load(args.bad)
    gk, bk = set(g), set(b)

    only_good, only_bad = gk - bk, bk - gk
    common = gk & bk

    poskeys = ("x", "y", "z")
    rotkeys = ("r11", "r12", "r13", "r21", "r22", "r23", "r31", "r32", "r33")

    per_sub = {}  # subdet -> [n_total, n_pos_diff, n_rot_diff, max_pos, max_rot]
    diffs = []
    for raw in common:
        rg, rb = g[raw], b[raw]
        sub = int(rg["subdet"])
        dp = fdiff(rg, rb, poskeys)
        dr = fdiff(rg, rb, rotkeys)
        s = per_sub.setdefault(sub, [0, 0, 0, 0.0, 0.0])
        s[0] += 1
        pos_bad = dp > args.postol
        rot_bad = dr > args.rottol
        if pos_bad:
            s[1] += 1
        if rot_bad:
            s[2] += 1
        s[3] = max(s[3], dp)
        s[4] = max(s[4], dr)
        if pos_bad or rot_bad:
            diffs.append((raw, sub, dp, dr))

    print("=== RecoSurface diff: %s (good) vs %s (bad) ===" % (args.good, args.bad))
    print("common DetIds: %d   only-good: %d   only-bad: %d"
          % (len(common), len(only_good), len(only_bad)))
    print("tolerances: pos=%g cm  rot=%g\n" % (args.postol, args.rottol))

    print("%-8s %8s %10s %10s %14s %14s" %
          ("subdet", "nDetId", "posDiff", "rotDiff", "maxdPos[cm]", "maxdRot"))
    for sub in sorted(per_sub):
        n, npos, nrot, mp, mr = per_sub[sub]
        print("%-8s %8d %10d %10d %14.3e %14.3e"
              % (SUBDET_NAME.get(sub, str(sub)), n, npos, nrot, mp, mr))

    print("\nTotal DetIds differing (pos or rot): %d" % len(diffs))
    if only_good or only_bad:
        print("WARNING: DetId sets differ -- geometries are not the same set of modules.")

    if args.list:
        print("\nrawid,subdet,dPos_cm,dRot")
        for raw, sub, dp, dr in sorted(diffs, key=lambda t: -t[2]):
            print("%d,%s,%.6e,%.6e" % (raw, SUBDET_NAME.get(sub, str(sub)), dp, dr))


if __name__ == "__main__":
    main()
