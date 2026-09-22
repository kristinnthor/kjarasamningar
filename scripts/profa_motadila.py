# -*- coding: utf-8 -*-
"""Aðhvarfspróf á stöðlun mótaðila.

Hvert próf er raunverulegt heiti eins og það birtist í skránni eða í
vefskjali, ásamt þeim mótaðila sem það á að staðlast í. Röng stöðlun blandar
sérsamningum inn í aðalsamning, svo þetta er verndað sérstaklega.

Notkun:
    python scripts/profa_motadila.py
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import motadilar as M  # noqa: E402

# Skrá ríkissáttasemjara: (heiti í skránni, vænt auðkenni)
UR_SKRA = [
    ("Samtök atvinnulífsins, SA", "sa"),
    ("Samtök atvinnulífsins, SA (millilandaskip)", "sa"),
    ("SA Greiðasala", "sa"),
    ("VSÍ", "sa"),                                   # forveri SA
    ("Vinnuveitendasamband Íslands, Vinnumálasambands samvinnufélaganna", "sa"),
    ("Samtök rafverktaka", "sa"),                    # aðili að SA
    ("Samninganefnd bankanna", "sa"),                # forveri í samningum SSF
    ("Ríkissjóður, SNR", "riki"),
    ("Ríkissjóður, SNR, Landhelgisgæsla Íslands", "riki"),
    ("Samband íslenskra sveitarfélaga", "sveitarfelog"),
    ("Reykjavíkurborg", "reykjavikurborg"),
    ("Félag atvinnurekenda", "fa"),
    ("Landssamband íslenskra útvegsmanna", "sfs"),   # forveri SFS
    ("Síminn hf.", "fy-siminn"),
    ("Símans hf.", "fy-siminn"),                     # eignarfall
    ("RARIK ohf.", "fy-rarik"),
    ("RARIK", "fy-rarik"),                           # án lagaforms
    ("Advania Ísland ehf.", "fy-advania-island"),
]

# Vefskjöl: (aðili 1, aðili 2, skjal, vefur, vænt auðkenni)
UR_VEFSKJALI = [
    ("", "SAMTAKA ATVINNULÍFSINS", "vr/samningur.pdf", "vr", "sa"),
    ("Samtaka atvinnulífsins", "Starfsgreinasambands Íslands", "sgs/x.pdf", "sgs", "sa"),
    ("", "Félags atvinnurekenda", "vr/fa.pdf", "vr", "fa"),
    ("fjármála- og efnahagsráðherra f.h. ríkissjóðs", "", "x.pdf", "bsrb", "riki"),
    ("SAMBANDS ÍSLENSKRA SVEITARFÉLAGA F.H. ÞEIRRA SVEITARFÉLAGA", "", "x.pdf", "sgs", "sveitarfelog"),
    ("Reykjavíkurborgar", "", "x.pdf", "efling", "reykjavikurborg"),
    # Skráarheitið segir til um mótaðilann þegar aðilareitirnir eru rusl
    ("fylgiskjöl", "miðlunargrein", "sgs/kjarasamningur-sgs-og-sambands-islenskra-sveitarfelaga-2020.pdf",
     "sgs", "sveitarfelog"),
    ("", "", "reykjavik/kalfur-rvk-sameyki-loka.pdf", "reykjavik", "reykjavikurborg"),
    # Vefur viðsemjanda segir til um mótaðilann þegar ekkert annað gerir það
    ("", "", "sa/kjoelfar_loka.pdf", "sa", "sa"),
    # Ruslið eitt og sér á að gefa óþekktan mótaðila, ekki giska
    ("fylgiskjöl", "ANNARRA AÐILA", "grafia/kynning.pdf", "grafia", "othekktur"),
]


def main():
    fyrirtaeki = M.Fyrirtaekjaskra(
        ["Landsvirkjun", "Norðurorka hf.", "Rafiðnaðarsamband Íslands"],
        stettarfelog=["Rafiðnaðarsamband Íslands"])
    fall = 0
    print(f"{'heiti':<58}{'vænt':>18}{'fékkst':>18}")
    print("-" * 96)
    for heiti, vaent in UR_SKRA:
        fekkst = M.ur_skra(heiti)[0]
        ok = fekkst == vaent
        fall += not ok
        print(f"{heiti[:56]:<58}{vaent:>18}{fekkst:>18}  {'í lagi' if ok else 'FELLUR'}")
    for a1, a2, skjal, vefur, vaent in UR_VEFSKJALI:
        fekkst = M.ur_vefskjali(a1, a2, skjal, fyrirtaeki, vefur)[0]
        ok = fekkst == vaent
        fall += not ok
        heiti = (a1 or a2 or skjal)[:56]
        print(f"{heiti:<58}{vaent:>18}{fekkst:>18}  {'í lagi' if ok else 'FELLUR'}")
    # Fyrirtæki í eignarfalli þekkjast, en stéttarfélag má aldrei teljast mótaðili
    for texti, vaent in [("Landsvirkjunar", "fy-landsvirkjun"),
                         ("Norðurorku hf", "fy-nordurorka"),
                         ("Rafiðnaðarsambands Íslands", None)]:
        f = fyrirtaeki.leita(texti)
        fekkst = f[0] if f else None
        ok = fekkst == vaent
        fall += not ok
        print(f"{texti:<58}{str(vaent):>18}{str(fekkst):>18}  {'í lagi' if ok else 'FELLUR'}")
    print("-" * 96)
    alls = len(UR_SKRA) + len(UR_VEFSKJALI) + 3
    if fall:
        print(f"{fall} af {alls} prófum falla")
        return 1
    print(f"Öll {alls} prófin standast")
    return 0


if __name__ == "__main__":
    sys.exit(main())
