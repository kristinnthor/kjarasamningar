# -*- coding: utf-8 -*-
"""Tekur saman heildaryfirlit yfir söfnuð skjöl og finnur tvítök.

Býr til samningar/_yfirlit.csv með einni línu á hverja skrá, þar á meðal
SHA-256 og merkingu um hvort skráin sé afrit af annarri.

Notkun:
    python scripts/yfirlit.py                 # skrifar yfirlit
    python scripts/yfirlit.py --fjarlaegja    # færir tvítök í samningar/_tvitok/
"""
from __future__ import annotations

import csv
import hashlib
import os
import shutil
import sys
from collections import defaultdict

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMNINGAR = os.path.join(ROT, "samningar")
YFIRLIT = os.path.join(SAMNINGAR, "_yfirlit.csv")
TVITOK = os.path.join(SAMNINGAR, "_tvitok")

# Heimildir í forgangsröð: eintakið sem heldur sér við afritahreinsun
FORGANGUR = ["rikissattasemjari", "sa", "rikid", "samband", "reykjavik"]


def sha256(leid: str) -> str:
    h = hashlib.sha256()
    with open(leid, "rb") as f:
        for hluti in iter(lambda: f.read(1 << 20), b""):
            h.update(hluti)
    return h.hexdigest()


def forgangur(kodi: str) -> int:
    return FORGANGUR.index(kodi) if kodi in FORGANGUR else len(FORGANGUR)


def main(argv):
    fjarlaegja = "--fjarlaegja" in argv

    skrar = []
    for mappa, _, nofn in os.walk(SAMNINGAR):
        if os.path.basename(mappa) == "_tvitok":
            continue
        for n in nofn:
            if n.lower().endswith(".pdf"):
                skrar.append(os.path.join(mappa, n))

    print(f"Reikna SHA-256 fyrir {len(skrar)} skrár ...")
    eftir_hasi = defaultdict(list)
    radir = []
    for i, leid in enumerate(skrar, 1):
        rel = os.path.relpath(leid, SAMNINGAR).replace("\\", "/")
        kodi = rel.split("/")[0]
        h = sha256(leid)
        eftir_hasi[h].append(rel)
        radir.append({"kodi": kodi, "skra": rel,
                      "staerd_bæti": os.path.getsize(leid), "sha256": h})
        if i % 500 == 0:
            print(f"  {i}/{len(skrar)}")

    # merkja hvert eintak er frumeintakið
    frumeintak = {}
    for h, lista in eftir_hasi.items():
        frumeintak[h] = sorted(lista, key=lambda r: (forgangur(r.split("/")[0]), r))[0]
    for r in radir:
        r["frumeintak"] = frumeintak[r["sha256"]]
        r["er_tvitak"] = int(r["skra"] != r["frumeintak"])

    with open(YFIRLIT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["kodi", "skra", "staerd_bæti",
                                          "sha256", "er_tvitak", "frumeintak"])
        w.writeheader()
        w.writerows(radir)

    tvitok = [r for r in radir if r["er_tvitak"]]
    einstok = len(eftir_hasi)
    heild = sum(r["staerd_bæti"] for r in radir)
    sparnadur = sum(r["staerd_bæti"] for r in tvitok)
    print(f"\n{len(radir)} skrár, {einstok} einstök skjöl, {len(tvitok)} tvítök")
    print(f"Heildarstærð {heild/2**30:.2f} GB, þar af tvítök {sparnadur/2**30:.2f} GB")

    # fjöldi eftir heimildum
    eftir_kodum = defaultdict(lambda: [0, 0])
    for r in radir:
        eftir_kodum[r["kodi"]][0] += 1
        if not r["er_tvitak"]:
            eftir_kodum[r["kodi"]][1] += 1
    print("\nheimild                 skrár  einstök")
    for k in sorted(eftir_kodum, key=lambda x: -eftir_kodum[x][1]):
        a, b = eftir_kodum[k]
        print(f"  {k:<22} {a:>5}  {b:>5}")

    if fjarlaegja and tvitok:
        os.makedirs(TVITOK, exist_ok=True)
        for r in tvitok:
            upp = os.path.join(SAMNINGAR, r["skra"])
            nidur = os.path.join(TVITOK, r["skra"].replace("/", "__"))
            os.makedirs(os.path.dirname(nidur) or TVITOK, exist_ok=True)
            shutil.move(upp, nidur)
        print(f"\nFærði {len(tvitok)} tvítök í {TVITOK} (ekki eytt).")
    print(f"\nYfirlit skrifað í {YFIRLIT}")


if __name__ == "__main__":
    main(sys.argv[1:])
