# -*- coding: utf-8 -*-
"""Mælir launahækkanir beint úr launatöflunum, óháð texta samninganna.

Samningur geymir iðulega eina launatöflu á hvert ár samningstímans. Sé sami
launaflokkur og sama starfsaldursþrep borið saman milli tveggja slíkra taflna
fæst hækkunin mæld beint í krónum - án þess að lesa eitt einasta orð.

Þetta er sjálfstæð mæling á sömu stærð og útdrátturinn úr textanum gefur, og
því raunverulegt viðmið: beri þeim saman styrkir það hvort tveggja.

Samanburðurinn er alltaf innan sama skjals. Milli skjala er hann ótækur, því
eitt skjal geymir oft margar ólíkar töflur - eina fyrir sveitarfélög, aðra
fyrir almenna markaðinn - og þær eru ekki sambærilegar.

Notkun:
    python scripts/taxtahaekkanir.py
"""
from __future__ import annotations

import collections
import csv
import os
import statistics
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sameina import FELAGSVEFIR  # noqa: E402
from launathroun import samhaefa_heiti  # noqa: E402

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
INN = os.path.join(GOGN, "launatoflur.csv")
UT = os.path.join(GOGN, "taxtahaekkanir.csv")

# Hækkun sem mælist utan þessara marka er ekki trúverðug sem áfangahækkun
MORK = (-2.0, 25.0)


def rekja_felag(rad, thekkt):
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
        radir = [r for r in csv.DictReader(f)
                 if not r["athugasemd"] and r["gildir_fra"]]
    print(f"Gildar taxtalínur: {len(radir):,}")

    thekkt = {}
    haekkanir = os.path.join(GOGN, "haekkanir_sameinad.csv")
    if os.path.exists(haekkanir):
        with open(haekkanir, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                n = samhaefa_heiti(r.get("felag"))
                if n and len(n) >= 3:
                    thekkt.setdefault(n, r["felag"])

    # skjal -> (launaflokkur, þrep) -> dagsetning -> fjárhæð
    eftir_skjali = collections.defaultdict(
        lambda: collections.defaultdict(dict))
    daemi_um_skjal = {}
    for r in radir:
        lykill = (r["launaflokkur"], r["threp_nr"])
        eftir_skjali[r["skjal"]][lykill][r["gildir_fra"]] = float(r["fjarhaed"])
        daemi_um_skjal.setdefault(r["skjal"], r)

    ut = []
    talning = collections.Counter()
    for skjal, reitir in eftir_skjali.items():
        # Safna öllum mældum breytingum milli samliggjandi dagsetninga
        breytingar = collections.defaultdict(list)
        for eftir_dags in reitir.values():
            dags = sorted(eftir_dags)
            for i in range(len(dags) - 1):
                fyrra, seinna = eftir_dags[dags[i]], eftir_dags[dags[i + 1]]
                if fyrra <= 0:
                    continue
                hlutfall = (seinna / fyrra - 1) * 100
                if MORK[0] <= hlutfall <= MORK[1]:
                    breytingar[(dags[i], dags[i + 1])].append(hlutfall)
        if not breytingar:
            continue
        syni = daemi_um_skjal[skjal]
        felag, rakning = rekja_felag(syni, thekkt)
        talning[rakning] += 1
        if not felag:
            continue
        for (fra, til), gildi in breytingar.items():
            if len(gildi) < 3:
                continue
            midgildi = statistics.median(gildi)
            # Almenn hækkun á að mælast eins í öllum flokkum. Mikil dreifing
            # þýðir að taflan breyttist að gerð, ekki bara að fjárhæð.
            spennt = max(gildi) - min(gildi)
            ut.append({
                "felag": felag,
                "rakning": rakning,
                "fra_dags": fra,
                "til_dags": til,
                "prosenta": round(midgildi, 2),
                "spennt": round(spennt, 2),
                "samraemd": int(spennt <= 0.5),
                "maelingar": len(gildi),
                "heimild": syni["heimild"],
                "skjal": skjal,
            })

    ut.sort(key=lambda r: (r["felag"], r["til_dags"]))
    dalkar = ["felag", "fra_dags", "til_dags", "prosenta", "spennt",
              "samraemd", "maelingar", "rakning", "heimild", "skjal"]
    with open(UT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=dalkar, extrasaction="ignore")
        w.writeheader()
        w.writerows(ut)

    samraemdar = sum(1 for r in ut if r["samraemd"])
    print(f"Skjöl með fleiri en eina dagsetta töflu: {len(eftir_skjali):,}")
    for k, v in talning.most_common():
        print(f"   {k:<20} {v}")
    print(f"Mældar hækkanir: {len(ut)} "
          f"({samraemdar} samræmdar yfir alla launaflokka)")
    print(f"Félög: {len({r['felag'] for r in ut})}")
    if ut:
        print(f"Tímabil: {min(r['fra_dags'] for r in ut)} - "
              f"{max(r['til_dags'] for r in ut)}")
    print(f"Skrifað í {UT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
