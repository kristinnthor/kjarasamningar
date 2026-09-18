# -*- coding: utf-8 -*-
"""Dregur launahækkanir úr PDF-skjölum sem sótt voru af vefjum félaganna.

Ólíkt skrá ríkissáttasemjara fylgja þessum skjölum engin lýsigögn, svo bæði
samningsaðilar og gildistími eru lesin úr skjalinu sjálfu. Niðurstaðan fer í
sérskrá og ber alltaf með sér hversu örugg rakningin er, svo hún blandist ekki
saman við þær færslur sem hafa staðfest lýsigögn.

Notkun:
    python scripts/utdrattur_pdf.py --kanna 15   # prófa á fáum skjölum
    python scripts/utdrattur_pdf.py              # keyra á öllu safninu
"""
from __future__ import annotations

import csv
import logging
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pypdf import PdfReader  # noqa: E402
from utdrattur import Argreining, utdrattur_ur_texta, MAN_RE  # noqa: E402
from heimildir import HEIMILDIR  # noqa: E402

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMNINGAR = os.path.join(ROT, "samningar")
YFIRLIT = os.path.join(SAMNINGAR, "_yfirlit.csv")
GOGN = os.path.join(ROT, "gogn")
UT = os.path.join(GOGN, "haekkanir_vefskjol.csv")

HEIMILDANOFN = {h["kodi"]: h["heiti"] for h in HEIMILDIR}

# Samningsaðilar eru nær alltaf nefndir á fyrstu síðu, en orðalagið er
# breytilegt. Mynstrin eru reynd í forgangsröð, frá afdráttarlausasta.
ADILAR_MYNSTUR = [
    # "milli Samtaka atvinnulífsins annars vegar og VR hins vegar"
    re.compile(r"\bmilli\s+(.{5,130}?)\s+annars\s+vegar\s+og\s+(.{5,130}?)\s+hins\s+vegar",
               re.I | re.S),
    # "milli X og Y um ..." / "milli X og Y\n"
    re.compile(r"\bmilli\s+(.{5,110}?)\s+og\s+(.{5,110}?)(?=\s*(?:\n|um\b|vegna\b|\d\.))",
               re.I | re.S),
    # "KJARASAMNINGUR\n X \n og \n Y"
    re.compile(r"KJARASAMNINGUR\s*\n+\s*(.{4,90}?)\s*\n+\s*og\s*\n+\s*(.{4,90}?)\s*(?:\n|$)",
               re.I),
    # "Kjarasamningur X og Y"
    re.compile(r"(?:kjara)?samningur\s+(.{5,90}?)\s+og\s+(.{5,90}?)(?=\s*(?:\n|um\b|\d\.))",
               re.I | re.S),
]

GILDISTIMI = re.compile(
    rf"gild(?:ir|istími)\s*(?:er\s*)?frá\s*(?:og með\s*)?(\d{{1,2}})\s*\.\s*({MAN_RE})"
    rf"\s*\.?\s*(\d{{4}}).{{0,40}}?til\s*(\d{{1,2}})\s*\.\s*({MAN_RE})\s*\.?\s*(\d{{4}})",
    re.I | re.S)
AR_I_NAFNI = re.compile(r"(19\d{2}|20\d{2})\s*[-–_]\s*(19\d{2}|20\d{2})")

from utdrattur import MANUDIR  # noqa: E402


def lesa_texta(leid: str, hamark_sidna: int = 60) -> str:
    """Les texta úr PDF. Skilar tómum streng ef skjalið er ólæsilegt.

    Sum skjöl í safninu eru dulkóðuð eða gölluð og kasta villu bæði við opnun
    og þegar reynt er að telja síður, svo hvort tveggja þarf að verja.
    """
    try:
        r = PdfReader(leid)
        sidur = list(r.pages[:hamark_sidna])
    except Exception:
        return ""
    bitar = []
    for bls in sidur:
        try:
            bitar.append(bls.extract_text() or "")
        except Exception:
            continue
    return "\n".join(bitar)


def finna_gildistima(texti: str, skraarnafn: str):
    """Skilar (fra, til) á ISO-formi, eða (None, None)."""
    m = GILDISTIMI.search(texti[:8000])
    if m:
        d1, m1, a1, d2, m2, a2 = m.groups()
        n1 = MANUDIR.get(m1.lower().rstrip("."))
        n2 = MANUDIR.get(m2.lower().rstrip("."))
        if n1 and n2:
            return f"{a1}-{n1:02d}-{int(d1):02d}", f"{a2}-{n2:02d}-{int(d2):02d}"
    m = AR_I_NAFNI.search(skraarnafn)
    if m:
        return f"{m.group(1)}-01-01", f"{m.group(2)}-12-31"
    return None, None


