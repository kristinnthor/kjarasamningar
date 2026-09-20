# -*- coding: utf-8 -*-
"""Gæðapróf á gagnasettinu. Skilar villukóða ef eitthvað stenst ekki.

Prófin byggja á staðreyndum sem hljóta að gilda ef úrvinnslan er rétt, svo þau
grípa villur sem tölurnar einar leyna. Það mikilvægasta er samanburðurinn við
launavísitölu Hagstofunnar: hún mælir raunverulega launaþróun með launaskriði,
svo umsamdar hækkanir einar eiga alltaf að liggja undir henni. Fari félag yfir
hana er það merki um tvítalningu.

Notkun:
    python scripts/gaedaprof.py
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")

villur = []
advaranir = []


def lesa(skra):
    leid = os.path.join(GOGN, skra)
    if not os.path.exists(leid):
        return []
    with open(leid, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def profa(heiti, skilyrdi, skilabod, alvarlegt=True):
    if skilyrdi:
        print(f"  [í lagi]  {heiti}")
    else:
        merki = "VILLA" if alvarlegt else "aðvörun"
        print(f"  [{merki}]  {heiti}: {skilabod}")
        (villur if alvarlegt else advaranir).append(f"{heiti}: {skilabod}")


def main():
    haekkanir = lesa("haekkanir_sameinad.csv") or lesa("haekkanir.csv")
    rod = lesa("launathroun_eftir_felagi.csv")
    felog = lesa("felog.csv")
    lv = {r["Mánuður"]: float(r["gildi"])
          for r in lesa("launavisitala_manadarleg.csv")
          if r["Eining"] == "Vísitölugildi"}

    print("Grunngögn")
    profa("hækkanir til", bool(haekkanir), "haekkanir_sameinad.csv er tóm")
    profa("tímaröð til", bool(rod), "launathroun_eftir_felagi.csv er tóm")
    profa("launavísitala til", bool(lv), "launavisitala_manadarleg.csv er tóm")
    if not (haekkanir and rod and lv):
        return 1

    print("\nGildissvið")
    pros = [float(r["prosenta"]) for r in haekkanir if r["prosenta"]]
    kr = [float(r["kronur"]) for r in haekkanir if r["kronur"]]
    profa("prósentur innan marka", all(0 < p <= 15 for p in pros),
          f"{sum(1 for p in pros if not 0 < p <= 15)} utan 0-15%")
    profa("krónutölur innan marka", all(500 <= k <= 100_000 for k in kr),
          f"{sum(1 for k in kr if not 500 <= k <= 100_000)} utan 500-100.000")
    midgildi = sorted(pros)[len(pros) // 2]
    profa("miðgildi prósentu trúverðugt", 2.0 <= midgildi <= 5.0,
          f"miðgildi er {midgildi}%, sem er utan þess sem búast má við")

    print("\nDagsetningar")
    dags = [r["gildir_fra"] for r in haekkanir if r["gildir_fra"]]
    framtid = [d for d in dags if d > "2030-01-01"]
    fortid = [d for d in dags if d < "1960-01-01"]
    profa("engar fjarlægar framtíðardagsetningar", not framtid,
          f"{len(framtid)} eftir 2030")
    profa("engar fjarlægar fortíðardagsetningar", not fortid,
          f"{len(fortid)} fyrir 1960")

    print("\nTímaröð")
    lyklar = [(r["felag_lykill"], r["dagsetning"]) for r in rod]
    profa("ein lína á hvert (félag, dagsetning)", len(lyklar) == len(set(lyklar)),
          f"{len(lyklar) - len(set(lyklar))} tvítök")

    print("\nSamanburður við launavísitölu Hagstofunnar")

    # Vísitala félagsins á tilteknum degi. Samningar ná fram í tímann (2028) en
    # launavísitalan aðeins til dagsins í dag, svo bera verður saman á sama degi
    # - annars er verið að mæla ólík tímabil hvort gegn öðru.
    eftir_lykli = {}
    for r in rod:
        eftir_lykli.setdefault(r["felag_lykill"], []).append(r)
    for linur in eftir_lykli.values():
        linur.sort(key=lambda r: r["dagsetning"])

    def visitala_vid(lykill, dagur):
        svar = None
        for r in eftir_lykli.get(lykill, []):
            if r["dagsetning"] > dagur:
                break
            if r.get("visitala_samfella") not in ("", None):
                svar = float(r["visitala_samfella"])
        return svar

    yfir = []
    profud = 0
    for f in felog:
        if f["heilleiki"] != "samfelld":
            continue
        # Samanburðurinn verður að miðast við sama upphaf og vísitalan.
        # Frá og með nýju samfelluskilgreiningunni hefst hún við samfelld_fra,
        # ekki fyrstu mælingu félagsins.
        fra = f.get("samfelld_fra") or f["fyrsta"]
        til = min(f["sidasta"], "2026-07-01")
        m1, m2 = f"{fra[:4]}M{fra[5:7]}", f"{til[:4]}M{til[5:7]}"
        if m1 not in lv or m2 not in lv or fra >= til:
            continue
        okkar = visitala_vid(f["felag_lykill"], til)
        if okkar is None:
            continue
        profud += 1
        hag = lv[m2] / lv[m1] * 100
        if okkar > hag * 1.02:
            yfir.append(f"{f['felag']} {okkar:.0f} > {hag:.0f}")
    profa(f"engin samfelld röð yfir launavísitölu ({profud} prófuð)",
          not yfir, "; ".join(yfir[:5]))

    print("\nRekjanleiki")
    an_tilvitnunar = sum(1 for r in haekkanir if not (r.get("tilvitnun") or "").strip())
    profa("allar hækkanir bera tilvitnun", an_tilvitnunar == 0,
          f"{an_tilvitnunar} án tilvitnunar")

    print()
    if villur:
        print(f"{len(villur)} villur, {len(advaranir)} aðvaranir")
        return 1
    print(f"Allt stóðst. {len(advaranir)} aðvaranir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
