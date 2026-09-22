# -*- coding: utf-8 -*-
"""Sækir samþykktar leiðréttingar úr GitHub Issues og festir þær í gögnin.

Opna eyðuskráningin (docs/eydur.html) sendir hverja skráningu sem issue með
merkinu "leiðrétting". Yfirferðin fer fram á GitHub:

  - samþykkja: bæta merkinu "samþykkt" við issue-ið
  - hafna:     bæta merkinu "hafnað" við og loka því

Þetta forrit sækir issue sem bera "samþykkt" en ekki "fest", les
eyðublaðsreitina, sannreynir gildin og festir þau með sömu leið og
vefskráningarnar (scripts/nota_vefskraningar.py). Að því loknu fær hvert
issue merkið "fest", athugasemd og er lokað.

Notar gh (GitHub CLI) með innskráningu eiganda geymslunnar.

Notkun:
    python scripts/saekja_leidrettingar.py            # festir og lokar issue
    python scripts/saekja_leidrettingar.py --kanna    # sýnir aðeins hvað yrði gert
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nota_vefskraningar  # noqa: E402

REPO = "kristinnthor/kjarasamningar"

# Fyrirsagnir í .github/ISSUE_TEMPLATE/leidretting.yml -> reitir
REITIR = {"Félag": "felag", "Auðkenni félags": "audkenni", "Samningur": "samningur",
          "Eyða": "eyda", "Tegund": "tegund", "Gildistaka": "dagsetning",
          "Prósenta": "prosenta", "Krónur": "kronur", "Á við": "a_vid",
          "Heimild": "heimild", "Athugasemd": "athugasemd"}
GILD_AVID = {"almenn laun", "kauptaxtar", "launatafla", "lágmarkstekjur",
             "byrjunarlaun", "óskilgreint"}


def gh(*args) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def lesa_reiti(body: str) -> dict:
    reitir = {}
    for hluti in re.split(r"^###\s+", body or "", flags=re.M)[1:]:
        fyrirsogn, _, gildi = hluti.partition("\n")
        lykill = REITIR.get(fyrirsogn.strip())
        if lykill:
            gildi = gildi.strip()
            reitir[lykill] = "" if gildi == "_No response_" else gildi
    return reitir


def tala(s):
    s = (s or "").strip().replace("%", "").replace(" ", "")
    if not s:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return "villa"


def kronutala(s):
    s = re.sub(r"(kr\.?|\s|\.)", "", (s or "").strip(), flags=re.I)
    if not s:
        return None
    return int(s) if s.isdigit() else "villa"


def sannreyna(numer, r):
    """Skilar (tillaga, villa). Tillagan er á formi nota_vefskraningar."""
    dagar = re.findall(r"\d{4}-\d{2}-\d{2}", r.get("eyda", ""))
    if len(dagar) < 2:
        return None, "eyðan er ekki á forminu áááá-mm-dd til áááá-mm-dd"
    fra, til = dagar[:2]
    grunnur = {"id": f"gh-{numer}", "felag": r.get("felag", "").strip(),
               "felag_audkenni": r.get("audkenni", "").strip(),
               "eyda": f"{fra}_{til}", "heimild": r.get("heimild", "").strip(),
               "athugasemd": (r.get("athugasemd", "") + f" (GitHub #{numer})").strip()}
    if not grunnur["felag"]:
        return None, "félag vantar"
    if r.get("tegund", "").startswith("Engin"):
        return {**grunnur, "tegund": "engin"}, None
    d = r.get("dagsetning", "").strip()
    try:
        date.fromisoformat(d)
    except ValueError:
        return None, f"gildistakan '{d}' er ekki gild dagsetning"
    if not (fra <= d < til):
        return None, f"gildistakan {d} er utan eyðunnar {fra} til {til}"
    pros, kr = tala(r.get("prosenta")), kronutala(r.get("kronur"))
    if "villa" in (pros, kr):
        return None, "ólæsileg prósenta eða krónutala"
    if pros is None and kr is None:
        return None, "hvorki prósenta né krónutala"
    if pros is not None and not (0 < pros <= 25):
        return None, f"prósentan {pros} er utan marka"
    if kr is not None and not (500 <= kr <= 200_000):
        return None, f"krónutalan {kr} er utan marka"
    a_vid = r.get("a_vid", "").strip() or "óskilgreint"
    if a_vid not in GILD_AVID:
        return None, f"'{a_vid}' er óþekkt viðmið"
    return {**grunnur, "tegund": "haekkun", "dagsetning": d, "prosenta": pros,
            "kronur": kr, "a_vid": a_vid}, None


def main(argv):
    kanna = "--kanna" in argv
    issue = json.loads(gh("issue", "list", "--repo", REPO, "--state", "all",
                          "--label", "leiðrétting", "--label", "samþykkt",
                          "--limit", "500", "--json", "number,title,body,labels,url"))
    obirt = [i for i in issue if "fest" not in {m["name"] for m in i["labels"]}]
    print(f"Samþykktar skráningar: {len(issue)}, þar af ófestar: {len(obirt)}")

    tillogur, villur = [], []
    for i in obirt:
        t, villa = sannreyna(i["number"], lesa_reiti(i["body"]))
        if villa:
            villur.append((i, villa))
        else:
            tillogur.append((i, t))
    for i, villa in villur:
        print(f"   #{i['number']}: {villa} - sleppt ({i['url']})")
    if not tillogur:
        print("Ekkert til að festa.")
        return 0

    # Sama snið og vefskráningarnar, svo festingin fari sömu leið
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump({"tillogur": [t for _, t in tillogur],
                   "mat": {t["id"]: "samthykkt" for _, t in tillogur}},
                  f, ensure_ascii=False)
        leid = f.name
    try:
        nidurstada = nota_vefskraningar.main([leid] + (["--kanna"] if kanna else []))
    finally:
        os.unlink(leid)
    if nidurstada or kanna:
        return nidurstada

    for i, _ in tillogur:
        gh("issue", "edit", str(i["number"]), "--repo", REPO, "--add-label", "fest")
        gh("issue", "close", str(i["number"]), "--repo", REPO, "--comment",
           "Takk! Leiðréttingin hefur verið fest í gagnasettið og birtist í "
           "API-inu og á síðunum við næstu uppfærslu.")
    print(f"\n{len(tillogur)} issue merkt 'fest' og lokað.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
