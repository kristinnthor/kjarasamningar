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
import json
import os
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from launathroun import samhaefa_heiti  # noqa: E402
import motadilar  # noqa: E402

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
SKRA = os.path.join(GOGN, "haekkanir.csv")
VEF = os.path.join(GOGN, "haekkanir_vefskjol.csv")
HANDVIRKT = os.path.join(GOGN, "handvirkar_leidrettingar.csv")
SAMNINGAR = os.path.join(ROT, "samningar")
# Slóðir sem niðurhalsskrárnar ná ekki yfir, flettar upp handvirkt
SLODIR_VIDBOT = os.path.join(GOGN, "skjalaslodir_vidbot.csv")
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
          "kronur", "a_vid", "artal_stada", "skjal", "slod", "tilvitnun",
          "motadili", "motadili_heiti", "af_felagsvef"]


def motadilar_eftir_slod():
    """(pdf-slóð, samhæft félagsheiti) -> mótaðili úr skránni.

    Sama PDF-skjal getur átt við fleiri en eitt félag með ólíkum mótaðila
    (samningur_185 er bæði Flugvirkjafélagsins við Samgöngustofu og
    flugumferðarstjóra við ríkið), svo félagið er hluti lykilsins.
    """
    leid = os.path.join(SAMNINGAR, "rikissattasemjari", "lysigogn.json")
    if not os.path.exists(leid):
        return {}
    with open(leid, encoding="utf-8") as f:
        gogn = json.load(f)
    kort = {}
    for x in gogn:
        if not x.get("pdf_url"):
            continue
        felag = samhaefa_heiti(x.get("launthegi_canonical") or x.get("launthegi"))
        kort.setdefault((x["pdf_url"], felag), motadilar.ur_skra(x.get("atvinnurekandi")))
        kort.setdefault((x["pdf_url"], ""), motadilar.ur_skra(x.get("atvinnurekandi")))
    return kort


def skjalaslodir():
    """Slóð á hvert skjal á netinu, svo hægt sé að vísa á samninginn sjálfan.

    Samningar heildarskrárinnar eru paraðir eftir auðkenni samnings, ekki
    skráarheiti: sama skráarheitið er stundum notað fyrir ólík skjöl.
    Vefskjöl eru pöruð eftir staðbundinni slóð í niðurhalsskránum.
    """
    eftir_id, eftir_skra = {}, {}
    leid = os.path.join(SAMNINGAR, "rikissattasemjari", "lysigogn.json")
    if os.path.exists(leid):
        with open(leid, encoding="utf-8") as f:
            for x in json.load(f):
                if x.get("pdf_url"):
                    eftir_id[str(x["id"])] = x["pdf_url"]
    for nafn in ("_skra.csv", "_skra_wp.csv"):
        for r in lesa(os.path.join(SAMNINGAR, nafn)):
            if r.get("skra") and r.get("slod"):
                eftir_skra.setdefault(r["skra"], r["slod"])
    for r in lesa(SLODIR_VIDBOT):
        eftir_skra.setdefault(r["skra"], r["slod"])
    return eftir_id, eftir_skra


def fyrirtaekjaskra():
    """Fyrirtæki úr skránni, svo þau þekkist líka í vefskjölum."""
    leid = os.path.join(SAMNINGAR, "rikissattasemjari", "lysigogn.json")
    if not os.path.exists(leid):
        return None
    with open(leid, encoding="utf-8") as f:
        gogn = json.load(f)
    return motadilar.Fyrirtaekjaskra(
        [x.get("atvinnurekandi") or "" for x in gogn],
        [x.get("launthegi_canonical") or x.get("launthegi") or "" for x in gogn])


