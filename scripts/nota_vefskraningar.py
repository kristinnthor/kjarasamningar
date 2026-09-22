# -*- coding: utf-8 -*-
"""Festir samþykktar skráningar úr vefviðmótinu (Eyðuskráning) í gagnasettið.

Vefviðmótið geymir skráningar í gagnagrunni síðunnar, sem aðeins er hægt að
lesa innskráð(ur). Claude sækir þær og vistar sem JSON á forminu

    {"tillogur": [{id, tegund, felag, eyda, dagsetning, prosenta, kronur,
                   a_vid, heimild, athugasemd}, ...],
     "mat": {tillaga_id: "samthykkt" | "hafnad"}}

og þetta forrit festir þær:

  - samþykktar hækkanir  -> gogn/handvirkar_leidrettingar.csv
  - samþykkt "engin hækkun" -> gogn/stadfestar_eydur.csv, svo eyðan birtist
    ekki aftur til yfirferðar

Aðeins samþykktar skráningar eru festar; tillögur sem bíða eða var hafnað
eru hunsaðar.

Notkun:
    python scripts/nota_vefskraningar.py skraningar.json
    python scripts/nota_vefskraningar.py skraningar.json --kanna
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
LEIDRETTINGAR = os.path.join(GOGN, "handvirkar_leidrettingar.csv")
STADFESTAR = os.path.join(GOGN, "stadfestar_eydur.csv")

L_DALKAR = ["felag", "gildir_fra", "prosenta", "kronur", "a_vid",
            "heimild", "athugasemd", "skradur", "motadili"]
S_DALKAR = ["felag", "eyda_fra", "eyda_til", "athugasemd", "skradur", "motadili"]
EYDUR_JSON = os.path.join(ROT, "yfirferd", "eydur.json")


def adalsamningar():
    """Auðkenni félags í vefviðmótinu -> mótaðili aðalsamnings þess.

    Eyðurnar í vefviðmótinu eru allar í aðalsamningi félagsins, svo skráning
    á eyðu á heima í þeirri samningslínu.
    """
    if not os.path.exists(EYDUR_JSON):
        return {}
    with open(EYDUR_JSON, encoding="utf-8") as f:
        return {x["audkenni"]: x.get("motadili", "") for x in json.load(f)["felog"]}


def lesa(leid):
    if not os.path.exists(leid):
        return []
    with open(leid, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def skrifa(leid, dalkar, radir):
    with open(leid, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=dalkar, extrasaction="ignore")
        w.writeheader()
        w.writerows(radir)


def tala(x):
    if x is None or x == "":
        return ""
    x = float(x)
    return int(x) if x.is_integer() else x


def main(argv):
    if not argv or argv[0].startswith("--"):
        print(__doc__)
        return 1
    kanna = "--kanna" in argv
    with open(argv[0], encoding="utf-8-sig") as f:
        gogn = json.load(f)
    mat = gogn.get("mat", {})
    samth = [t for t in gogn["tillogur"] if mat.get(t["id"]) == "samthykkt"]
    idag = date.today().isoformat()
    adal = adalsamningar()

    nyjar_l, nyjar_s = [], []
    for t in samth:
        if t.get("tegund") == "engin":
            fra, til = t["eyda"].split("_")
            nyjar_s.append({"felag": t["felag"], "eyda_fra": fra, "eyda_til": til,
                            "athugasemd": t.get("athugasemd") or "", "skradur": idag,
                            "motadili": adal.get(t.get("felag_audkenni"), "")})
            continue
        nyjar_l.append({
            "felag": t["felag"], "gildir_fra": t["dagsetning"],
            "prosenta": tala(t.get("prosenta")), "kronur": tala(t.get("kronur")),
            "a_vid": t.get("a_vid") or "óskilgreint",
            "heimild": t.get("heimild") or "", "athugasemd": t.get("athugasemd") or "",
            "skradur": idag,
            "motadili": adal.get(t.get("felag_audkenni"), ""),
        })

    print(f"Skráningar: {len(gogn['tillogur'])}, samþykktar: {len(samth)}")
    print(f"  hækkanir:       {len(nyjar_l)}")
    print(f"  engin hækkun:   {len(nyjar_s)}")
    for r in sorted(nyjar_l, key=lambda r: (r["felag"], r["gildir_fra"])):
        print(f"   {r['gildir_fra']}  {r['felag'][:36]:<38} "
              f"{r['prosenta'] or '-':>6}%  {r['kronur'] or '-':>7} kr")
    for r in nyjar_s:
        print(f"   {r['eyda_fra']} → {r['eyda_til']}  {r['felag'][:36]}  engin hækkun")
    if kanna:
        print("\n--kanna: ekkert skrifað.")
        return 0

    # Nýrri skráning á sama degi hjá sama félagi leysir eldri af hólmi
    lyklar = {(r["felag"], r["gildir_fra"]) for r in nyjar_l}
    allar = [r for r in lesa(LEIDRETTINGAR)
             if (r["felag"], r["gildir_fra"]) not in lyklar] + nyjar_l
    allar.sort(key=lambda r: (r["felag"], r["gildir_fra"]))
    skrifa(LEIDRETTINGAR, L_DALKAR, allar)

    lyklar = {(r["felag"], r["eyda_fra"], r["eyda_til"]) for r in nyjar_s}
    stadf = [r for r in lesa(STADFESTAR)
             if (r["felag"], r["eyda_fra"], r["eyda_til"]) not in lyklar] + nyjar_s
    stadf.sort(key=lambda r: (r["felag"], r["eyda_fra"]))
    skrifa(STADFESTAR, S_DALKAR, stadf)

    print(f"\n{len(allar)} leiðréttingar í {LEIDRETTINGAR}")
    print(f"{len(stadf)} staðfestar eyður í {STADFESTAR}")
    print("Keyrðu næst: sameina.py, launathroun.py, byggja_api.py, yfirferd.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
