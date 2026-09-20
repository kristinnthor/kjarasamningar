# -*- coding: utf-8 -*-
"""Aðhvarfspróf á síunum í útdrættinum.

Hvert próf er raunverulegur texti úr samningi ásamt því hvort hann eigi að
skila launahækkun. Tilvikin sem eiga *ekki* að skila neinu eru þau sem hafa
raunverulega ratað ranglega inn í gagnasettið; hin eru þau sem freistandi
væri að sía burt með of grófri reglu.

Notkun:
    python scripts/profa_utdratt.py
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utdrattur import Argreining, utdrattur_ur_texta  # noqa: E402

# (heiti, texti, á að finnast hækkun, skýring)
PROFANIR = [
    # --- á ekki að skila hækkun ------------------------------------- #
    ("framlag í VIRK", False,
     "Framlag í starfsendurhæfingarsjóð er hlutfall af launum, ekki hækkun.",
     "launum starfsmanns til Menntunarsjóðs SSF6. 8.4 Starfsendurhæfingarsjóður "
     "8.4.1 Atvinnurekendur greiða 0,13%7 í VIRK-Starfsendurhæfingarsjóð. "
     "6 Gildir frá og með 1. júní 2024. 7 Gjald til VIRK-Starfsendurhæfingarsjóðs "
     "var tímabundið lækkað í 0,1% frá 1. janúar 2016."),
    ("gjald í orlofssjóð", False,
     "Sjóðsgjald, ekki launahækkun.",
     "7.gr. Orlofssjóður Frá 1. maí 2018 verður gjald í orlofssjóð 0,5% "
     "af heildarlaunum starfsmanns."),
    ("greiðsla í styrktarsjóð", False,
     "Greiðsla launagreiðanda í sjóð, ekki hækkun til starfsmanns.",
     "Launagreiðandi greiðir 0,55% af heildarlaunum starfsmanns í styrktarsjóð "
     "BHM. Frá og með 1. júlí 2020 breytist grein 14.2.1."),
    ("vaktaálag", False,
     "Prósentan skilgreinir álagstaxta en er ekki hækkun.",
     "Eftirfarandi gildir frá 1. nóvember 2024: 1.6.1 Vaktaálag reiknast af "
     "dagvinnukaupi. Vaktaálag skal vera: 33,33%"),
    ("launastig", False,
     "Fjárhæðin er launastig sem á heima í launatöflunum.",
     "Mánaðarlaun fyrir fullt starf skulu vera sem hér segir: "
     "Frá 1. júní 2018, kr. 300.000."),
    ("skilyrðisdagsetning", False,
     "Dagsetningin er skilyrði um ráðningartíma, ekki gildistaka.",
     "Launaþróunartrygging starfsmanna sem hófu störf fyrir 1. febrúar 2014."),
    ("orlofsréttur eftir starfsaldri", False,
     "Orlofsprósentan (10,17 / 11,59 / 13,04) er réttur eftir starfsaldri, "
     "ekki launabreyting.",
     "Við 10 ára starfsaldur eða 35 ára aldur skal hann fá 11,59%. Við 15 ára "
     "starfsaldur eða 50 ára aldur skal hann fá 13,04%. Starfsmenn í "
     "launaflokki 112 - 121 fá þó 11,59%."),
    ("orlofslaun reiknuð", False,
     "Hlutfall orlofslauna af heildarlaunum, ekki hækkun.",
     "Orlofslaun reiknast 10,17% af heildarlaunum frá 1. maí 2020."),
    ("eingreiðsla", False,
     "Stök uppgjörsgreiðsla, ekki hækkun á launum.",
     "1.2.1 Uppgjörsgreiðsla fyrir tímabilið 1. apríl 2019 til "
     "31. október 2019 er kr 75.500, sem greiðist í nóvember."),

    # --- á að skila hækkun ------------------------------------------ #
    ("ríkissjóður sem vinnuveitandi", True,
     "Ríkissjóður er viðsemjandi, ekki sjóður sem greitt er í.",
     "kjarasamningi fjármálaráðherra f.h. ríkissjóðs og SGS. "
     "Laun hækka um 3,5% þann 1. janúar 2025."),
    ("launaþróunartrygging", True,
     "Trygging er hér launahugtak en ekki vátrygging.",
     "Launabreytingar 1. janúar 2016 Þann 1. janúar 2016 hækka laun og "
     "launatengdir liðir um 6,2%, sbr. launaþróunartryggingu."),
    ("kauptrygging", True,
     "Kauptrygging er launaliður sem hækkar.",
     "Kauptrygging hækkar á samningstímabilinu sem hér segir: "
     "1. janúar 2025 hækkar kauptrygging um 3,5%."),
    ("prósenta eða krónutala", True,
     "Algengasta form áfangahækkunar.",
     "2. gr. Launahækkanir 1. janúar 2025: Laun hækka um 3,50% eða 23.750 kr."),
    ("áfangatafla", True,
     "Upptalning áfangahækkana.",
     "3. grein. Áfangahækkanir. Á samningstímanum hækka laun sem hér segir: "
     "1. júní 1988 3,25% 1. september 1988 2,5%"),
    ("krónutöluhækkun", True,
     "Hækkun sem eingöngu er krónutala.",
     "2. gr. Launahækkanir 1. apríl 2020: Laun hækka um 18.000 kr."),
    ("hækkun þótt orlof sé nefnt", True,
     "Orðið orlof stendur tilviljanakennt í sama glugga og fullgild hækkun; "
     "sían má ekki fella hana.",
     "Mánaðarlaun samkvæmt grein 1.1.1 skulu hækka hinn 1. september 1989 "
     "um 1.500 kr. Starfsmaður á rétt á orlofi samkvæmt lögum."),
]


def main():
    argr = Argreining("1985-01-01", "2028-12-31")
    fall = 0
    print(f"{'próf':<34}{'vænt':>8}{'fékkst':>9}  staða")
    print("-" * 70)
    for heiti, aetti, skyring, texti in PROFANIR:
        fannst = bool(utdrattur_ur_texta(texti, argr))
        ok = fannst == aetti
        if not ok:
            fall += 1
        print(f"{heiti:<34}{'hækkun' if aetti else 'ekkert':>8}"
              f"{'hækkun' if fannst else 'ekkert':>9}  "
              f"{'í lagi' if ok else 'FELLUR'}")
        if not ok:
            print(f"    {skyring}")
    print("-" * 70)
    if fall:
        print(f"{fall} af {len(PROFANIR)} prófum falla")
        return 1
    print(f"Öll {len(PROFANIR)} prófin standast")
    return 0


if __name__ == "__main__":
    sys.exit(main())
