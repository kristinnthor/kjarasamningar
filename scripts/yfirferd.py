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
    python scripts/yfirferd.py --eydur-fra 1990   # sleppa eyðum sem enda fyrr

Eyður sem ljúka fyrir 1990 eru ekki teknar með: gögn frá þeim tíma eru rýr
og skipta litlu í greiningum. Eyða sem spannar 1990 (t.d. 1987 → 1992) er
tekin með, því hluti hennar fellur innan tímabilsins sem skiptir máli.

Útfylltar línur úr fyrri útgáfu skrárinnar haldast: þær eru paraðar við nýju
línurnar eftir (félag, eyda_fra, eyda_til). Útfylltar línur sem eiga sér enga
eyðu lengur - t.d. af því að leiðréttingin hefur þegar lokað henni - eru
ekki felldar niður nema þær séu þegar komnar í gogn/handvirkar_leidrettingar.csv.
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from launathroun import samhaefa_heiti  # noqa: E402
import motadilar  # noqa: E402

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
                   hamark: int = 4) -> list[dict]:
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
    return [{"dagsetning": d, "prosenta": p, "felog": n}
            for (d, p), n in teljari.most_common(hamark) if n >= 3]


def lysa_algengt(algengt: list[dict]) -> str:
    return "; ".join(f"{a['dagsetning']} {a['prosenta']:.2f}%".replace(".", ",")
                     + f" ({a['felog']} félög)" for a in algengt)


def lesa_samninga():
    """Samningar heildarskrárinnar með beinni PDF-slóð og gildistíma.

    Ríkissáttasemjari birtir hvern samning á fastri slóð, svo hægt er að
    vísa beint á skjalið sem ætti að geyma hækkunina sem vantar.
    """
    leid = os.path.join(ROT, "samningar", "rikissattasemjari", "lysigogn.json")
    if not os.path.exists(leid):
        return []
    with open(leid, encoding="utf-8") as f:
        allir = json.load(f)
    ut = []
    for x in allir:
        if not x.get("pdf_url"):
            continue
        heiti = f"{x.get('launthegi_canonical') or ''} ; {x.get('launthegi') or ''}"
        ut.append({
            "nafn": samhaefa_heiti(heiti),
            "hratt": heiti.lower(),
            "fra": (x.get("fra") or "")[:10],
            "til": (x.get("til") or "")[:10],
            "tegund": x.get("tegund") or "",
            # Skráarheitin eru ekki lýsandi - "SA_v_kvikmyndahusa.pdf" er
            # RSÍ-samningur. Viðsemjandinn segir notandanum hvað hann opnar.
            "atvinnurekandi": (x.get("atvinnurekandi") or "").strip(),
            "motadili": motadilar.ur_skra(x.get("atvinnurekandi"))[0],
            "slod": x["pdf_url"],
        })
    return ut


def samningar_a_bili(samningar, felag: str, fra: str, til: str, hamark: int = 3,
                     motadili: str | None = None):
    """Samningar félagsins sem gilda yfir eyðuna.

    Hækkun sem vantar á að standa í samningi sem var í gildi á tímabilinu, svo
    skörun gildistíma er rétta viðmiðið - ekki undirritunardagur. Eyðan er í
    aðalsamningnum, svo samningar við sama mótaðila koma fyrst: sérsamningur
    við annan mótaðila á ekki heima í þeirri röð.
    """
    n = samhaefa_heiti(felag)
    if not n or len(n) < 3:
        return []
    # Stuttar skammstafanir ("rsí", "vm", "kí") mega ekki lenda inni í öðrum
    # orðum, svo þær eru bornar saman á orðamörkum.
    if len(n) <= 4:
        mynstur = re.compile(rf"(?<!\w){re.escape(n)}(?!\w)")
        passar = lambda s: bool(mynstur.search(s["nafn"]) or mynstur.search(s["hratt"]))
    else:
        passar = lambda s: n in s["nafn"] or n in s["hratt"]
    fundnir = []
    for s in samningar:
        if not passar(s):
            continue
        if not s["fra"]:
            continue
        # Skörun: samningurinn hefst fyrir lok eyðunnar og lýkur eftir upphaf hennar
        if s["fra"] > til:
            continue
        if s["til"] and s["til"] < fra:
            continue
        fundnir.append(s)
    # Sami mótaðili fyrst, svo þeir sem hefjast innan eyðunnar
    fundnir.sort(key=lambda s: (motadili is not None and s["motadili"] != motadili,
                                not (fra <= s["fra"] <= til), s["fra"]))
    return fundnir[:hamark]


