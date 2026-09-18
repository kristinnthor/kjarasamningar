# -*- coding: utf-8 -*-
"""Könnun: hversu vel er hægt að draga launabreytingar úr textum samninganna?

Þetta er ekki lokaútdrátturinn heldur mælitæki - það telur hvað finnst, hvar
það finnst og sýnir dæmi, svo hægt sé að meta gæði gagnanna áður en gagnasettið
sjálft er smíðað.

Notkun:
    python scripts/kanna_launalid.py
    python scripts/kanna_launalid.py --daemi 20
"""
from __future__ import annotations

import json
import os
import re
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LYSIGOGN = os.path.join(ROT, "samningar", "rikissattasemjari", "lysigogn.json")

MANUDIR = {
    "janúar": 1, "januar": 1, "febrúar": 2, "februar": 2, "mars": 3,
    "apríl": 4, "april": 4, "maí": 5, "mai": 5, "júní": 6, "juni": 6,
    "júlí": 7, "juli": 7, "ágúst": 8, "agust": 8, "september": 9,
    "október": 10, "oktober": 10, "nóvember": 11, "november": 11,
    "desember": 12,
}
MAN_RE = "|".join(sorted(MANUDIR, key=len, reverse=True))

# "1. júní 1988" / "1. janúar 2026"
DAGS = rf"(\d{{1,2}})\.?\s*(?:dag\s+)?({MAN_RE})\s*,?\s*(\d{{4}})?"
# 3,25%  3.25 %  5,1%
PROSENTA = r"(\d{1,2}(?:[.,]\d{1,2})?)\s*%"
# kr. 2.025 / 23.750 kr.
KRONUR = r"(?:kr\.?\s*([\d.]{3,9})|([\d.]{3,9})\s*kr\.?)"

# Mynstur A: dagsetning fremst, prósenta á eftir  ("1. júní 1988 3,25%")
A = re.compile(rf"{DAGS}\s*[:\-–]?\s*(?:um\s+|hækka\s+um\s+)?{PROSENTA}", re.I)
# Mynstur B: prósenta fremst, dagsetning á eftir ("hækka um 5,1% þann 1. maí 2024")
B = re.compile(rf"{PROSENTA}\s*(?:hækkun\s*)?(?:frá|þann|hinn|fr\.o\.m\.?|1\.)?\s*{DAGS}", re.I)

HAEKKUNARORD = re.compile(
    r"hækk|launabreyting|launaþróun|kauptaxt|taxtahækk|launahækk", re.I)


def normadags(d, m, a):
    try:
        dagur = int(d)
        man = MANUDIR[m.lower()]
    except (ValueError, KeyError):
        return None
    if not a:
        return None
    ar = int(a)
    if not (1940 <= ar <= 2035) or not (1 <= dagur <= 31):
        return None
    return f"{ar:04d}-{man:02d}-{dagur:02d}"


def finna(texti: str):
    """Skilar lista af (dagsetning, prósenta, samhengi)."""
    ut = []
    for m in A.finditer(texti):
        d, man, ar, pros = m.groups()
        dags = normadags(d, man, ar)
        if not dags:
            continue
        umhverfi = texti[max(0, m.start() - 160):m.end() + 60]
        if not HAEKKUNARORD.search(umhverfi):
            continue
        p = float(pros.replace(",", "."))
        if 0 < p <= 40:
            ut.append((dags, p, " ".join(umhverfi.split())))
    for m in B.finditer(texti):
        pros, d, man, ar = m.groups()
        dags = normadags(d, man, ar)
        if not dags:
            continue
        umhverfi = texti[max(0, m.start() - 160):m.end() + 60]
        if not HAEKKUNARORD.search(umhverfi):
            continue
        p = float(pros.replace(",", "."))
        if 0 < p <= 40:
            ut.append((dags, p, " ".join(umhverfi.split())))
    # fjarlægja tvítök á (dags, prósentu)
    sed, hreint = set(), []
    for dags, p, s in ut:
        if (dags, p) in sed:
            continue
        sed.add((dags, p))
        hreint.append((dags, p, s))
    return hreint


def main(argv):
    fj_daemi = 10
    if "--daemi" in argv:
        fj_daemi = int(argv[argv.index("--daemi") + 1])

    d = json.load(open(LYSIGOGN, encoding="utf-8"))
    med_texta = [x for x in d if (x.get("ocr_text") or "").strip()]

    med_nidurstodu = 0
    allar = []
    eftir_aratug = collections.Counter()
    eftir_felagi = collections.Counter()
    samn_eftir_aratug = collections.Counter()

    for x in med_texta:
        ar = (x.get("fra") or "")[:4]
        aratugur = f"{int(ar)//10*10}s" if ar.isdigit() else "óþekkt"
        samn_eftir_aratug[aratugur] += 1
        nidur = finna(x["ocr_text"])
        if nidur:
            med_nidurstodu += 1
            eftir_aratug[aratugur] += len(nidur)
            eftir_felagi[x.get("launthegi_canonical") or "óþekkt"] += len(nidur)
            for dags, p, s in nidur:
                allar.append((dags, p, x.get("launthegi_canonical"),
                              x.get("atvinnurekandi"), x.get("markadsflokk"), s))

    print(f"Samningar með texta:            {len(med_texta)}")
    print(f"Þar sem launahækkun fannst:     {med_nidurstodu} "
          f"({med_nidurstodu/len(med_texta)*100:.0f}%)")
    print(f"Hækkanir (dags + %) alls:       {len(allar)}\n")

    print("áratugur  samningar  með hækkun  hækkanir")
    for k in sorted(samn_eftir_aratug):
        print(f"  {k:<8} {samn_eftir_aratug[k]:>9}  "
              f"{'':>10}  {eftir_aratug.get(k,0):>8}")

    print("\nStéttarfélög með flestar fundnar hækkanir:")
    for k, v in eftir_felagi.most_common(15):
        print(f"  {v:>5}  {str(k)[:64]}")

    print(f"\n== {fj_daemi} dæmi ==")
    for dags, p, fel, atv, mark, s in sorted(allar)[:fj_daemi]:
        print(f"\n{dags}  {p}%  | {str(fel)[:45]} <-> {str(atv)[:35]} [{mark}]")
        print(f"   ...{s[:230]}...")


if __name__ == "__main__":
    main(sys.argv[1:])
