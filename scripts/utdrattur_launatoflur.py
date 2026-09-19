# -*- coding: utf-8 -*-
"""Dregur launatöflur út úr kjarasamningum: fjárhæðir á launaflokk og þrep.

Ólíkt hækkununum gefa töflurnar raunverulegt launastig, ekki breytingu. Þær
eru líka forsenda þess að hægt sé að umbreyta krónutöluhækkunum í hlutföll.

Þrennt þarf að halda utan um samhliða, því tölurnar einar eru merkingarlausar:

  gildir_fra    hvenær taflan tók gildi ("Gilda frá 1. apríl 2026")
  maelikvardi   mánaðarlaun, tímakaup í dagvinnu, yfirvinnukaup, álag …
                Sama tafla er oft endurtekin í hverjum mælikvarða.
  threp         starfsaldursþrep dálkanna ("Byrjunarl.", "1 ár", "3 ár" …)

Notkun:
    python scripts/utdrattur_launatoflur.py --kanna 20
    python scripts/utdrattur_launatoflur.py
"""
from __future__ import annotations

import csv
import logging
import os
import re
import sys
import warnings
from concurrent.futures import ProcessPoolExecutor

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pypdf import PdfReader  # noqa: E402
from utdrattur import MANUDIR, MAN_RE  # noqa: E402
from utdrattur_pdf import (  # noqa: E402
    skjol_til_vinnslu, finna_adila, finna_gildistima, HEIMILDANOFN)

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
UT = os.path.join(GOGN, "launatoflur.csv")

# ---------------------------------------------------------------------- #
# Mynstur                                                                #
# ---------------------------------------------------------------------- #

# "Gilda frá 1. apríl 2026", "Launatafla 1.2.2024", "Gildir frá 1. maí 2015"
DAGS_ORD = re.compile(
    rf"(?:launatafl\w*|launataxt\w*|kauptaxt\w*|gild\w*|tekur\s+gildi)"
    rf"[\s,:—–-]*(?:frá|f\.?o\.?m\.?|og\s+með|gildir)*[\s,:—–-]*"
    rf"(\d{{1,2}})\s*\.\s*({MAN_RE})\s*\.?\s*(\d{{4}})", re.I)
DAGS_TOLUR = re.compile(
    r"(?:launatafla|kauptaxtar?|gildir?\s+frá)\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", re.I)

# Mælikvarðar. Röðin skiptir máli - sértækast fyrst.
MAELIKVARDAR = [
    ("vaktaálag", re.compile(r"^\s*vaktaálag", re.I)),
    ("stórhátíðakaup", re.compile(r"^\s*stórhátíða", re.I)),
    ("yfirvinnukaup", re.compile(r"^\s*yfirvinn", re.I)),
    ("tímakaup í dagvinnu", re.compile(r"^\s*(?:dagvinna|tímakaup)", re.I)),
    ("mánaðarlaun", re.compile(r"^\s*mánaðarlaun", re.I)),
]

# Fjárhæð: 476.379 eða 2.748,39 eða 476379
FJARHAED = r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{4,7}(?:,\d{1,2})?"

# "Launaflokkur 4   476.379 481.143 …"  /  "126 434.191 440.178 …"
TAXTALINA = re.compile(
    rf"^[\s|]*(?:launafl(?:okkur|\.)?|lfl\.?|fl\.?|flokkur)?[\s|]*"
    rf"(\d{{1,3}})[\s|]+((?:(?:{FJARHAED})[\s|]*){{2,14}})$", re.I)

# Dálkahaus: "Starfsaldur Byrjunarl. 1 ár 3 ár 5 ár"
THREPAHAUS = re.compile(r"(byrjunarl|starfsaldur|grunnlaun|grunnl\.|eftir\s*\d)", re.I)
THREP = re.compile(r"byrjunarl\w*\.?|grunnl\w*\.?|eftir\s*\d+\s*(?:ár|mán\w*)|"
                   r"\d+\s*ár|\d+\s*mán\w*", re.I)

# Skynsamleg mörk eftir mælikvarða, til að hafna rusli
MORK = {
    "mánaðarlaun": (15_000, 3_000_000),
    "tímakaup í dagvinnu": (50, 20_000),
    "yfirvinnukaup": (100, 40_000),
    "stórhátíðakaup": (100, 50_000),
    "vaktaálag": (10, 40_000),
}


def lesa_fjarhaed(s: str):
    s = s.strip()
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    return float(s.replace(".", ""))


