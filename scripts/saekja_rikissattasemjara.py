# -*- coding: utf-8 -*-
"""Sækir heildarskrá ríkissáttasemjara yfir kjarasamninga (kjarasamningar.is).

Ríkissáttasemjari safnar öllum kjarasamningum á grundvelli laga nr. 80/1938 og
birtir þá á kjarasamningar.is. Bakendinn skilar bæði lýsigögnum, PDF-slóð og
OCR-texta hvers samnings.

Notkun:
    python scripts/saekja_rikissattasemjara.py --lysigogn   # aðeins lýsigögn
    python scripts/saekja_rikissattasemjara.py --pdf        # sækja PDF-skjölin
    python scripts/saekja_rikissattasemjara.py --texti      # vista OCR-texta
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date

import requests

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMNINGAR = os.path.join(ROT, "samningar")
MAPPA = os.path.join(SAMNINGAR, "rikissattasemjari")
PDF_MAPPA = os.path.join(MAPPA, "pdf")
TEXTI_MAPPA = os.path.join(MAPPA, "ocr_texti")
JSON_SKRA = os.path.join(MAPPA, "lysigogn.json")
CSV_SKRA = os.path.join(MAPPA, "lysigogn.csv")

API = "https://api.kjarasamningar.hestafl.is/api/samningar"
HAUSAR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

CSV_DALKAR = [
    "id", "contract_id", "filename", "launthegi_canonical", "launthegi",
    "atvinnurekandi", "kennitala_launthega", "kennitala_atvinnurekanda",
    "heildarsamtok", "markadsflokk", "tegund", "fra", "til", "fra_year",
    "er_kjarasamningur", "er_virkur", "foreldrasamningur", "par_id",
    "source", "pdf_url", "pdf_skra", "texta_skra", "ocr_lengd",
]


def hreinsa(s: str, hamark: int = 120) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"[\\/:*?\"<>|\r\n\t]", "-", s)
    s = re.sub(r"\s+", " ", s).strip(" .-_")
    return s[:hamark].rstrip(" .-_") or "skjal"


def saekja_lysigogn(s: requests.Session) -> list[dict]:
    allt: list[dict] = []
    sida = 1
    while True:
        r = s.get(API, params={"page": sida, "per_page": 100}, timeout=90)
        r.raise_for_status()
        d = r.json()
        allt.extend(d["data"])
        print(f"  síða {sida}/{d['last_page']} - {len(allt)}/{d['total']}")
        if sida >= d["last_page"]:
            break
        sida += 1
        time.sleep(0.2)
    return allt


def main(argv):
    vil_pdf = "--pdf" in argv
    vil_texta = "--texti" in argv
    os.makedirs(MAPPA, exist_ok=True)

    s = requests.Session()
    s.headers.update(HAUSAR)

    if os.path.exists(JSON_SKRA) and "--endurnyja" not in argv:
        with open(JSON_SKRA, encoding="utf-8") as f:
            faerslur = json.load(f)
        print(f"Les {len(faerslur)} færslur úr {JSON_SKRA}")
    else:
        print("Sæki lýsigögn af kjarasamningar.is ...")
        faerslur = saekja_lysigogn(s)
        with open(JSON_SKRA, "w", encoding="utf-8") as f:
            json.dump(faerslur, f, ensure_ascii=False, indent=1)
        print(f"Vistaði {len(faerslur)} færslur í {JSON_SKRA}")

    # ---------------- OCR-texti ---------------- #
    if vil_texta:
        os.makedirs(TEXTI_MAPPA, exist_ok=True)
        n = 0
        for f_ in faerslur:
            t = f_.get("ocr_text") or ""
            if not t.strip():
                continue
            nafn = f"{f_['id']}_{hreinsa(f_.get('filename') or '')}"
            nafn = re.sub(r"\.(txt|pdf)$", "", nafn, flags=re.I) + ".txt"
            with open(os.path.join(TEXTI_MAPPA, nafn), "w", encoding="utf-8") as fh:
                fh.write(t)
            n += 1
        print(f"Vistaði OCR-texta fyrir {n} samninga í {TEXTI_MAPPA}")

    # ---------------- PDF ---------------- #
    if vil_pdf:
        os.makedirs(PDF_MAPPA, exist_ok=True)
        nytt = fyrir = mistokst = 0
        for i, f_ in enumerate(faerslur, 1):
            u = f_.get("pdf_url")
            if not u:
                continue
            nafn = f"{f_['id']}_{hreinsa(os.path.basename(u))}"
            if not nafn.lower().endswith(".pdf"):
                nafn += ".pdf"
            leid = os.path.join(PDF_MAPPA, nafn)
            if os.path.exists(leid) and os.path.getsize(leid) > 1000:
                fyrir += 1
                continue
            try:
                r = s.get(u, timeout=180)
                if r.status_code >= 400 or not r.content.startswith(b"%PDF"):
                    mistokst += 1
                    continue
                with open(leid, "wb") as fh:
                    fh.write(r.content)
                nytt += 1
            except Exception:
                mistokst += 1
            if i % 50 == 0:
                print(f"  {i}/{len(faerslur)} - ný {nytt}, fyrir {fyrir}, mistókst {mistokst}")
            time.sleep(0.15)
        print(f"PDF: {nytt} ný, {fyrir} voru til, {mistokst} mistókust")

    # ---------------- CSV yfirlit ---------------- #
    with open(CSV_SKRA, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_DALKAR, extrasaction="ignore")
        w.writeheader()
        for f_ in faerslur:
            rad = {k: f_.get(k) for k in CSV_DALKAR}
            u = f_.get("pdf_url") or ""
            nafn = f"{f_['id']}_{hreinsa(os.path.basename(u))}" if u else ""
            if nafn and not nafn.lower().endswith(".pdf"):
                nafn += ".pdf"
            rad["pdf_skra"] = nafn if nafn and os.path.exists(
                os.path.join(PDF_MAPPA, nafn)) else ""
            tnafn = re.sub(r"\.(txt|pdf)$", "",
                           f"{f_['id']}_{hreinsa(f_.get('filename') or '')}",
                           flags=re.I) + ".txt"
            rad["texta_skra"] = tnafn if os.path.exists(
                os.path.join(TEXTI_MAPPA, tnafn)) else ""
            rad["ocr_lengd"] = len(f_.get("ocr_text") or "")
            w.writerow(rad)
    print(f"Skrifaði yfirlit í {CSV_SKRA}")


if __name__ == "__main__":
    main(sys.argv[1:])
