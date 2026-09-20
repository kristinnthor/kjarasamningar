# -*- coding: utf-8 -*-
"""Les yfirferðarskrána og festir handvirkar leiðréttingar í gagnasettið.

Leiðréttingarnar eru geymdar sérstaklega en ekki skrifaðar beint inn í
útdráttinn. Ástæðan er einföld: útdrátturinn er endurkeyrður reglulega og
myndi þá henda handavinnunni. Með sérgeymslu lifa leiðréttingarnar af hverja
endurkeyrslu og sjást alltaf sem það sem þær eru.

Vinnuferlið:
    1. python scripts/yfirferd.py            býr til yfirferd/eydur.csv
    2. fylltu út dálkana fremst í skránni
    3. python scripts/nota_leidrettingar.py  festir þær
    4. python scripts/sameina.py && python scripts/launathroun.py
       && python scripts/byggja_api.py

Notkun:
    python scripts/nota_leidrettingar.py            # les og festir
    python scripts/nota_leidrettingar.py --kanna    # sýnir aðeins hvað yrði gert
"""
from __future__ import annotations

import csv
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
INN = os.path.join(ROT, "yfirferd", "eydur.csv")
UT = os.path.join(GOGN, "handvirkar_leidrettingar.csv")

DALKAR = ["felag", "gildir_fra", "prosenta", "kronur", "a_vid",
          "heimild", "athugasemd", "skradur"]

GILD_AVID = {"almenn laun", "kauptaxtar", "launatafla", "lágmarkstekjur",
             "byrjunarlaun", "óskilgreint"}


def tala(s, heil=False):
    s = (s or "").strip().replace("%", "").replace(" ", "")
    if not s:
        return None
    s = s.replace(".", "") if heil else s.replace(",", ".")
    try:
        return int(s) if heil else float(s)
    except ValueError:
        return "villa"


def main(argv):
    kanna = "--kanna" in argv
    if not os.path.exists(INN):
        print(f"{INN} fannst ekki - keyrðu scripts/yfirferd.py fyrst")
        return 1

    with open(INN, encoding="utf-8-sig", newline="") as f:
        linur = list(csv.DictReader(f))

    nyjar, villur, sleppt = [], [], 0
    for nr, r in enumerate(linur, 2):          # 2 = fyrsta línan eftir haus
        stada = (r.get("stada") or "").strip().lower()
        dags = (r.get("dagsetning") or "").strip()
        if not stada and not dags:
            sleppt += 1
            continue
        if stada in ("rétt", "rett", "óvisst", "ovisst", "óvíst"):
            sleppt += 1
            continue
        if not dags:
            villur.append(f"lína {nr}: staða '{stada}' en engin dagsetning")
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dags):
            villur.append(f"lína {nr}: dagsetning '{dags}' er ekki á forminu ÁÁÁÁ-MM-DD")
            continue
        try:
            date.fromisoformat(dags)
        except ValueError:
            villur.append(f"lína {nr}: '{dags}' er ekki gild dagsetning")
            continue

        pros, kr = tala(r.get("prosenta")), tala(r.get("kronur"), heil=True)
        if pros == "villa" or kr == "villa":
            villur.append(f"lína {nr}: ólæsileg tala "
                          f"(prósenta={r.get('prosenta')!r}, kronur={r.get('kronur')!r})")
            continue
        if pros is None and kr is None:
            villur.append(f"lína {nr}: hvorki prósenta né krónutala")
            continue
        if pros is not None and not (0 < pros <= 25):
            villur.append(f"lína {nr}: prósenta {pros} utan skynsamlegra marka")
            continue
        if kr is not None and not (500 <= kr <= 200_000):
            villur.append(f"lína {nr}: krónutala {kr} utan skynsamlegra marka")
            continue

        avid = (r.get("a_vid") or "").strip() or "óskilgreint"
        if avid not in GILD_AVID:
            villur.append(f"lína {nr}: a_vid '{avid}' er óþekkt "
                          f"(gild gildi: {', '.join(sorted(GILD_AVID))})")
            continue
        if not (r.get("felag") or "").strip():
            villur.append(f"lína {nr}: félag vantar")
            continue

        nyjar.append({
            "felag": r["felag"].strip(),
            "gildir_fra": dags,
            "prosenta": pros if pros is not None else "",
            "kronur": kr if kr is not None else "",
            "a_vid": avid,
            "heimild": (r.get("heimild") or "").strip(),
            "athugasemd": (r.get("athugasemd") or "").strip(),
            "skradur": date.today().isoformat(),
        })

    print(f"Línur í yfirferðarskrá: {len(linur)}")
    print(f"  óútfylltar eða merktar réttar: {sleppt}")
    print(f"  leiðréttingar:                 {len(nyjar)}")
    if villur:
        print(f"\n{len(villur)} villur - ekkert var fest:")
        for v in villur[:20]:
            print(f"   {v}")
        return 1
    if not nyjar:
        print("\nEkkert til að festa.")
        return 0

    # Fyrri leiðréttingar haldast; nýjar bætast við eða leysa af hólmi
    fyrri = []
    if os.path.exists(UT):
        with open(UT, encoding="utf-8-sig", newline="") as f:
            fyrri = list(csv.DictReader(f))
    lyklar = {(r["felag"], r["gildir_fra"]) for r in nyjar}
    haldid = [r for r in fyrri if (r["felag"], r["gildir_fra"]) not in lyklar]
    allar = sorted(haldid + nyjar, key=lambda r: (r["felag"], r["gildir_fra"]))

    if kanna:
        print("\n--kanna: ekkert skrifað. Þetta yrði fest:\n")
        for r in nyjar:
            print(f"   {r['gildir_fra']}  {r['felag'][:34]:<36} "
                  f"{r['prosenta'] or '-':>6}%  {r['kronur'] or '-':>7} kr  "
                  f"{r['a_vid']}")
        return 0

    os.makedirs(GOGN, exist_ok=True)
    with open(UT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DALKAR, extrasaction="ignore")
        w.writeheader()
        w.writerows(allar)
    print(f"\n{len(allar)} leiðréttingar í {UT}")
    print("Keyrðu næst: scripts/sameina.py, launathroun.py, byggja_api.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
