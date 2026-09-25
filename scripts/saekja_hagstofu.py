# -*- coding: utf-8 -*-
"""Sækir launavísitölu og vísitölu neysluverðs Hagstofunnar gegnum PX-Web API.

Launavísitalan mælir raunverulega launaþróun, ekki umsamdar hækkanir, og er
því sjálfstæð viðmiðunarröð við hliðina á samningsgögnunum - ekki staðgengill
fyrir þau. Hún skiptist eftir markaði (almennur, ríki, sveitarfélög) en ekki
eftir stéttarfélagi; það sem er eftir stéttarfélagi kemur úr samningunum.

Mánaðarröðin nær aftur til janúar 1989 og brúar þannig 10. áratuginn, þar sem
samningar eru of gisnir til að bera samfellda röð.

Vísitala neysluverðs er annað viðmið: hún mælir verðlag, ekki laun. Umsamin
hækkun umfram hana er raunhækkun kauptaxta; hækkun undir henni er kjararýrnun.

Notkun:
    python scripts/saekja_hagstofu.py                         # allar töflur
    python scripts/saekja_hagstofu.py visitala_neysluverds    # aðeins ein
"""
from __future__ import annotations

import csv
import json
import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
GRUNNUR = "https://px.hagstofa.is/pxis/api/v1/is/Samfelag/launogtekjur/2_lvt"
VERDLAG = "https://px.hagstofa.is/pxis/api/v1/is/Efnahagur/visitolur/1_vnv/1_vnv"

TOFLUR = [
    {
        "skra": "launavisitala_manadarleg.csv",
        "slod": f"{GRUNNUR}/1_manadartolur/LAU04000.px",
        "lysing": "Launavísitala eftir mánuðum frá 1989",
    },
    {
        "skra": "launavisitala_hopar_1990_2000.csv",
        "slod": f"{GRUNNUR}/5_eldra/LAU09903.px",
        "lysing": "Launavísitala helstu launþegahópa, ársfjórðungar 1990-2000",
    },
    {
        "skra": "launavisitala_hopar_2000_2006.csv",
        "slod": f"{GRUNNUR}/5_eldra/LAU09902.px",
        "lysing": "Launavísitala helstu launþegahópa, ársfjórðungar 2000-2006",
    },
    {
        "skra": "launavisitala_hopar_2005_2022.csv",
        "slod": f"{GRUNNUR}/5_eldra/LAU09901.px",
        "lysing": "Ársfjórðungsleg launavísitala helstu launþegahópa 2005-2022",
    },
    {
        "skra": "launavisitala_hopar_fra_2015.csv",
        "slod": f"{GRUNNUR}/1_manadartolur/LAU04003.px",
        "lysing": "Vísitölur launa helstu launþegahópa eftir mánuðum frá 2015",
    },
    {
        "skra": "visitala_neysluverds.csv",
        "slod": f"{VERDLAG}/VIS01000.px",
        "lysing": "Vísitala neysluverðs og breytingar, grunnur maí 1988 = 100",
        # Taflan geymir líka ársbreytingu síðustu 1, 3 og 6 mánaða; þær eru
        # afleiddar af vísitölunni og myndu þrefalda skrána án þess að bæta
        # neinu við.
        "val": {"Liður": ["index", "change_M", "change_A"]},
    },
]


def saekja_toflu(s: requests.Session, slod: str, val: dict | None = None):
    """Sækir töfluna; `val` takmarkar breytu við tiltekin gildi, annars allt."""
    val = val or {}
    lysing = s.get(slod, timeout=60).json()
    fyrirspurn = {
        "query": [
            {"code": v["code"],
             "selection": ({"filter": "item", "values": val[v["code"]]}
                           if v["code"] in val
                           else {"filter": "all", "values": ["*"]})}
            for v in lysing["variables"]
        ],
        "response": {"format": "json-stat2"},
    }
    r = s.post(slod, json=fyrirspurn, timeout=180)
    r.raise_for_status()
    return lysing, r.json()


def fletja(jst):
    """Breytir json-stat2 í flata lista af línum."""
    vidir = jst["id"]
    staerdir = [jst["size"][i] for i in range(len(vidir))]
    flokkar = []
    for v in vidir:
        d = jst["dimension"][v]
        kort = d["category"]
        merki = kort.get("label", {})
        rod = sorted(kort["index"].items(), key=lambda kv: kv[1])
        flokkar.append([(k, merki.get(k, k)) for k, _ in rod])

    gildi = jst["value"]
    radir = []
    n = len(gildi)
    for hnit in range(n):
        eftir = hnit
        lykt = []
        for i in range(len(vidir) - 1, -1, -1):
            lykt.append(flokkar[i][eftir % staerdir[i]])
            eftir //= staerdir[i]
        lykt.reverse()
        rad = {}
        for v, (k, heiti) in zip(vidir, lykt):
            rad[jst["dimension"][v]["label"]] = heiti
        rad["gildi"] = gildi[hnit]
        radir.append(rad)
    return radir


def main(argv):
    os.makedirs(GOGN, exist_ok=True)
    s = requests.Session()
    s.headers.update({"User-Agent": "kjarasamningar-gagnasett/1.0"})

    toflur = [t for t in TOFLUR if not argv or t["skra"][:-4] in argv]
    if not toflur:
        sys.exit("Engin tafla heitir " + ", ".join(argv) + ". Í boði: "
                 + ", ".join(t["skra"][:-4] for t in TOFLUR))
    for t in toflur:
        print(f"[{t['skra']}] {t['lysing']}")
        try:
            lysing, jst = saekja_toflu(s, t["slod"], t.get("val"))
        except Exception as e:
            print(f"  villa: {type(e).__name__}: {e}")
            continue
        radir = [r for r in fletja(jst) if r["gildi"] is not None]
        if not radir:
            print("  engin gildi")
            continue
        dalkar = [k for k in radir[0] if k != "gildi"] + ["gildi"]
        ut = os.path.join(GOGN, t["skra"])
        with open(ut, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=dalkar, extrasaction="ignore")
            w.writeheader()
            w.writerows(radir)
        print(f"  {len(radir)} línur -> {ut}")


if __name__ == "__main__":
    main(sys.argv[1:])
