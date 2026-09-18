# -*- coding: utf-8 -*-
"""Sækir PDF-skjöl af WordPress-vefjum í gegnum wp-json REST API.

Margir vefir stéttarfélaga keyra á WordPress. Skráasafnið þar er oft miklu
stærra en það sem sést í valmyndum vefjarins, og API-ið skilar öllu.

Notkun:
    python scripts/saekja_wp.py --kanna        # telja og sýna hvað fyndist
    python scripts/saekja_wp.py                # sækja allt sem síast í gegn
    python scripts/saekja_wp.py asi rafis      # aðeins valda vefi
    python scripts/saekja_wp.py --allt asi     # sleppa efnisorðasíu
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
from urllib.parse import urlparse, unquote

import requests

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMNINGAR = os.path.join(ROT, "samningar")
SKRA_CSV = os.path.join(SAMNINGAR, "_skra_wp.csv")

HAUSAR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

# host -> kóði/undirmappa
VEFIR = {
    "asi": ("www.asi.is", "Alþýðusamband Íslands"),
    "rafis": ("www.rafis.is", "Rafiðnaðarsamband Íslands"),
    "framsyn": ("framsyn.is", "Framsýn stéttarfélag"),
    "verkvest": ("www.verkvest.is", "Verkalýðsfélag Vestfirðinga"),
    "vm": ("vm.is", "VM - Félag vélstjóra og málmtæknimanna"),
    "grafia": ("grafia.is", "Grafía"),
    "samidn": ("samidn.is", "Samiðn"),
    "matvis": ("matvis.is", "MATVÍS"),
    "ssf": ("ssf.kreatives.is", "Samtök starfsmanna fjármálafyrirtækja"),
    "liv": ("liv.is", "Landssamband íslenzkra verzlunarmanna"),
    "efling": ("www.efling.is", "Efling stéttarfélag"),
    "ssi": ("www.ssi.is", "Sjómannasamband Íslands"),
    "sgs": ("sgs.is", "Starfsgreinasamband Íslands"),
    "vlfa": ("www.vlfa.is", "Verkalýðsfélag Akraness"),
}

# Efnisorð sem benda til þess að skjalið tengist kjarasamningi/launum
JAKVAETT = re.compile(
    r"kjarasamn|kjarasamm|samningur|samningar|samkomulag|bokun|bókun|"
    r"launatafl|launataxt|kauptaxt|kaupgjald|launatoflu|launatöflu|taxtar|"
    r"gerdardom|gerðardóm|midlunartillag|miðlunartillög|sattatillag|sáttatillög|"
    r"lifskjarasamning|lífskjarasamning|stodugleikasamning|stöðugleikasamning|"
    r"serkjarasamn|sérkjarasamn|vidauki|viðauki|launabreyting|launahaekkun|"
    r"launahækkun|kjarasamningur", re.I)

NEIKVAETT = re.compile(
    r"umsokn|umsókn|eydublad|eyðublað|arsreikning|ársreikning|fundargerd|"
    r"fundargerð|personuvernd|persónuvernd|orlofshus|orlofshús|styrkumsokn|"
    r"tjonstilkynning|auglysing|auglýsing|vinnustadaskirteini|namskeid|námskeið",
    re.I)


def hreinsa(s: str, hamark: int = 130) -> str:
    s = unquote(s or "")
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[\\/:*?\"<>|\r\n\t]", "-", s)
    s = re.sub(r"\s+", " ", s).strip(" .-_")
    return s[:hamark].rstrip(" .-_") or "skjal"


def listi_pdf(s: requests.Session, host: str) -> list[dict]:
    """Sækir öll PDF-viðhengi af WordPress-vef."""
    ut, sida = [], 1
    while True:
        u = f"https://{host}/wp-json/wp/v2/media"
        try:
            r = s.get(u, params={"per_page": 100, "page": sida,
                                 "mime_type": "application/pdf",
                                 "_fields": "id,date,title,slug,source_url,link,post"},
                      timeout=90)
        except Exception as e:
            print(f"    villa: {e}")
            break
        if r.status_code >= 400:
            break
        hluti = r.json()
        if not isinstance(hluti, list) or not hluti:
            break
        ut.extend(hluti)
        alls = int(r.headers.get("X-WP-TotalPages", 1))
        if sida >= alls:
            break
        sida += 1
        time.sleep(0.2)
    return ut


def vidkomandi(m: dict) -> bool:
    titill = (m.get("title") or {}).get("rendered", "") if isinstance(m.get("title"), dict) else ""
    strengur = unquote(f"{titill} {m.get('slug','')} {m.get('source_url','')}")
    if NEIKVAETT.search(strengur):
        return False
    return bool(JAKVAETT.search(strengur))


def main(argv):
    kanna = "--kanna" in argv
    allt = "--allt" in argv
    valdir = [a for a in argv if not a.startswith("--")]
    kodar = valdir or list(VEFIR)

    s = requests.Session()
    s.headers.update(HAUSAR)

    radir: list[dict] = []
    ser: set[str] = set()
    if os.path.exists(SKRA_CSV):
        with open(SKRA_CSV, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                radir.append(r)
                ser.add(r.get("sha256", ""))

    for kodi in kodar:
        if kodi not in VEFIR:
            print(f"[{kodi}] óþekktur vefur - sleppt")
            continue
        host, heiti = VEFIR[kodi]
        print(f"[{kodi}] {heiti} ({host})")
        skjol = listi_pdf(s, host)
        valid = skjol if allt else [m for m in skjol if vidkomandi(m)]
        print(f"  {len(skjol)} PDF alls, {len(valid)} eftir síun")
        if kanna:
            for m in valid[:40]:
                t = (m.get("title") or {}).get("rendered", "")
                print(f"     - {t[:70]} | {m.get('source_url','')[:100]}")
            continue

        mappa = os.path.join(SAMNINGAR, kodi)
        os.makedirs(mappa, exist_ok=True)
        nytt = 0
        for m in valid:
            u = m.get("source_url")
            if not u:
                continue
            nafn = hreinsa(os.path.basename(urlparse(u).path))
            if not nafn.lower().endswith(".pdf"):
                nafn += ".pdf"
            leid = os.path.join(mappa, nafn)
            if os.path.exists(leid):
                continue
            try:
                r = s.get(u, timeout=150)
                if r.status_code >= 400 or not r.content.startswith(b"%PDF"):
                    continue
                sha = hashlib.sha256(r.content).hexdigest()
                if sha in ser:
                    continue
                with open(leid, "wb") as f:
                    f.write(r.content)
                ser.add(sha)
                nytt += 1
                radir.append({
                    "kodi": kodi, "heimild": heiti,
                    "skra": f"{kodi}/{nafn}",
                    "titill": (m.get("title") or {}).get("rendered", ""),
                    "slod": u,
                    "dagsett": m.get("date", ""),
                    "staerd_bæti": len(r.content),
                    "sha256": sha,
                    "sott": date.today().isoformat(),
                })
            except Exception:
                continue
            time.sleep(0.15)
        print(f"  {nytt} ný skjöl sótt")

        with open(SKRA_CSV, "w", encoding="utf-8-sig", newline="") as f:
            dalkar = ["kodi", "heimild", "skra", "titill", "slod", "dagsett",
                      "staerd_bæti", "sha256", "sott"]
            w = csv.DictWriter(f, fieldnames=dalkar, extrasaction="ignore")
            w.writeheader()
            w.writerows(radir)

    print(f"\nSamtals í _skra_wp.csv: {len(radir)} skjöl")


if __name__ == "__main__":
    main(sys.argv[1:])
