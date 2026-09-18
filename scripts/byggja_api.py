# -*- coding: utf-8 -*-
"""Byggir static JSON-API úr gagnasettinu, tilbúið fyrir GitHub Pages.

Aðferðin er vísvitandi einföld: engin bakendaþjónusta, heldur fastar
JSON-skrár sem CDN afgreiðir. Það kostar ekkert, þolir álag, er útgáfustýrt
með gögnunum sjálfum og GitHub Pages sendir CORS-hausa sjálfkrafa svo hægt sé
að sækja gögnin beint úr vafra.

Notkun:
    python scripts/byggja_api.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
API = os.path.join(ROT, "docs", "api", "v1")

UTGAFA = "1.0"
GRUNNSLOD = "https://kristinnthor.github.io/kjarasamningar/api/v1"

STAFIR = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ý": "y",
          "þ": "th", "æ": "ae", "ö": "o", "ð": "d"}


def slodarheiti(s: str) -> str:
    """Breytir félagsheiti í stutt, slóðarhæft auðkenni."""
    s = (s or "").lower()
    s = "".join(STAFIR.get(c, c) for c in s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "ohekkt"


def lesa(skra):
    leid = os.path.join(GOGN, skra)
    if not os.path.exists(leid):
        return []
    with open(leid, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def tolur(r, heil=(), fleyti=()):
    """Skilar afriti þar sem tölulegir dálkar eru tölur en ekki strengir."""
    ut = {}
    for k, v in r.items():
        if v == "":
            ut[k] = None
        elif k in heil:
            ut[k] = int(v)
        elif k in fleyti:
            ut[k] = float(v)
        else:
            ut[k] = v
    return ut


def skrifa(leid, gogn):
    os.makedirs(os.path.dirname(leid), exist_ok=True)
    with open(leid, "w", encoding="utf-8") as f:
        json.dump(gogn, f, ensure_ascii=False, separators=(",", ":"))


FYRIRVARAR = [
    "Vísitalan leggur saman þær hækkanir sem tókst að finna í samningum. "
    "Hún er ekki launavísitala og er aðeins marktæk fyrir félög þar sem "
    "reiturinn heilleiki er 'samfelld'.",
    "Krónutöluhækkanir er ekki hægt að umbreyta í hlutfall án þess að vita "
    "launastigið. Þar stendur vísitalan í stað og línan er merkt.",
    "Launavísitala Hagstofunnar skiptist eftir markaði en ekki stéttarfélagi, "
    "og mælir raunverulega launaþróun með launaskriði - ekki umsamdar hækkanir.",
    "Gögnin eru unnin vélrænt úr OCR-texta. Hver hækkun ber tilvitnun í "
    "frumtextann svo hægt sé að sannreyna hana.",
]


def main():
    felog = lesa("felog.csv")
    rod = lesa("launathroun_eftir_felagi.csv")
    # Sameinaða skráin er notuð þegar hún er til: hún ber bæði færslur með
    # staðfest lýsigögn og þær sem raktar voru úr vefskjölum.
    haekkanir = lesa("haekkanir_sameinad.csv") or lesa("haekkanir.csv")

    if not felog:
        print("gogn/felog.csv fannst ekki - keyrðu scripts/launathroun.py fyrst")
        return

    HEIL = ("fjoldi_haekkana", "kronur", "heimildir", "olik_gildi",
            "bil_manudir", "mesta_bil_manudir")
    FLEYTI = ("prosenta", "visitala")

    # ---- auðkenni félaga ---- #
    slod_eftir_lykli = {}
    notud = set()
    for f in felog:
        grunnur = slodarheiti(f["felag"])
        s, i = grunnur, 2
        while s in notud:
            s, i = f"{grunnur}-{i}", i + 1
        notud.add(s)
        slod_eftir_lykli[f["felag_lykill"]] = s

    # ---- tímaröð á hvert félag ---- #
    eftir_felagi = defaultdict(list)
    for r in rod:
        eftir_felagi[r["felag_lykill"]].append(tolur(r, HEIL, FLEYTI))

    for f in felog:
        lykill = f["felag_lykill"]
        s = slod_eftir_lykli[lykill]
        linur = sorted(eftir_felagi[lykill], key=lambda r: r["dagsetning"])
        skrifa(os.path.join(API, "felog", f"{s}.json"), {
            "audkenni": s,
            "felag": f["felag"],
            "felag_id": f["felag_id"] or None,
            "markadur": f["markadur"] or None,
            "heildarsamtok": f["heildarsamtok"] or None,
            "fyrsta": f["fyrsta"],
            "sidasta": f["sidasta"],
            "fjoldi_haekkana": int(f["fjoldi_haekkana"]),
            "heilleiki": f["heilleiki"],
            "mesta_bil_manudir": int(f["mesta_bil_manudir"]) if f["mesta_bil_manudir"] else None,
            "haekkanir": linur,
        })

    # ---- listi félaga ---- #
    skrifa(os.path.join(API, "felog.json"), {
        "fjoldi": len(felog),
        "felog": [{
            "audkenni": slod_eftir_lykli[f["felag_lykill"]],
            "felag": f["felag"],
            "markadur": f["markadur"] or None,
            "heildarsamtok": f["heildarsamtok"] or None,
            "fyrsta": f["fyrsta"], "sidasta": f["sidasta"],
            "fjoldi_haekkana": int(f["fjoldi_haekkana"]),
            "heilleiki": f["heilleiki"],
            "slod": f"{GRUNNSLOD}/felog/{slod_eftir_lykli[f['felag_lykill']]}.json",
        } for f in felog],
    })

    # ---- allar hækkanir, og eftir ári ---- #
    allar = [tolur(r, ("kronur",), ("prosenta",)) for r in haekkanir]
    skrifa(os.path.join(API, "haekkanir.json"),
           {"fjoldi": len(allar), "haekkanir": allar})

    eftir_ari = defaultdict(list)
    for r in allar:
        eftir_ari[r["gildir_fra"][:4]].append(r)
    for ar, linur in eftir_ari.items():
        skrifa(os.path.join(API, "haekkanir", f"{ar}.json"),
               {"ar": ar, "fjoldi": len(linur), "haekkanir": linur})

    # ---- launavísitala ---- #
    visitolur = {}
    for skra in sorted(os.listdir(GOGN)):
        if skra.startswith("launavisitala") and skra.endswith(".csv"):
            heiti = skra[:-4]
            linur = lesa(skra)
            skrifa(os.path.join(API, "launavisitala", f"{heiti}.json"),
                   {"heiti": heiti, "fjoldi": len(linur), "gildi": linur})
            visitolur[heiti] = f"{GRUNNSLOD}/launavisitala/{heiti}.json"

    # ---- rót ---- #
    skrifa(os.path.join(API, "index.json"), {
        "heiti": "Kjarasamningar - umsamdar launahækkanir á Íslandi",
        "utgafa": UTGAFA,
        "uppfaert": date.today().isoformat(),
        "grunnslod": GRUNNSLOD,
        "leyfi": "Frumgögn eru opinber gögn útgefenda sinna; úrvinnslan er frjáls til nota.",
        "heimildir": [
            "Ríkissáttasemjari - kjarasamningar.is",
            "Hagstofa Íslands - PX-Web API",
            "Vefir stéttarfélaga og samtaka atvinnurekenda",
        ],
        "fyrirvarar": FYRIRVARAR,
        "endapunktar": {
            "felog": f"{GRUNNSLOD}/felog.json",
            "felag": f"{GRUNNSLOD}/felog/{{audkenni}}.json",
            "haekkanir": f"{GRUNNSLOD}/haekkanir.json",
            "haekkanir_eftir_ari": f"{GRUNNSLOD}/haekkanir/{{ar}}.json",
            "launavisitala": visitolur,
        },
        "tolur": {
            "felog": len(felog),
            "haekkanir": len(allar),
            "maelipunktar": len(rod),
            "ar": [min(eftir_ari), max(eftir_ari)] if eftir_ari else None,
        },
    })

    n = sum(len(f) for _, _, f in os.walk(API))
    staerd = sum(os.path.getsize(os.path.join(m, x))
                 for m, _, fs in os.walk(API) for x in fs)
    print(f"Skrifaði {n} JSON-skrár ({staerd/2**20:.1f} MB) í {API}")
    print(f"Félög: {len(felog)}, hækkanir: {len(allar)}, mælipunktar: {len(rod)}")


if __name__ == "__main__":
    main()