def finna_dagsetningu(lina: str):
    m = DAGS_ORD.search(lina)
    if m:
        man = MANUDIR.get(m.group(2).lower().rstrip("."))
        if man:
            return f"{m.group(3)}-{man:02d}-{int(m.group(1)):02d}"
    m = DAGS_TOLUR.search(lina)
    if m:
        d, man, ar = int(m.group(1)), int(m.group(2)), m.group(3)
        if 1 <= man <= 12 and 1 <= d <= 31:
            return f"{ar}-{man:02d}-{d:02d}"
    return None


def finna_threp(lina: str):
    fundin = [" ".join(x.split()) for x in THREP.findall(lina)]
    return fundin or None


def lesa_sidu(texti: str, stada: dict):
    """Les eina blaðsíðu og skilar töxtum. `stada` lifir milli blaðsíðna."""
    ut = []
    for lina in texti.split("\n"):
        hreint = lina.rstrip()
        if not hreint.strip():
            continue

        d = finna_dagsetningu(hreint)
        if d and d != stada.get("gildir_fra"):
            stada["gildir_fra"] = d
            stada["tafla_nr"] = stada.get("tafla_nr", 0) + 1

        for heiti, mynstur in MAELIKVARDAR:
            if mynstur.match(hreint):
                if heiti != stada.get("maelikvardi"):
                    stada["tafla_nr"] = stada.get("tafla_nr", 0) + 1
                stada["maelikvardi"] = heiti
                break

        if THREPAHAUS.search(hreint) and not TAXTALINA.match(hreint):
            th = finna_threp(hreint)
            if th:
                # Nýr dálkahaus markar upphaf nýrrar töflu
                stada["threp"] = th
                stada["tafla_nr"] = stada.get("tafla_nr", 0) + 1
                stada.setdefault("sedir_flokkar", set()).clear()
                continue

        m = TAXTALINA.match(hreint)
        if not m:
            continue
        flokkur = m.group(1)
        # Innan einnar töflu kemur hver launaflokkur aðeins einu sinni fyrir.
        # Endurtekning þýðir að ný tafla er hafin - samningar geyma iðulega
        # eina töflu á hvert ár samningstímans, hverja á eftir annarri.
        sedir = stada.setdefault("sedir_flokkar", set())
        if flokkur in sedir:
            stada["tafla_nr"] = stada.get("tafla_nr", 0) + 1
            sedir.clear()
        sedir.add(flokkur)
        fjarhaedir = re.findall(FJARHAED, m.group(2))
        if len(fjarhaedir) < 2:
            continue
        maeli = stada.get("maelikvardi")
        if not maeli:
            # Þegar fyrirsögn vantar má lesa mælikvarðann af stærðargráðunni:
            # mánaðarlaun eru í hundruðum þúsunda, tímakaup í þúsundum.
            try:
                fyrsta = lesa_fjarhaed(fjarhaedir[0])
            except ValueError:
                continue
            maeli = "mánaðarlaun" if fyrsta >= 50_000 else "tímakaup í dagvinnu"
        lagmark, hamark = MORK.get(maeli, (10, 3_000_000))
        threp = stada.get("threp") or []
        for i, f in enumerate(fjarhaedir):
            try:
                gildi = lesa_fjarhaed(f)
            except ValueError:
                continue
            if not (lagmark <= gildi <= hamark):
                continue
            ut.append({
                "gildir_fra": stada.get("gildir_fra") or "",
                "tafla_nr": stada.get("tafla_nr", 1),
                "maelikvardi": maeli,
                "launaflokkur": flokkur,
                "threp_nr": i + 1,
                "threp": threp[i] if i < len(threp) else "",
                "fjarhaed": gildi,
            })
    return ut


def stadfesta(radir):
    """Merkir línur sem brjóta innri reglu töflunnar.

    Innan sama launaflokks eiga fjárhæðir að hækka eftir starfsaldursþrepum.
    Brot á því er sterk vísbending um OCR-villu eða ranga þáttun.
    """
    eftir_rod = {}
    for r in radir:
        lykill = (r.get("skjal"), r["tafla_nr"], r["launaflokkur"])
        eftir_rod.setdefault(lykill, []).append(r)
    for rod in eftir_rod.values():
        rod.sort(key=lambda r: r["threp_nr"])
        fyrra = None
        for r in rod:
            r["athugasemd"] = ""
            if fyrra is not None and r["fjarhaed"] < fyrra:
                r["athugasemd"] = "lægra en fyrra þrep"
            fyrra = max(fyrra or 0, r["fjarhaed"])
    return radir


