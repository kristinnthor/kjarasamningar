# -*- coding: utf-8 -*-
"""Býr til yfirferðarskrá yfir eyður í tímaröðum félaga.

Eyða þýðir að langt líður milli skráðra hækkana. Tvennt getur valdið því:
hækkun vantar í gögnin, eða félagið samdi einfaldlega ekki á tímabilinu.
Vélin getur ekki greint þar á milli - það þarf mannsauga.

Skráin er því gerð til að fara yfir handvirkt. Hver lína er ein eyða, með
samhenginu sem þarf til að meta hana: hækkunin á undan, hækkunin á eftir, og
hvað önnur félög sömdu um á sama tímabili.

Notkun:
    python scripts/yfirferd.py
    python scripts/yfirferd.py --fra 2025    # félög með gögn frá og með 2025
"""
from __future__ import annotations

import collections
import csv
import os
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
YFIRFERD = os.path.join(ROT, "yfirferd")

# Bil sem telst eyða. Kjarasamningar eru sjaldan lengri en þrjú ár og bera
# oftast árlega áfanga, svo lengra bil en 18 mánuðir kallar á skoðun.
EYDUMORK = 18


def lesa(skra):
    with open(os.path.join(GOGN, skra), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def manudir(a: str, b: str) -> int:
    return ((int(b[:4]) - int(a[:4])) * 12) + (int(b[5:7]) - int(a[5:7]))


def lysa(r) -> str:
    """Stutt lýsing á hækkun, til samanburðar í yfirferð."""
    hlutar = []
    if r.get("prosenta"):
        hlutar.append(f"{float(r['prosenta']):.2f}%".replace(".", ","))
    if r.get("kronur"):
        hlutar.append(f"{int(r['kronur']):,} kr".replace(",", "."))
    return " / ".join(hlutar) or "-"


def algengt_a_bili(allar_radir, fra: str, til: str, sleppa_lykli: str,
                   hamark: int = 4) -> str:
    """Hvað sömdu önnur félög um á þessu tímabili?

    Íslenskir kjarasamningar fylgjast að og oftast er sama prósenta í gildi
    hjá mörgum félögum sama dag. Sjáist að tugir félaga hækkuðu um 3,50%
    þann 1. janúar 2025 en ekkert er skráð hjá þessu félagi er líklegt að
    hækkun vanti - en ekki víst, og því er þetta vísbending en ekki niðurstaða.
    """
    teljari = collections.Counter()
    for r in allar_radir:
        if r["felag_lykill"] == sleppa_lykli:
            continue
        if not (fra < r["dagsetning"] <= til) or not r["prosenta"]:
            continue
        teljari[(r["dagsetning"], float(r["prosenta"]))] += 1
    bestu = [f"{d} {p:.2f}%".replace(".", ",") + f" ({n} félög)"
             for (d, p), n in teljari.most_common(hamark) if n >= 3]
    return "; ".join(bestu)


DALKAR = [
    # Til útfyllingar
    "stada", "dagsetning", "prosenta", "kronur", "a_vid", "heimild", "athugasemd",
    # Samhengi, forútfyllt
    "felag", "felag_audkenni", "eyda_fra", "eyda_til", "manudir",
    "haekkun_a_undan", "haekkun_a_eftir", "algengt_hja_odrum",
    "heilleiki", "fjoldi_haekkana", "timabil_felags",
]


def main(argv):
    fra_ar = "2025"
    if "--fra" in argv:
        fra_ar = argv[argv.index("--fra") + 1]

    felog = lesa("felog.csv")
    rod = lesa("launathroun_eftir_felagi.csv")

    # Auðkenni félaga eins og API-ið notar
    audkenni = {}
    try:
        import json
        with open(os.path.join(ROT, "docs", "api", "v1", "felog.json"),
                  encoding="utf-8") as f:
            for x in json.load(f)["felog"]:
                audkenni[x["felag"]] = x["audkenni"]
    except Exception:
        pass

    eftir_felagi = collections.defaultdict(list)
    for r in rod:
        eftir_felagi[r["felag_lykill"]].append(r)

    valin = [f for f in felog
             if f["sidasta"] >= f"{fra_ar}-01-01"
             and f["heilleiki"] != "samfelld"]
    valin.sort(key=lambda f: -int(f["fjoldi_haekkana"]))

    linur = []
    for f in valin:
        eigin = sorted(eftir_felagi[f["felag_lykill"]],
                       key=lambda r: r["dagsetning"])
        for i in range(1, len(eigin)):
            fyrri, thessi = eigin[i - 1], eigin[i]
            bil = manudir(fyrri["dagsetning"], thessi["dagsetning"])
            if bil <= EYDUMORK:
                continue
            linur.append({
                "stada": "", "dagsetning": "", "prosenta": "", "kronur": "",
                "a_vid": "", "heimild": "", "athugasemd": "",
                "felag": f["felag"],
                "felag_audkenni": audkenni.get(f["felag"], ""),
                "eyda_fra": fyrri["dagsetning"],
                "eyda_til": thessi["dagsetning"],
                "manudir": bil,
                "haekkun_a_undan": lysa(fyrri),
                "haekkun_a_eftir": lysa(thessi),
                "algengt_hja_odrum": algengt_a_bili(
                    rod, fyrri["dagsetning"], thessi["dagsetning"],
                    f["felag_lykill"]),
                "heilleiki": f["heilleiki"],
                "fjoldi_haekkana": f["fjoldi_haekkana"],
                "timabil_felags": f"{f['fyrsta']} – {f['sidasta']}",
            })

    os.makedirs(YFIRFERD, exist_ok=True)
    ut = os.path.join(YFIRFERD, "eydur.csv")
    with open(ut, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DALKAR)
        w.writeheader()
        w.writerows(linur)

    # Læsilegt yfirlit til að skanna hratt
    md = [f"# Eyður til yfirferðar\n",
          f"Félög með gögn frá og með {fra_ar} þar sem röðin er ekki samfelld.\n",
          f"**{len(valin)} félög, {len(linur)} eyður.** "
          f"Eyða telst bil lengra en {EYDUMORK} mánuðir.\n"]
    eftir_heiti = collections.defaultdict(list)
    for l in linur:
        eftir_heiti[l["felag"]].append(l)
    for heiti in sorted(eftir_heiti, key=lambda h: -len(eftir_heiti[h])):
        hop = eftir_heiti[heiti]
        md.append(f"\n## {heiti}\n")
        md.append(f"{hop[0]['fjoldi_haekkana']} hækkanir, "
                  f"{hop[0]['timabil_felags']}, {len(hop)} eyður\n")
        md.append("| Frá | Til | Mán. | Á undan | Á eftir | Aðrir á tímabilinu |")
        md.append("|---|---|---:|---|---|---|")
        for l in sorted(hop, key=lambda x: x["eyda_fra"]):
            md.append(f"| {l['eyda_fra']} | {l['eyda_til']} | {l['manudir']} | "
                      f"{l['haekkun_a_undan']} | {l['haekkun_a_eftir']} | "
                      f"{l['algengt_hja_odrum'] or '—'} |")
    with open(os.path.join(YFIRFERD, "eydur.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"Félög til yfirferðar: {len(valin)}")
    print(f"Eyður: {len(linur)}")
    print(f"\n{ut}\n{os.path.join(YFIRFERD, 'eydur.md')}")


if __name__ == "__main__":
    main(sys.argv[1:])