def hreinsa_adila(s: str) -> str:
    s = " ".join(s.split())
    s = re.sub(r"^(?:annars vegar|hins vegar|samnings?)\s+", "", s, flags=re.I)
    s = re.sub(r"\s+(?:annars|hins)\s+vegar$", "", s, flags=re.I)
    return s[:110].strip(" ,.-:")


def finna_adila(texti: str):
    haus = texti[:4000]
    for mynstur in ADILAR_MYNSTUR:
        m = mynstur.search(haus)
        if m:
            a, b = hreinsa_adila(m.group(1)), hreinsa_adila(m.group(2))
            if 3 <= len(a) <= 110 and 3 <= len(b) <= 110:
                return a, b
    return None, None


DALKAR = [
    "heimild", "heimild_heiti", "skjal", "adili_1", "adili_2",
    "rakning", "samningur_fra", "samningur_til",
    "gildir_fra", "tegund", "prosenta", "kronur", "a_vid",
    "artal_stada", "tilvitnun",
]


def skjol_til_vinnslu():
    """Einstök skjöl utan heildarskrárinnar, tvítök undanskilin."""
    frumeintok = None
    if os.path.exists(YFIRLIT):
        frumeintok = set()
        with open(YFIRLIT, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r["er_tvitak"] == "0":
                    frumeintok.add(r["skra"])
    ut = []
    for mappa, _, nofn in os.walk(SAMNINGAR):
        grunnur = os.path.basename(mappa)
        if grunnur in ("rikissattasemjari", "_tvitok", "pdf", "ocr_texti"):
            continue
        if "rikissattasemjari" in mappa or "_tvitok" in mappa:
            continue
        for n in nofn:
            if not n.lower().endswith(".pdf"):
                continue
            rel = os.path.relpath(os.path.join(mappa, n), SAMNINGAR).replace("\\", "/")
            if frumeintok is not None and rel not in frumeintok:
                continue
            ut.append((rel, os.path.join(mappa, n)))
    return sorted(ut)


def main(argv):
    kanna = "--kanna" in argv
    hamark = int(argv[argv.index("--kanna") + 1]) if kanna else 0

    skjol = skjol_til_vinnslu()
    if kanna:
        skjol = skjol[:hamark]
    print(f"Skjöl til vinnslu: {len(skjol)}")

    radir = []
    med, an_texta = 0, 0
    for i, (rel, leid) in enumerate(skjol, 1):
        texti = lesa_texta(leid)
        if len(texti) < 500:
            an_texta += 1
            continue
        kodi = rel.split("/")[0]
        fra, til = finna_gildistima(texti, os.path.basename(rel))
        a1, a2 = finna_adila(texti)
        rakning = "aðilar úr skjali" if a1 else "aðeins heimild"
        argr = Argreining(fra, til)
        haekkanir = utdrattur_ur_texta(texti, argr)
        if haekkanir:
            med += 1
        for h in haekkanir:
            radir.append({
                "heimild": kodi,
                "heimild_heiti": HEIMILDANOFN.get(kodi, kodi),
                "skjal": rel,
                "adili_1": a1, "adili_2": a2,
                "rakning": rakning,
                "samningur_fra": fra or "", "samningur_til": til or "",
                **h,
            })
        if i % 100 == 0:
            print(f"  {i}/{len(skjol)} - {len(radir)} hækkanir, {an_texta} án texta")

    if kanna:
        for r in radir[:20]:
            print(f"\n{r['gildir_fra']} | {r['prosenta'] or '-'}% | {r['kronur'] or '-'} kr "
                  f"| {r['a_vid']} | {r['heimild']} | {r['rakning']}")
            print(f"   aðilar: {r['adili_1']} <-> {r['adili_2']}")
            print(f"   {r['tilvitnun'][:200]}")
        return

    os.makedirs(GOGN, exist_ok=True)
    radir.sort(key=lambda r: (r["gildir_fra"], r["heimild"]))
    with open(UT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DALKAR, extrasaction="ignore")
        w.writeheader()
        w.writerows(radir)
    print(f"\nSkjöl: {len(skjol)}, án nothæfs texta: {an_texta}, "
          f"með hækkun: {med}")
    print(f"Hækkanir alls: {len(radir)}")
    print(f"Skrifað í {UT}")


if __name__ == "__main__":
    main(sys.argv[1:])