def main():
    skra = lesa(SKRA)
    vef = lesa(VEF)
    if not vef:
        print("gogn/haekkanir_vefskjol.csv fannst ekki - "
              "keyrðu scripts/utdrattur_pdf.py fyrst")
        return

    kort = thekkt_felog(skra)
    print(f"Þekkt félög úr heildarskránni: {len(kort)}")

    slod_id, slod_skra = skjalaslodir()
    fyrirtaeki = fyrirtaekjaskra()
    ut = []
    for r in skra:
        motadili, motadili_heiti = motadilar.ur_skra(r.get("atvinnurekandi"))
        ut.append({
            "uppruni": "ríkissáttasemjari", "rakning": "staðfest lýsigögn",
            **{k: r.get(k) for k in DALKAR if k not in ("uppruni", "rakning")},
            "slod": slod_id.get(str(r.get("samningur_id")), ""),
            "motadili": motadili, "motadili_heiti": motadili_heiti,
            "af_felagsvef": 0,
        })

    talning = collections.Counter()
    for r in vef:
        felag, adferd = finna_felag(r, kort)
        talning[adferd] += 1
        if not felag:
            continue
        motadili, motadili_heiti = motadilar.ur_vefskjali(
            r.get("adili_1"), r.get("adili_2"), r.get("skjal"), fyrirtaeki,
            r.get("heimild") or "")
        ut.append({
            "uppruni": "vefskjal", "rakning": adferd, "felag": felag,
            "motadili": motadili, "motadili_heiti": motadili_heiti,
            # Skjal af vef félagsins sjálfs er langoftast aðalsamningur þess;
            # það ræður hvert hækkun með óþekktum mótaðila fer.
            "af_felagsvef": int((r.get("heimild") or "") in FELAGSVEFIR),
            "felag_id": "", "atvinnurekandi": r.get("adili_2") or "",
            "markadur": "", "heildarsamtok": "",
            "gildir_fra": r["gildir_fra"], "tegund": r["tegund"],
            "prosenta": r["prosenta"], "kronur": r["kronur"],
            "a_vid": r["a_vid"], "artal_stada": r["artal_stada"],
            "skjal": r["skjal"],
            "slod": slod_skra.get((r["skjal"] or "").replace("\\", "/"), ""),
            "tilvitnun": r["tilvitnun"],
        })

    # Handvirkar leiðréttingar eru geymdar sérstaklega svo þær lifi af
    # endurkeyrslu útdráttarins. Þær bera eigin uppruna og rakningu, svo
    # alltaf sé ljóst hvað var vélrænt lesið og hvað var lagfært af manni.
    handvirkt = lesa(HANDVIRKT)
    motad_slod = motadilar_eftir_slod()
    for r in handvirkt:
        # Mótaðili: skráður í leiðréttingunni, annars samningsins sem heimildin
        # vísar í, annars autt = aðalsamningur félagsins
        m = (r.get("motadili") or "").strip()
        m_heiti = motadilar.HEITI.get(m, "")
        heimild = (r.get("heimild") or "").strip()
        if not m and heimild:
            m, m_heiti = motad_slod.get((heimild, samhaefa_heiti(r["felag"])),
                                        motad_slod.get((heimild, ""), ("", "")))
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
            "slod": (r.get("heimild") or "") if (r.get("heimild") or "").startswith(
                ("http://", "https://")) else "",
            "tilvitnun": (r.get("athugasemd")
                          or "Handvirk leiðrétting við yfirferð eyðu."),
            "motadili": m,
            "motadili_heiti": m_heiti,
            "af_felagsvef": 0,
        })

    # Handvirk leiðrétting ræður á sínum degi. Sá sem skráði hana fór yfir
    # samninginn og skráði það sem gildir þann dag, svo vélrænt lesnar
    # hækkanir sama félags sama dag víkja - annars tvítelst hækkunin, eða
    # röng tala úr útdrættinum lifir áfram við hlið þeirrar réttu.
    if handvirkt:
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
    med_slod = sum(1 for r in ut if r.get("slod"))
    motad = collections.Counter(
        "óþekktur" if r["motadili"] in ("", motadilar.OTHEKKTUR) else "þekktur"
        for r in ut if r["uppruni"] != "handvirk leiðrétting")
    print(f"Mótaðili:              {dict(motad)}")
    print(f"\nSameinað:              {len(ut)}")
    print(f"Með slóð á skjal:      {med_slod}")
    print(f"Skrifað í {UT}")


if __name__ == "__main__":
    main()