DALKAR = ["heimild", "heimild_heiti", "skjal", "adili_1", "adili_2",
          "samningur_fra", "samningur_til", "gildir_fra", "tafla_nr", "maelikvardi",
          "launaflokkur", "threp_nr", "threp", "fjarhaed", "athugasemd"]


def vinna_skjal(verk):
    """Vinnur eitt skjal. Sjálfstætt fall svo hægt sé að dreifa á ferli."""
    rel, leid = verk
    try:
        lesari = PdfReader(leid)
        sidur = list(lesari.pages[:200])
    except Exception:
        return rel, []

    ur_skjali, haus_texti = lesa_skjal(sidur, "plain")
    if not ur_skjali:
        ur_skjali, haus_texti = lesa_skjal(sidur, "layout")
    ur_skjali = [r for r in ur_skjali if r["maelikvardi"] == "mánaðarlaun"]

    sed, einstakar = set(), []
    for r in ur_skjali:
        lykill = (r["tafla_nr"], r["launaflokkur"], r["threp_nr"], r["fjarhaed"])
        if lykill in sed:
            continue
        sed.add(lykill)
        einstakar.append(r)
    if not einstakar:
        return rel, []

    a1, a2 = finna_adila(haus_texti)
    fra, til = finna_gildistima(haus_texti, os.path.basename(rel))
    kodi = rel.split("/")[0]
    for r in einstakar:
        r.update({"heimild": kodi,
                  "heimild_heiti": HEIMILDANOFN.get(kodi, kodi),
                  "skjal": rel, "adili_1": a1, "adili_2": a2,
                  "samningur_fra": fra or "", "samningur_til": til or ""})
        if not r["gildir_fra"]:
            r["gildir_fra"] = fra or ""
    return rel, einstakar


def lesa_skjal(sidur, hamur: str):
    """Les allar blaðsíður skjalsins í tilteknum textaham."""
    stada: dict = {}
    radir, haus = [], ""
    for nr, bls in enumerate(sidur):
        try:
            texti = (bls.extract_text(extraction_mode="layout") if hamur == "layout"
                     else bls.extract_text()) or ""
        except Exception:
            continue
        if nr < 3:
            haus += "\n" + texti
        radir.extend(lesa_sidu(texti, stada))
    return radir, haus


def main(argv):
    kanna = "--kanna" in argv
    hamark = int(argv[argv.index("--kanna") + 1]) if kanna else 0
    ferli = int(argv[argv.index("--ferli") + 1]) if "--ferli" in argv else (os.cpu_count() or 4)

    skjol = skjol_til_vinnslu()
    if kanna:
        skjol = [s for s in skjol if re.search(r"taxt|launatafl|kjarasamn",
                                               s[0], re.I)][:hamark]
    print(f"Skjöl til vinnslu: {len(skjol)} ({ferli} ferli)")

    allar = []
    med = 0
    with ProcessPoolExecutor(max_workers=ferli) as safn:
        for i, (rel, radir) in enumerate(safn.map(vinna_skjal, skjol, chunksize=4), 1):
            if radir:
                med += 1
                allar.extend(radir)
            if i % 200 == 0:
                print(f"  {i}/{len(skjol)} - {len(allar)} taxtalínur úr {med} skjölum")

    allar = stadfesta(allar)

    if kanna:
        for r in allar[:30]:
            print(f"  {r['gildir_fra']:>10} | {r['maelikvardi']:<22} | "
                  f"fl {r['launaflokkur']:>3} | þrep {r['threp_nr']} "
                  f"{r['threp'][:10]:<10} | {r['fjarhaed']:>12,.2f} "
                  f"{r['athugasemd']}")
        print(f"\n{len(allar)} taxtalínur úr {med} skjölum")
        return

    os.makedirs(GOGN, exist_ok=True)
    with open(UT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DALKAR, extrasaction="ignore")
        w.writeheader()
        w.writerows(allar)
    gallad = sum(1 for r in allar if r["athugasemd"])
    print(f"\nSkjöl með launatöflu: {med}")
    print(f"Taxtalínur: {len(allar)} (þar af {gallad} með athugasemd)")
    print(f"Skrifað í {UT}")


if __name__ == "__main__":
    main(sys.argv[1:])
