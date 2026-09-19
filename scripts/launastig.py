# -*- coding: utf-8 -*-
"""Dregur saman launatöflurnar í nothæfa tímaröð um launastig.

Fullar launatöflur eru gríðarstórar - hver tafla ber tugi launaflokka sinnum
nokkur starfsaldursþrep, og samningur geymir eina töflu á hvert ár. Fyrir
tímaröð um launaþróun er sú upplausn hvorki þörf né nothæf.

Hér er hver tafla dregin saman í þrjár tölur sem svara ólíkum spurningum:

  lagsti_taxti     byrjunarlaun í lægsta launaflokki - gólfið í samningnum
  midgildi_taxti   miðgildi allra taxta töflunnar - dæmigerð staða
  haesti_taxti     efsti taxti - þakið

Notkun:
    python scripts/launastig.py
"""
from __future__ import annotations

import csv
import os
import statistics
import sys
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sameina import FELAGSVEFIR, EKKI_FELAGSVEFIR  # noqa: E402
from launathroun import samhaefa_heiti  # noqa: E402

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
INN = os.path.join(GOGN, "launatoflur.csv")
UT = os.path.join(GOGN, "launastig.csv")


def rekja_felag(rad, thekkt):
    """Sama þrepaskipta rakning og notuð er fyrir hækkanirnar."""
    for reitur in ("adili_1", "adili_2"):
        hrar = rad.get(reitur) or ""
        for hluti in [hrar] + hrar.replace(" og ", ",").split(","):
            n = samhaefa_heiti(hluti)
            if n and n in thekkt:
                return thekkt[n], "aðili úr skjali"
    kodi = rad.get("heimild")
    if kodi in FELAGSVEFIR:
        return FELAGSVEFIR[kodi], "vefur félagsins"
    return None, "órakið"


def main():
    if not os.path.exists(INN):
        print(f"{INN} fannst ekki - keyrðu scripts/utdrattur_launatoflur.py fyrst")
        return 1

    with open(INN, encoding="utf-8-sig", newline="") as f:
        radir = list(csv.DictReader(f))
    print(f"Taxtalínur inn: {len(radir):,}")

    # Þekkt félög úr hækkanagagnasettinu, til að rekja töflurnar eins
    thekkt = {}
    haekkanir = os.path.join(GOGN, "haekkanir_sameinad.csv")
    if os.path.exists(haekkanir):
        with open(haekkanir, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                n = samhaefa_heiti(r.get("felag"))
                if n and len(n) >= 3:
                    thekkt.setdefault(n, r["felag"])

    # Safna eftir (skjal, tafla) og halda aðeins gildum töflum
    hopar = collections.defaultdict(list)
    for r in radir:
        if r["athugasemd"]:
            continue
        if not r["gildir_fra"]:
            continue
        hopar[(r["skjal"], r["tafla_nr"])].append(r)

    ut = []
    talning = collections.Counter()
    for (skjal, tafla), linur in hopar.items():
        fjarhaedir = [float(r["fjarhaed"]) for r in linur]
        if len(fjarhaedir) < 4:
            continue
        fyrsta = linur[0]
        felag, rakning = rekja_felag(fyrsta, thekkt)
        talning[rakning] += 1
        if not felag:
            continue
        # Byrjunarlaun í lægsta flokki: lægsta þrep þess flokks sem er lægstur
        eftir_flokki = collections.defaultdict(dict)
        for r in linur:
            eftir_flokki[r["launaflokkur"]][int(r["threp_nr"])] = float(r["fjarhaed"])
        byrjun = [min(threp.items())[1] for threp in eftir_flokki.values() if threp]
        ut.append({
            "felag": felag,
            "rakning": rakning,
            "heimild": fyrsta["heimild"],
            "gildir_fra": fyrsta["gildir_fra"],
            "lagsti_taxti": round(min(byrjun)) if byrjun else "",
            "midgildi_taxti": round(statistics.median(fjarhaedir)),
            "haesti_taxti": round(max(fjarhaedir)),
            "fjoldi_launaflokka": len(eftir_flokki),
            "fjoldi_threpa": max((len(t) for t in eftir_flokki.values()), default=0),
            "taxtalinur": len(linur),
            "skjal": skjal,
        })

    # Ein lína á hvert (félag, dagsetning): miðgildi þegar fleiri töflur eiga við
    eftir_lykli = collections.defaultdict(list)
    for r in ut:
        eftir_lykli[(r["felag"], r["gildir_fra"])].append(r)
    endanlegt = []
    for (felag, dags), hopur in eftir_lykli.items():
        endanlegt.append({
            "felag": felag,
            "gildir_fra": dags,
            "lagsti_taxti": round(statistics.median(
                [r["lagsti_taxti"] for r in hopur if r["lagsti_taxti"] != ""])),
            "midgildi_taxti": round(statistics.median(
                [r["midgildi_taxti"] for r in hopur])),
            "haesti_taxti": round(statistics.median(
                [r["haesti_taxti"] for r in hopur])),
            "toflur": len(hopur),
            "rakning": hopur[0]["rakning"],
            "heimild": hopur[0]["heimild"],
            "skjal": hopur[0]["skjal"],
        })
    endanlegt.sort(key=lambda r: (r["felag"], r["gildir_fra"]))

    dalkar = ["felag", "gildir_fra", "lagsti_taxti", "midgildi_taxti",
              "haesti_taxti", "toflur", "rakning", "heimild", "skjal"]
    with open(UT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=dalkar, extrasaction="ignore")
        w.writeheader()
        w.writerows(endanlegt)

    print(f"Töflur alls:      {len(hopar):,}")
    for k, v in talning.most_common():
        print(f"   {k:<20} {v:,}")
    print(f"Mælipunktar út:   {len(endanlegt):,}")
    print(f"Félög:            {len({r['felag'] for r in endanlegt})}")
    if endanlegt:
        print(f"Tímabil:          {min(r['gildir_fra'] for r in endanlegt)} - "
              f"{max(r['gildir_fra'] for r in endanlegt)}")
    print(f"Skrifað í {UT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