DALKAR = [
    # Til útfyllingar
    "stada", "dagsetning", "prosenta", "kronur", "a_vid", "heimild", "athugasemd",
    # Samhengi, forútfyllt
    "felag", "felag_audkenni", "motadili", "motadili_heiti",
    "eyda_fra", "eyda_til", "manudir",
    "haekkun_a_undan", "haekkun_a_eftir", "algengt_hja_odrum",
    "samningar_fjoldi", "samningar", "slodir",
    "heilleiki", "fjoldi_haekkana", "timabil_felags",
]


TIL_UTFYLLINGAR = DALKAR[:7]


def lesa_fyrri_utfyllingu():
    """Útfylltar línur úr núverandi eydur.csv, flokkaðar eftir eyðu.

    Ein eyða getur átt margar útfylltar línur - notandinn afritar línuna
    einu sinni fyrir hverja hækkun sem vantar.
    """
    leid = os.path.join(YFIRFERD, "eydur.csv")
    if not os.path.exists(leid):
        return {}
    eftir_eydu = collections.defaultdict(list)
    with open(leid, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if any((r.get(d) or "").strip() for d in TIL_UTFYLLINGAR):
                eftir_eydu[(r["felag"], r["eyda_fra"], r["eyda_til"])].append(r)
    return eftir_eydu


def thegar_festar():
    leid = os.path.join(GOGN, "handvirkar_leidrettingar.csv")
    if not os.path.exists(leid):
        return set()
    with open(leid, encoding="utf-8-sig", newline="") as f:
        return {(r["felag"], r["gildir_fra"]) for r in csv.DictReader(f)}


def main(argv):
    fra_ar = "2025"
    if "--fra" in argv:
        fra_ar = argv[argv.index("--fra") + 1]
    eydur_fra = "1990"
    if "--eydur-fra" in argv:
        eydur_fra = argv[argv.index("--eydur-fra") + 1]
    eydumork_dags = f"{eydur_fra}-01-01"
    fyrri_utfylling = lesa_fyrri_utfyllingu()
    # Eyður sem hafa verið staðfestar réttar ("engin hækkun á tímabilinu")
    stadfestar = set()
    if os.path.exists(os.path.join(GOGN, "stadfestar_eydur.csv")):
        stadfestar = {(r["felag"], r["eyda_fra"], r["eyda_til"])
                      for r in lesa("stadfestar_eydur.csv")}

    felog = lesa("felog.csv")
    rod = lesa("launathroun_eftir_felagi.csv")
    samningar = lesa_samninga()

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

    # Eyður eru aðeins skoðaðar í aðalsamningi hvers félags. Sérsamningar eru
    # stopulir í eðli sínu og bil í þeim þýðir ekki að hækkun vanti.
    rod = [r for r in rod if r.get("adalsamningur", "1") == "1"]
    eftir_felagi = collections.defaultdict(list)
    for r in rod:
        eftir_felagi[r["felag_lykill"]].append(r)

    # Samfella er mæld aftur á bak frá nýjustu mælingu, svo félag getur talist
    # samfellt en samt átt eyður fyrir samfelld_fra. Þær eyður eru einmitt það
    # sem stöðvar röðina, svo öll nýleg félög koma til greina - valið ræðst af
    # því hvort þau eigi eyðu eftir markinu, ekki af heilleika.
    valin = [f for f in felog if f["sidasta"] >= f"{fra_ar}-01-01"]
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
            if thessi["dagsetning"] < eydumork_dags:
                continue
            if (f["felag"], fyrri["dagsetning"], thessi["dagsetning"]) in stadfestar:
                continue
            tengdir = samningar_a_bili(samningar, f["felag"],
                                       fyrri["dagsetning"], thessi["dagsetning"],
                                       motadili=f.get("adalsamningur"))
            linur.append({
                "_tengdir": tengdir,
                "samningar_fjoldi": len(tengdir),
                "samningar": " | ".join(
                    f"{s['fra']}–{s['til'] or '?'} {s['atvinnurekandi'] or '?'} "
                    f"({s['tegund']})" for s in tengdir),
                "slodir": " ".join(s["slod"] for s in tengdir),
                "stada": "", "dagsetning": "", "prosenta": "", "kronur": "",
                "a_vid": "", "heimild": "", "athugasemd": "",
                "felag": f["felag"],
                "felag_audkenni": audkenni.get(f["felag"], ""),
                "motadili": f.get("adalsamningur", ""),
                "motadili_heiti": f.get("adalsamningur_heiti", ""),
                "eyda_fra": fyrri["dagsetning"],
                "eyda_til": thessi["dagsetning"],
                "manudir": bil,
                "haekkun_a_undan": lysa(fyrri),
                "haekkun_a_eftir": lysa(thessi),
                "_algengt": (algengt := algengt_a_bili(
                    rod, fyrri["dagsetning"], thessi["dagsetning"],
                    f["felag_lykill"])),
                "algengt_hja_odrum": lysa_algengt(algengt),
                "heilleiki": f["heilleiki"],
                "fjoldi_haekkana": f["fjoldi_haekkana"],
                "timabil_felags": f"{f['fyrsta']} – {f['sidasta']}",
            })

    valin = [f for f in valin if any(l["felag"] == f["felag"] for l in linur)]

    # Fyrri útfylling flutt yfir. Eyða með fleiri en eina útfyllta línu fær
    # eina línu á hverja.
    festar = thegar_festar()
    notadar, fluttar = set(), 0
    med_utfyllingu = []
    for l in linur:
        lykill = (l["felag"], l["eyda_fra"], l["eyda_til"])
        fyrri = fyrri_utfylling.get(lykill)
        if not fyrri:
            med_utfyllingu.append(l)
            continue
        notadar.add(lykill)
        for r in fyrri:
            med_utfyllingu.append({**l, **{d: r.get(d, "") for d in TIL_UTFYLLINGAR}})
            fluttar += 1
    # Útfylltar línur sem eiga enga eyðu lengur og eru ekki þegar festar
    munadarlausar = [r for k, rr in fyrri_utfylling.items() if k not in notadar
                     for r in rr
                     if (r["felag"], (r.get("dagsetning") or "").strip()) not in festar]
    for r in munadarlausar:
        med_utfyllingu.append({**r, "_tengdir": []})
    linur = med_utfyllingu
    fjoldi_eyda = len({(l["felag"], l["eyda_fra"], l["eyda_til"]) for l in linur})

    os.makedirs(YFIRFERD, exist_ok=True)
    ut = os.path.join(YFIRFERD, "eydur.csv")
    with open(ut, "w", encoding="utf-8-sig", newline="") as f:
        # _tengdir er hjálparreitur fyrir markdown-útgáfuna
        w = csv.DictWriter(f, fieldnames=DALKAR, extrasaction="ignore")
        w.writeheader()
        w.writerows(linur)

    # Skipulögð útgáfa fyrir vefviðmótið (yfirferd.html), eitt skjal á félag
    vefur = {}
    for l in linur:
        if "_algengt" not in l:
            continue
        a = l["felag_audkenni"] or re.sub(r"[^a-z0-9]+", "-", l["felag"].lower())
        f = vefur.setdefault(a, {
            "audkenni": a, "felag": l["felag"], "heilleiki": l["heilleiki"],
            "motadili": l.get("motadili", ""),
            "adalsamningur": l.get("motadili_heiti", ""),
            "fjoldi_haekkana": int(l["fjoldi_haekkana"]),
            "timabil": l["timabil_felags"], "eydur": []})
        if any(e["id"] == f"{l['eyda_fra']}_{l['eyda_til']}" for e in f["eydur"]):
            continue
        f["eydur"].append({
            "id": f"{l['eyda_fra']}_{l['eyda_til']}",
            "fra": l["eyda_fra"], "til": l["eyda_til"], "manudir": l["manudir"],
            "undan": l["haekkun_a_undan"], "eftir": l["haekkun_a_eftir"],
            "algengt": l["_algengt"],
            "samningar": [{**{k: s[k] for k in ("fra", "til", "atvinnurekandi",
                                                  "tegund", "slod")},
                           "sami_motadili": s["motadili"] == l.get("motadili")}
                          for s in l["_tengdir"]],
        })
    with open(os.path.join(YFIRFERD, "eydur.json"), "w", encoding="utf-8") as f:
        json.dump({"eydur_fra": eydur_fra, "felog": list(vefur.values())},
                  f, ensure_ascii=False, indent=1)
    # Sama skrá fyrir opnu eyðuskráninguna á GitHub Pages (docs/eydur.html)
    with open(os.path.join(ROT, "docs", "eydur.json"), "w", encoding="utf-8") as f:
        json.dump({"eydur_fra": eydur_fra, "uppfaert": date.today().isoformat(),
                   "felog": list(vefur.values())},
                  f, ensure_ascii=False, separators=(",", ":"))

    # Læsilegt yfirlit til að skanna hratt
    md = [f"# Eyður til yfirferðar\n",
          f"Félög með gögn frá og með {fra_ar}. Aðeins eyður í aðalsamningi "
          f"hvers félags sem ljúka {eydur_fra} eða síðar eru teknar með.\n",
          f"**{len(valin)} félög, {fjoldi_eyda} eyður.** "
          f"Eyða telst bil lengra en {EYDUMORK} mánuðir.\n"]
    eftir_heiti = collections.defaultdict(list)
    for l in linur:
        eftir_heiti[l["felag"]].append(l)
    for heiti in sorted(eftir_heiti, key=lambda h: -len(eftir_heiti[h])):
        hop = eftir_heiti[heiti]
        md.append(f"\n## {heiti}\n")
        md.append(f"Aðalsamningur við {hop[0].get('motadili_heiti') or '?'}: "
                  f"{hop[0]['fjoldi_haekkana']} hækkanir, "
                  f"{hop[0]['timabil_felags']}, {len(hop)} eyður\n")
        for l in sorted(hop, key=lambda x: x["eyda_fra"]):
            md.append(f"\n**{l['eyda_fra']} → {l['eyda_til']}** "
                      f"({l['manudir']} mán.)  ")
            md.append(f"Á undan: {l['haekkun_a_undan']} · "
                      f"Á eftir: {l['haekkun_a_eftir']}  ")
            if l["algengt_hja_odrum"]:
                md.append(f"Aðrir á tímabilinu: {l['algengt_hja_odrum']}  ")
            if l["_tengdir"]:
                md.append("Samningar í gildi:  ")
                for t in l["_tengdir"]:
                    md.append(f"- [{t['fra']}–{t['til'] or '?'} · "
                              f"{t['atvinnurekandi'] or 'óþekktur viðsemjandi'} · "
                              f"{t['tegund']}]({t['slod']})")
            else:
                md.append("*Enginn samningur fannst í heildarskránni "
                          "fyrir þetta tímabil.*  ")
    with open(os.path.join(YFIRFERD, "eydur.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(f"Félög til yfirferðar: {len(valin)}")
    print(f"Eyður: {fjoldi_eyda} (sem ljúka {eydur_fra} eða síðar)")
    print(f"Útfylltar línur fluttar yfir: {fluttar}"
          + (f", auk {len(munadarlausar)} án eyðu" if munadarlausar else ""))
    print(f"\n{ut}\n{os.path.join(YFIRFERD, 'eydur.md')}")


if __name__ == "__main__":
    main(sys.argv[1:])
