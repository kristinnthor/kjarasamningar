# -*- coding: utf-8 -*-
"""Sameinar hækkanir úr vefskjölum við þær sem hafa staðfest lýsigögn.

Vandinn er rakning: vefskjölunum fylgja engin lýsigögn, svo áður en færsla má
fara inn í tímaröð félags þarf að vera ljóst hvaða félag á í hlut. Hér er það
gert í þremur þrepum, og hver færsla ber með sér hvaða þrep skilaði henni:

  1. Aðili úr skjalinu passar við félag sem þegar er þekkt úr heildarskránni.
  2. Skjalið kom af vef stéttarfélags, svo félagið liggur í augum uppi.
  3. Hvorugt - færslan er órakin og fer ekki í tímaraðirnar.

Notkun:
    python scripts/sameina.py
"""
from __future__ import annotations

import csv
import os
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from launathroun import samhaefa_heiti  # noqa: E402

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
SKRA = os.path.join(GOGN, "haekkanir.csv")
VEF = os.path.join(GOGN, "haekkanir_vefskjol.csv")
HANDVIRKT = os.path.join(GOGN, "handvirkar_leidrettingar.csv")
UT = os.path.join(GOGN, "haekkanir_sameinad.csv")

# Vefir stéttarfélaga: skjal þaðan á við það félag nema annað komi fram.
FELAGSVEFIR = {
    "vr": "VR", "efling": "Efling", "sgs": "SGS",
    "afl": "AFL Starfsgreinafélag", "rsi": "RSÍ", "rafis": "RSÍ",
    "samidn": "Samiðn", "vm": "VM", "matvis": "MATVÍS", "grafia": "Grafía",
    "ssf": "Samtök starfsmanna fjármálafyrirtækja",
    "eining-idja": "Eining-Iðja", "framsyn": "Framsýn",
    "vlfa": "Verkalýðsfélag Akraness", "verkvest": "Verkalýðsfélag Vestfirðinga",
    "liv": "LÍV", "sjomenn": "Sjómannasamband Íslands",
    "bhm": "BHM", "bsrb": "BSRB", "ki": "Kennarasamband Íslands",
    "sameyki": "Sameyki", "hjukrun": "Félag íslenskra hjúkrunarfræðinga",
    "lis": "Læknafélag Íslands", "fin": "Félag íslenskra náttúrufræðinga",
    "vfi": "Verkfræðingafélag Íslands",
}

# Vefir viðsemjenda og heildarsamtaka: félagið verður að koma úr skjalinu
# sjálfu, því hver þessara vefja geymir samninga við tugi ólíkra félaga.
EKKI_FELAGSVEFIR = {"sa", "fa", "rikid", "samband", "reykjavik", "asi"}


