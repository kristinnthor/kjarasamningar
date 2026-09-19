# -*- coding: utf-8 -*-
"""Dregur umsamdar launahækkanir út úr texta kjarasamninga.

Skilar einni línu á hverja umsamda hækkun: hvenær hún tók gildi, hversu mikil
hún var (prósenta og/eða krónutala), við hvað hún miðast og hvaðan hún er
komin - ásamt beinni tilvitnun svo hægt sé að sannreyna hverja færslu.

Notkun:
    python scripts/utdrattur.py                # keyrir á heildarskránni
    python scripts/utdrattur.py --daemi 25     # sýnir dæmi í stað þess að vista
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LYSIGOGN = os.path.join(ROT, "samningar", "rikissattasemjari", "lysigogn.json")
GOGN = os.path.join(ROT, "gogn")

# --------------------------------------------------------------------------- #
# Dagsetningar                                                                 #
# --------------------------------------------------------------------------- #

MANUDIR = {
    "janúar": 1, "januar": 1, "jan": 1,
    "febrúar": 2, "februar": 2, "feb": 2,
    "mars": 3, "mar": 3,
    "apríl": 4, "april": 4, "apr": 4,
    "maí": 5, "mai": 5,
    "júní": 6, "juni": 6, "jún": 6, "jun": 6,
    "júlí": 7, "juli": 7, "júl": 7, "jul": 7,
    "ágúst": 8, "agust": 8, "ág": 8, "ag": 8,
    "september": 9, "sept": 9, "sep": 9,
    "október": 10, "oktober": 10, "okt": 10,
    "nóvember": 11, "november": 11, "nóv": 11, "nov": 11,
    "desember": 12, "des": 12,
}
MAN_RE = "|".join(sorted((re.escape(m) for m in MANUDIR), key=len, reverse=True))

# "1. júní 1988", "1. des. 1977", "1. janúar"
DAGS_RE = rf"(\d{{1,2}})\s*\.\s*(?:dag[i]?\s+)?({MAN_RE})\s*\.?\s*(\d{{4}})?"

# Neikvæða framsýnin kemur í veg fyrir að aftasti hluti lengri tölu sé lesinn
# sem sjálfstæð prósenta: án hennar varð "0,615%" að "15%".
PROSENTA_RE = r"(?<![\d.,])(\d{1,2}(?:[.,]\d{1,2})?)\s*%"
KRONUR_RE = (r"(?:kr\.?\s*(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d{4,7})"
             r"|(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d{4,7})\s*(?:kr\.?|krón\w*))")

# --------------------------------------------------------------------------- #
# Samhengisorð                                                                 #
# --------------------------------------------------------------------------- #

# Verður að vera launatengt til að teljast með
LAUNAORD = re.compile(
    r"\blaun|\bkaup|taxt|mánaðarlaun|grunnlaun|byrjunarlaun|launaflokk|"
    r"launatafl|launali[ðd]|kjarataxt|tímakaup|dagvinn", re.I)

# Greinileg merki um að hækkunin eigi ekki við grunnlaun. Tvennt er hér:
# annars vegar greiðslur sem eru ekki laun, hins vegar álags- og
# hlutfallsákvæði þar sem prósentan skilgreinir taxta en er ekki hækkun
# (t.d. "vaktaálag skal vera 33,33%").
UTILOKAD = re.compile(
    r"iðgjald|lífeyri|mótframlag|séreign|sjúkrasjó[ðd]|starfsmennta|"
    r"orlofsheimil|félagsgjald|tryggingagjald|vaxta|verðbólg|"
    r"framlag í|sjóðfélag|endurmenntun|vísitala neysluverðs|"
    r"desemberuppbót|orlofsuppbót|persónuuppbót|"
    r"eingreiðsl|uppgjörsgreiðsl|innáborgun|"
    r"vaktaálag|stórhelgi|álagsgreiðsl|ferðapening|dagpening|vátrygg|"
    r"bifreiðastyrk|fatapening|akstursgjald|námskeiðaálag|"
    r"vátryggingarfjárhæð|slysatrygg|starfsaldursálag", re.I)

# Orðalag sem lýsir launastigi fremur en hækkun: "breytist í 467.000 kr.",
# "skal vera 15% hærri". Slíkar fjárhæðir eiga heima í launatöflunum.
LAUNASTIG = re.compile(
    r"í\s*(?:kr\.?\s*)?\d|skal vera|skulu vera|verða\s*(?:kr\.?\s*)?\d|"
    r"reiknast|nemur\s*\d|% hærri|hærri en", re.I)

# Hækkun verður að vera orðuð sem breyting. Orðalag á borð við "mánaðarlaun
# skulu vera kr. 245.000" lýsir launastigi og á heima í launatöflunum, ekki hér.
HAEKKUNARORD = re.compile(
    r"hækk|lækk|breyt(?:ast|ist|ing)|taka? hlutfallsh|"
    r"kemur til framkvæmda|áfangahækkun", re.I)

# Hvað hækkunin á við
AVID = [
    ("kauptaxtar", re.compile(r"kauptaxt|launataxt|taxtakaup|taxtalaun|kauptöxt", re.I)),
    ("launatafla", re.compile(r"launatafl|launaflokk|launaþrep|launatöfl", re.I)),
    ("lágmarkstekjur", re.compile(r"lágmarkstekj|lágmarkslaun|tekjutrygg", re.I)),
    ("byrjunarlaun", re.compile(r"byrjunarlaun|upphafslaun", re.I)),
    ("almenn laun", re.compile(r"öll laun|almenn\w* (?:launa)?hækk|mánaðarlaun|"
                               r"grunnlaun|laun hækka|hækka laun|dagvinnulaun", re.I)),
]

# Hvernig krónutalan tengist prósentunni
LAGMARK = re.compile(r"að lágmarki|þó (?:eigi|ekki) (?:um )?lægri|hi[ðd] minnsta|"
                     r"lágmarkshækkun|krónutöluhækkun að lágmarki", re.I)
EDA = re.compile(r"\beða\b", re.I)

# Dagsetningar sem eru skilyrði eða viðmiðunarmörk fremur en gildistökudagur
# hækkunar, t.d. "starfsmenn sem hófu störf fyrir 1. febrúar 2014".
SKILYRDI = re.compile(
    r"(?:hófu|hóf|hafið|hefja|hefur hafið)\s+(?:þá\s+)?störf[^.]{0,30}$|"
    r"ráðni[rn][^.]{0,25}$|starfað[^.]{0,25}$|"
    r"til og með\s*$|gildir til\s*$|rann út\s*$", re.I)


def bua_til_dags(dagur: int, man: int, ar: int):
    try:
        return date(ar, man, dagur)
    except ValueError:
        return None


class Argreining:
    """Metur og leiðréttir ártal hækkunar út frá gildistíma samningsins."""

    def __init__(self, fra: str | None, til: str | None):
        self.fra = self._les(fra)
        self.til = self._les(til)

    @staticmethod
    def _les(s):
        if not s:
            return None
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None

    def gluggi(self):
        """Tímabil sem hækkun getur með réttu fallið innan."""
        f = (self.fra - timedelta(days=400)) if self.fra else None
        t = (self.til + timedelta(days=400)) if self.til else None
        if f and not t:
            t = date(f.year + 6, 12, 31)
        if t and not f:
            f = date(t.year - 8, 1, 1)
        return f, t

    def leysa(self, dagur: int, man: int, ar: int | None):
        """Skilar (dagsetning, stada) þar sem stada lýsir vissunni um ártalið."""
        f, t = self.gluggi()
        if ar:
            d = bua_til_dags(dagur, man, ar)
            if not d:
                return None, "ógilt"
            if not f or not t or f <= d <= t:
                return d, "úr texta"
            # Ártal utan gildistíma - líklega OCR-villa. Reyna eins stafs lagfæringu.
            tillogur = []
            for kandidat in range(f.year, t.year + 1):
                if self._einn_stafur_fra(ar, kandidat):
                    d2 = bua_til_dags(dagur, man, kandidat)
                    if d2 and f <= d2 <= t:
                        tillogur.append(d2)
            if len(tillogur) == 1:
                return tillogur[0], "leiðrétt"
            return d, "grunsamlegt"
        # Ekkert ártal í textanum - álykta af gildistíma
        if not f or not t:
            return None, "ekkert ártal"
        mogulegar = [bua_til_dags(dagur, man, a) for a in range(f.year, t.year + 1)]
        mogulegar = [d for d in mogulegar if d and f <= d <= t]
        if len(mogulegar) == 1:
            return mogulegar[0], "ályktað"
        if mogulegar:
            return mogulegar[0], "ályktað (óvisst)"
        return None, "ekkert ártal"

    @staticmethod
    def _einn_stafur_fra(a: int, b: int) -> bool:
        sa, sb = f"{a:04d}", f"{b:04d}"
        return sum(1 for x, y in zip(sa, sb) if x != y) == 1


def prosentutala(s: str | None):
    """Les prósentu. Punktur og komma eru bæði tugabrotsmerki hér - prósentur
    í kjarasamningum eru aldrei svo háar að þúsundaskil komi við sögu."""
    if not s:
        return None
    return float(s.replace(",", "."))


def kronutala(s: str | None):
    if not s:
        return None
    return int(s.replace(".", ""))


def flokka_avid(samhengi: str) -> str:
    for heiti, mynstur in AVID:
        if mynstur.search(samhengi):
            return heiti
    return "óskilgreint"


def flokka_tegund(pros, kr, samhengi) -> str:
    if pros is not None and kr is not None:
        if EDA.search(samhengi):
            return "prósenta eða krónutala"
        if LAGMARK.search(samhengi):
            return "prósenta með krónutölulágmarki"
        return "prósenta og krónutala"
    if pros is not None:
        return "prósenta"
    return "krónutala"


# --------------------------------------------------------------------------- #
# Útdráttur                                                                    #
# --------------------------------------------------------------------------- #

def klippa(texti: str, byrjun: int, endir: int, fyrir=200, eftir=120) -> str:
    """Skilar samhengi kringum fundna hækkun, til sannreyningar."""
    b = max(0, byrjun - fyrir)
    e = min(len(texti), endir + eftir)
    return " ".join(texti[b:e].split())


DAGS_ALLT = re.compile(DAGS_RE, re.I)
PROSENTA_ALLT = re.compile(PROSENTA_RE)
KRONUR_ALLT = re.compile(KRONUR_RE, re.I)

def _gildi_i_glugga(gluggi: str):
    """Skilar (prósenta, krónutala) úr afmörkuðum texta."""
    pm = PROSENTA_ALLT.search(gluggi)
    km = KRONUR_ALLT.search(gluggi)
    pros = prosentutala(pm.group(1)) if pm else None
    kr = kronutala(km.group(1) or km.group(2)) if km else None
    return pros, kr


def utdrattur_ur_texta(texti: str, argr: Argreining):
    """Dregur hækkanir út með dagsetningar sem akkeri.

    Hver dagsetning fær glugga sem nær fram að næstu dagsetningu (eða 90 stafi,
    hvort sem kemur á undan). Þannig lekur gildi ekki milli liða í upptalningu
    á borð við "1. apríl 2019 17.000 kr. 1. apríl 2020 18.000 kr.", og prósenta
    og krónutala sem eiga saman - "3,50% eða 23.750 kr." - lenda í sömu færslu.
    """
    fundid: dict[tuple, dict] = {}
    dagsetningar = list(DAGS_ALLT.finditer(texti))

    for i, m in enumerate(dagsetningar):
        man_n = MANUDIR.get(m.group(2).lower().rstrip("."))
        if not man_n:
            continue

        naesta = dagsetningar[i + 1].start() if i + 1 < len(dagsetningar) else len(texti)
        fyrri = dagsetningar[i - 1].end() if i > 0 else 0

        # Dagsetningar sem eru skilyrði eiga ekki að verða gildistökudagur
        undanfari = " ".join(texti[max(0, m.start() - 60):m.start()].split())
        if SKILYRDI.search(undanfari):
            continue

        # Fyrst er leitað fram fyrir dagsetninguna, sem er algengasta orðaröðin
        endir = min(m.end() + 90, naesta)
        pros, kr = _gildi_i_glugga(texti[m.end():endir])
        span = (m.start(), endir)

        # Annars aftur fyrir hana: "hækka um 5% þann 1. febrúar 1977"
        if pros is None and kr is None:
            byrjun = max(fyrri, m.start() - 90)
            pros, kr = _gildi_i_glugga(texti[byrjun:m.start()])
            span = (byrjun, m.end())

        if pros is None and kr is None:
            continue

        samhengi = klippa(texti, span[0], span[1])
        if UTILOKAD.search(samhengi) or not LAUNAORD.search(samhengi):
            continue
        if not HAEKKUNARORD.search(samhengi):
            continue
        # Þrengra samhengi til að greina launastig frá hækkun
        naerumhverfi = " ".join(texti[span[0]:span[1] + 40].split())
        if LAUNASTIG.search(naerumhverfi):
            continue

        d, stada = argr.leysa(int(m.group(1)), man_n,
                              int(m.group(3)) if m.group(3) else None)
        if d is None:
            continue
        if pros is not None and not (0 < pros <= 15):
            pros = None
        if kr is not None and not (500 <= kr <= 100_000):
            kr = None
        if pros is None and kr is None:
            continue

        lykill = (d.isoformat(), pros, kr)
        if lykill in fundid:
            continue
        fundid[lykill] = {
            "gildir_fra": d.isoformat(),
            "tegund": flokka_tegund(pros, kr, samhengi),
            "prosenta": pros,
            "kronur": kr,
            "a_vid": flokka_avid(samhengi),
            "artal_stada": stada,
            "tilvitnun": samhengi[:400],
        }

    return list(fundid.values())


# --------------------------------------------------------------------------- #

DALKAR = [
    "samningur_id", "contract_id", "felag_id", "felag", "atvinnurekandi",
    "markadur", "heildarsamtok", "samningur_fra", "samningur_til",
    "gildir_fra", "tegund", "prosenta", "kronur", "a_vid",
    "artal_stada", "heimild", "skjal", "tilvitnun",
]


def main(argv):
    syna = "--daemi" in argv
    fj = int(argv[argv.index("--daemi") + 1]) if syna else 0

    gogn = json.load(open(LYSIGOGN, encoding="utf-8"))
    radir = []
    med_nidurstodu = 0

    for x in gogn:
        texti = x.get("ocr_text") or ""
        if not texti.strip():
            continue
        argr = Argreining(x.get("fra"), x.get("til"))
        haekkanir = utdrattur_ur_texta(texti, argr)
        if haekkanir:
            med_nidurstodu += 1
        for h in haekkanir:
            radir.append({
                "samningur_id": x.get("id"),
                "contract_id": x.get("contract_id"),
                "felag_id": x.get("launthegi_felag_id"),
                "felag": x.get("launthegi_canonical") or x.get("launthegi"),
                "atvinnurekandi": x.get("atvinnurekandi"),
                "markadur": x.get("markadsflokk"),
                "heildarsamtok": x.get("heildarsamtok"),
                "samningur_fra": (x.get("fra") or "")[:10],
                "samningur_til": (x.get("til") or "")[:10],
                "heimild": "rikissattasemjari",
                "skjal": x.get("filename"),
                **h,
            })

    radir.sort(key=lambda r: (r["gildir_fra"], str(r["felag"])))

    if syna:
        for r in radir[:fj]:
            print(f"\n{r['gildir_fra']}  {r['tegund']}  "
                  f"{r['prosenta'] if r['prosenta'] is not None else '-'}%  "
                  f"{r['kronur'] if r['kronur'] is not None else '-'} kr  "
                  f"[{r['a_vid']}] ártal: {r['artal_stada']}")
            print(f"   {str(r['felag'])[:70]} <-> {str(r['atvinnurekandi'])[:40]}")
            print(f"   ...{r['tilvitnun'][:220]}...")
        return

    os.makedirs(GOGN, exist_ok=True)
    ut = os.path.join(GOGN, "haekkanir.csv")
    with open(ut, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DALKAR, extrasaction="ignore")
        w.writeheader()
        w.writerows(radir)

    print(f"Samningar með texta:        {sum(1 for x in gogn if (x.get('ocr_text') or '').strip())}")
    print(f"Þar sem hækkun fannst:      {med_nidurstodu}")
    print(f"Hækkanir alls:              {len(radir)}")
    print(f"Skrifað í {ut}")


if __name__ == "__main__":
    main(sys.argv[1:])