def lesa(leid):
    if not os.path.exists(leid):
        return []
    with open(leid, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def thekkt_felog(radir):
    """Uppfletting frá samhæfðu heiti yfir í heiti eins og það er skráð."""
    kort = {}
    fj = collections.Counter()
    for r in radir:
        n = samhaefa_heiti(r.get("felag"))
        if n and len(n) >= 3:
            kort.setdefault(n, r["felag"])
            fj[n] += 1
    return kort


def finna_felag(rad, kort):
    """Skilar (heiti, adferd) eða (None, 'órakið')."""
    for reitur in ("adili_1", "adili_2"):
        n = samhaefa_heiti(rad.get(reitur))
        if n and n in kort:
            return kort[n], "aðili úr skjali"
    # Sumir aðilareitir telja upp fleiri félög; prófa hvern hluta
    for reitur in ("adili_1", "adili_2"):
        hrar = rad.get(reitur) or ""
        for hluti in hrar.replace(" og ", ",").split(","):
            n = samhaefa_heiti(hluti)
            if n and n in kort:
                return kort[n], "aðili úr skjali"
    kodi = rad.get("heimild")
    if kodi in FELAGSVEFIR:
        return FELAGSVEFIR[kodi], "vefur félagsins"
    return None, "órakið"


DALKAR = ["uppruni", "rakning", "felag", "felag_id", "atvinnurekandi",
          "markadur", "heildarsamtok", "gildir_fra", "tegund", "prosenta",
          "kronur", "a_vid", "artal_stada", "skjal", "tilvitnun"]


def main():
    skra = lesa(SKRA)
    vef = lesa(VEF)
    if not vef:
        print("gogn/haekkanir_vefskjol.csv fannst ekki - "
              "keyrðu scripts/utdrattur_pdf.py fyrst")
        return

    kort = thekkt_felog(skra)
    print(f"Þekkt félög úr heildarskránni: {len(kort)}")

    ut = []
    for r in skra:
        ut.append({
            "uppruni": "ríkissáttasemjari", "rakning": "staðfest lýsigögn",
            **{k: r.get(k) for k in DALKAR if k not in ("uppruni", "rakning")},
        })

    talning = collections.Counter()
    for r in vef:
        felag, adferd = finna_felag(r, kort)
        talning[adferd] += 1
        if not felag:
            continue
        ut.append({
            "uppruni": "vefskjal", "rakning": adferd, "felag": felag,
            "felag_id": "", "atvinnurekandi": r.get("adili_2") or "",
            "markadur": "", "heildarsamtok": "",
            "gildir_fra": r["gildir_fra"], "tegund": r["tegund"],
            "prosenta": r["prosenta"], "kronur": r["kronur"],
            "a_vid": r["a_vid"], "artal_stada": r["artal_stada"],
            "skjal": r["skjal"], "tilvitnun": r["tilvitnun"],
        })

    # Handvirkar leiðréttingar eru geymdar sérstaklega svo þær lifi af
    # endurkeyrslu útdráttarins. Þær bera eigin uppruna og rakningu, svo
    # alltaf sé ljóst hvað var vélrænt lesið og hvað var lagfært af manni.
    handvirkt = lesa(HANDVIRKT)
    for r in handvirkt:
        ut.append({
            "uppruni": "handvirk leiðrétting",
            "rakning": "yfirfarið handvirkt",
            "felag": r["felag"], "felag_id": "",
            "atvinnurekandi": "", "markadur": "", "heildarsamtok": "",
            "gildir_fra": r["gildir_fra"],
            "tegund": ("prósenta" if r["prosenta"] and not r["kronur"]
                       else "krónutala" if r["kronur"] and not r["prosenta"]
                       else "prósenta og krónutala"),
            "prosenta": r["prosenta"], "kronur": r["kronur"],
            "a_vid": r["a_vid"], "artal_stada": "úr texta",
            "skjal": r.get("heimild") or "",
            "tilvitnun": (r.get("athugasemd")
                          or "Handvirk leiðrétting við yfirferð eyðu."),
        })

    # Handvirk leiðrétting ræður á sínum degi. Sá sem skráði hana fór yfir
    # samninginn og skráði það sem gildir þann dag, svo vélrænt lesnar
    # hækkanir sama félags sama dag víkja - annars tvítelst hækkunin, eða
    # röng tala úr útdrættinum lifir áfram við hlið þeirrar réttu.
    if handvirkt:
        from launathroun import samhaefa_heiti
        leidrettir = {(samhaefa_heiti(r["felag"]), r["gildir_fra"]) for r in handvirkt}
        fyrir = len(ut)
        ut = [r for r in ut if r["uppruni"] == "handvirk leiðrétting"
              or (samhaefa_heiti(str(r["felag"] or "")), r["gildir_fra"]) not in leidrettir]
        print(f"Vélrænar hækkanir sem víkja fyrir leiðréttingu: {fyrir - len(ut)}")

    ut.sort(key=lambda r: (r["gildir_fra"] or "", str(r["felag"])))
    with open(UT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DALKAR, extrasaction="ignore")
        w.writeheader()
        w.writerows(ut)

    print(f"\nÚr heildarskrá:        {len(skra)}")
    print(f"Úr vefskjölum:         {len(vef)}")
    for k, v in talning.most_common():
        print(f"   {k:<22} {v}")
    print(f"\nSameinað:              {len(ut)}")
    print(f"Skrifað í {UT}")


if __name__ == "__main__":
    main()
