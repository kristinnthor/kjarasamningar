# -*- coding: utf-8 -*-
"""Byggir tímaröð umsaminna launahækkana eftir stéttarfélagi.

Tekur við haekkanir.csv og skilar tvennu:

  launathroun_eftir_felagi.csv  ein lína á hvert (félag, dagsetning) með
                                umsaminni hækkun og keðjaðri vísitölu
  felog.csv                     uppflettitafla félaga

Vísitalan er keðjuð út frá prósentuhækkunum. Þar sem eingöngu var samið um
krónutöluhækkun stendur vísitalan í stað og línan er merkt, því krónutölu er
ekki hægt að umbreyta í hlutfall án þess að vita launastigið - það bíður
launataflnanna.

Notkun:
    python scripts/launathroun.py
"""
from __future__ import annotations

import csv
import os
import sys
import collections
import re
import statistics

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
# Sameinaða skráin er notuð þegar hún er til, annars aðeins heildarskráin.
_SAMEINAD = os.path.join(GOGN, "haekkanir_sameinad.csv")
INN = _SAMEINAD if os.path.exists(_SAMEINAD) else os.path.join(GOGN, "haekkanir.csv")
UT_ROD = os.path.join(GOGN, "launathroun_eftir_felagi.csv")
UT_FELOG = os.path.join(GOGN, "felog.csv")

# Hvaða viðmið gengur fyrir þegar fleiri en eitt er skráð sama dag
FORGANGUR = ["almenn laun", "launatafla", "kauptaxtar",
             "lágmarkstekjur", "byrjunarlaun", "óskilgreint"]

# Ártalsstöður sem eru nógu traustar til að fara í tímaröðina
TRAUST = {"úr texta", "leiðrétt", "ályktað"}

# Bil sem telst rof á samfellu. Kjarasamningar bera oftast árlega áfanga, svo
# lengra bil en 18 mánuðir þýðir að hækkun vanti eða félagið hafi ekki samið.
EYDUMORK = 18


def manudir_milli(a: str, b: str) -> int:
    ay, am = int(a[:4]), int(a[5:7])
    by, bm = int(b[:4]), int(b[5:7])
    return (by - ay) * 12 + (bm - am)


def lesa():
    with open(INN, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def samhaefa_heiti(n: str) -> str:
    """Færir heiti félags í samanburðarhæft form.

    Sama félag kemur fyrir í mismunandi myndum - eignarfalli ("Samiðnar"),
    með skýringarhala ("Samiðn - Samband iðnfélaga") eða skammstafað. Þetta
    dregur úr því svo sama félag klofni ekki í tvær tímaraðir.
    """
    n = (n or "").strip().lower()
    n = re.split(r"\s+[-–]\s+", n)[0]          # skýringarhali aftan við bandstrik
    n = re.sub(r"\s*\(.*?\)", "", n)            # svigar
    n = re.sub(r"\s+stéttarfélag(?:s)?$", "", n)
    n = re.sub(r"[.,]", "", n).strip()
    # eignarfallsendingar sem birtast þegar heitið stendur í samhengi
    n = re.sub(r"(sambands|félags|sambandi|félagi)$", lambda m: m.group(1)[:-1]
               if m.group(1).endswith("s") else m.group(1), n)
    n = re.sub(r"^samiðnar$", "samiðn", n)
    n = re.sub(r"s$", "", n) if n.endswith("ðnar") else n
    return n


def samraema_felog(radir):
    """Skilar (lykill -> heiti) þar sem lykill er felag_id ef hann er til.

    Sama félag birtist undir mörgum heitum ("Samiðn", "Samiðnar",
    "Samiðn - Samband iðnfélaga"). felag_id úr skrá ríkissáttasemjara heldur
    þeim saman; algengasta heitið er valið sem samræmt heiti.
    """
    nofn = collections.defaultdict(collections.Counter)
    for r in radir:
        lykill = lykill_felags(r)
        if r["felag"]:
            nofn[lykill][r["felag"]] += 1
    return {k: c.most_common(1)[0][0] for k, c in nofn.items()}


def lykill_felags(r) -> str:
    """Auðkenni félags. Samhæft heiti gengur fyrir svo beygingarmyndir og
    skammstafanir renni saman; felag_id er vararáð þegar heiti vantar."""
    n = samhaefa_heiti(r.get("felag"))
    if n:
        return f"nafn:{n}"
    return f"id:{r['felag_id']}" if r.get("felag_id") else "óþekkt"


def algengast(teljari):
    return teljari.most_common(1)[0][0] if teljari else None


def dagar_milli(a: str, b: str) -> int:
    from datetime import date
    return abs((date.fromisoformat(b) - date.fromisoformat(a)).days)


def fella_saman_tvitok(rod, dagamork: int = 90):
    """Fellir saman sömu hækkun sem birtist á lítillega ólíkum dagsetningum.

    Sami áfangi er iðulega skráður með ólíkri dagsetningu eftir skjölum - ýmist
    vegna OCR-villu eða af því að eitt skjal nefnir undirritunardag og annað
    gildistökudag. Keðjist þeir báðir tvöfaldast hækkunin.

    Tvær færslur eru taldar sama áfanginn ef prósentan er sú sama og innan við
    `dagamork` dagar skilja þær að. Sú sem fleiri heimildir styðja heldur sér.
    """
    rod = sorted(rod, key=lambda r: r["dagsetning"])
    haldid, felld = [], 0
    for r in rod:
        tviburi = None
        if r["prosenta"]:
            for fyrri in reversed(haldid):
                if dagar_milli(fyrri["dagsetning"], r["dagsetning"]) > dagamork:
                    break
                if fyrri["prosenta"] == r["prosenta"]:
                    tviburi = fyrri
                    break
        if tviburi is None:
            haldid.append(r)
            continue
        felld += 1
        if r["heimildir"] > tviburi["heimildir"]:
            tviburi.update({k: r[k] for k in ("a_vid", "tegund", "skjal", "kronur")})
            tviburi["heimildir"] = r["heimildir"]
        tviburi["sameinad"] = tviburi.get("sameinad", 0) + 1
    return haldid, felld


def merkja_hlidarsamninga(linur, gluggi_dagar: int = 100, hlutfall: int = 3):
    """Merkir hækkanir sem líklega tilheyra hliðarsamningi en ekki aðalröðinni.

    Stéttarfélag semur oft við marga viðsemjendur samtímis - RSÍ semur við SA,
    Samtök rafverktaka, Landsnet og Orkuveituna, hvert með eigin áföngum. Séu
    þeir allir keðjaðir saman margfaldast hækkunin: RSÍ mældist með tólf
    hækkanir á tveimur árum sem námu +56%, langt yfir raunverulegri launaþróun.

    Aðalsamningurinn er sá sem flest skjöl staðfesta. Standi hækkun sem aðeins
    eitt skjal nefnir við hlið annarrar sem margfalt fleiri staðfesta er hún
    talin hliðarsamningur og ekki keðjuð - en hún hverfur ekki úr gögnunum.
    """
    linur = sorted(linur, key=lambda r: r["dagsetning"])
    for r in linur:
        r["i_kedju"] = 1
    for r in linur:
        h = int(r.get("heimildir") or 1)
        for o in linur:
            if o is r:
                continue
            if abs(dagar_milli(o["dagsetning"], r["dagsetning"])) > gluggi_dagar:
                continue
            ho = int(o.get("heimildir") or 1)
            if ho >= h * hlutfall and ho >= 3:
                r["i_kedju"] = 0
                break
    return linur


def finna_samfellu(linur, mork: int = EYDUMORK):
    """Finnur hvenær samfelld röð félagsins hefst, talið aftur á bak frá endanum.

    Samfella er mæld frá nýjustu mælingu aftur að fyrsta rofi - ekki yfir alla
    söguna. Eyða frá 1991 á ekki að ógilda röð sem hefur verið samfelld síðan
    2004: gömul göt skipta engu máli fyrir greiningu á síðustu tveimur áratugum,
    en gamla skilgreiningin útilokaði slíkar raðir alfarið.

    Skilar (samfelld_fra, fjöldi punkta í samfellunni, fjöldi eldri eyða).
    """
    linur = sorted(linur, key=lambda r: r["dagsetning"])
    rof = None
    for i in range(len(linur) - 1, 0, -1):
        if manudir_milli(linur[i - 1]["dagsetning"], linur[i]["dagsetning"]) > mork:
            rof = i
            break
    if rof is None:
        return linur[0]["dagsetning"], len(linur), 0
    eldri = sum(1 for i in range(1, rof)
                if manudir_milli(linur[i - 1]["dagsetning"],
                                 linur[i]["dagsetning"]) > mork)
    return linur[rof]["dagsetning"], len(linur) - rof, eldri + 1


def heilleiki(y) -> str:
    """Mat á samfellu, miðað við nýjasta óslitna kaflann.

    `samfelld_fra` segir hvenær sá kafli hefst; þessi einkunn segir aðeins
    hvort hann sé nógu langur til að byggja á.
    """
    if y.get("samfelld_n", 0) < 3:
        return "of fáir punktar"
    if y.get("samfelld_ar", 0) >= 3:
        return "samfelld"
    return "eyður"


def main():
    radir = lesa()
    heiti = samraema_felog(radir)

    # Safna saman eftir (félag, dagsetning)
    hopar = collections.defaultdict(list)
    for r in radir:
        if r["artal_stada"] not in TRAUST:
            continue
        hopar[(lykill_felags(r), r["gildir_fra"])].append(r)

    ut = []
    for (lykill, dags), hopur in hopar.items():
        # Velja viðmið eftir forgangi
        besta = min(hopur, key=lambda r: FORGANGUR.index(r["a_vid"])
                    if r["a_vid"] in FORGANGUR else len(FORGANGUR))
        vidmid = besta["a_vid"]
        sama = [r for r in hopur if r["a_vid"] == vidmid]

        prosentur = [float(r["prosenta"]) for r in sama if r["prosenta"]]
        kronur = [int(r["kronur"]) for r in sama if r["kronur"]]

        pros = statistics.median(prosentur) if prosentur else None
        kr = statistics.median(kronur) if kronur else None
        olik = len(set(prosentur)) if prosentur else 0

        ut.append({
            "felag_lykill": lykill,
            "felag_id": besta.get("felag_id") or "",
            "felag": heiti.get(lykill, besta["felag"]),
            "markadur": besta.get("markadur") or "",
            "heildarsamtok": besta.get("heildarsamtok") or "",
            "dagsetning": dags,
            "a_vid": vidmid,
            "prosenta": round(pros, 2) if pros is not None else None,
            "kronur": int(kr) if kr is not None else None,
            "tegund": besta["tegund"],
            "upprunar": ",".join(sorted({r.get("uppruni") or "ríkissáttasemjari"
                                         for r in hopur})),
            "heimildir": len(hopur),
            "olik_gildi": olik,
            "skjal": besta["skjal"],
        })

    # Merkja hliðarsamninga áður en keðjað er
    _eftir_felagi = collections.defaultdict(list)
    for r in ut:
        _eftir_felagi[r["felag_lykill"]].append(r)
    for linur in _eftir_felagi.values():
        merkja_hlidarsamninga(linur)

    # Fella saman tvítalningu innan hvers félags áður en keðjað er
    eftir_felagi = collections.defaultdict(list)
    for r in ut:
        eftir_felagi[r["felag_lykill"]].append(r)
    ut, felld_alls = [], 0
    for linur in eftir_felagi.values():
        haldid, felld = fella_saman_tvitok(linur)
        ut.extend(haldid)
        felld_alls += felld
    print(f"Tvítalningar felldar saman:  {felld_alls}")

    ut.sort(key=lambda r: (r["felag"] or "", r["dagsetning"]))

    # Keðjuð vísitala á hvert félag, ásamt mælingu á eyðum.
    #
    # Vísitalan er aðeins marktæk ef allar hækkanir félagsins náðust. Löng bil
    # milli mælipunkta þýða að hækkanir vanti og vísitalan vanmeti þróunina.
    # `bil_manudir` gerir það sýnilegt á hverri línu.
    visitala = {}
    sidasta = {}
    for r in ut:
        f = r["felag_lykill"]
        d = r["dagsetning"]
        if f not in visitala:
            visitala[f] = 100.0
            r["visitala"] = 100.0
            r["bil_manudir"] = ""
            r["visitala_athugasemd"] = "grunnur"
            sidasta[f] = d
            continue
        bil = manudir_milli(sidasta[f], d)
        r["bil_manudir"] = bil
        if not r.get("i_kedju", 1):
            r["visitala_athugasemd"] = "hliðarsamningur - ekki keðjað"
        elif r["prosenta"]:
            visitala[f] *= (1 + r["prosenta"] / 100)
            r["visitala_athugasemd"] = "" if bil <= 24 else "löng eyða á undan"
        else:
            r["visitala_athugasemd"] = "krónutöluhækkun - vísitala stendur í stað"
        r["visitala"] = round(visitala[f], 2)
        sidasta[f] = d

    # Samfella hvers félags, talin aftur á bak frá nýjustu mælingu
    eftir_felagi_lokad = collections.defaultdict(list)
    for r in ut:
        eftir_felagi_lokad[r["felag_lykill"]].append(r)
    samfella = {}
    for lykill, linur in eftir_felagi_lokad.items():
        if not linur:
            continue
        fra, n, eldri = finna_samfellu(linur)
        sidasta = max(r["dagsetning"] for r in linur)
        samfella[lykill] = {
            "fra": fra, "n": n, "eldri": eldri,
            "ar": int(sidasta[:4]) - int(fra[:4]),
        }
        # Vísitala endurgrunnuð á upphaf samfellunnar. Það er talan sem má
        # nota - keðjan yfir eyðuna er einmitt sá hluti sem ekki er treystandi.
        grunnur = next((r["visitala"] for r in sorted(
            linur, key=lambda x: x["dagsetning"]) if r["dagsetning"] >= fra), None)
        for r in linur:
            innan = r["dagsetning"] >= fra
            r["innan_samfellu"] = int(innan)
            r["visitala_samfella"] = (round(r["visitala"] / grunnur * 100, 2)
                                      if innan and grunnur else "")

    dalkar = ["felag_lykill", "felag_id", "felag", "markadur", "heildarsamtok",
              "dagsetning", "a_vid", "prosenta", "kronur", "tegund",
              "visitala", "visitala_samfella", "innan_samfellu", "i_kedju",
              "bil_manudir", "visitala_athugasemd",
              "heimildir", "olik_gildi", "sameinad", "upprunar", "skjal"]
    with open(UT_ROD, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=dalkar, extrasaction="ignore")
        w.writeheader()
        w.writerows(ut)

    # Uppflettitafla félaga. Markaður og heildarsamtök eru tekin sem algengasta
    # gildið, ekki það síðasta - stök færsla getur borið villandi flokkun.
    yfirlit = collections.defaultdict(
        lambda: {"n": 0, "fra": "9999", "til": "0",
                 "markadir": collections.Counter(),
                 "samtok": collections.Counter(),
                 "audkenni": collections.Counter()})
    for r in ut:
        y = yfirlit[r["felag_lykill"]]
        y["n"] += 1
        y["fra"] = min(y["fra"], r["dagsetning"])
        y["til"] = max(y["til"], r["dagsetning"])
        y["felag"] = r["felag"]
        if r["felag_id"]:
            y["audkenni"][r["felag_id"]] += 1
        if r["markadur"]:
            y["markadir"][r["markadur"]] += 1
        if r["heildarsamtok"]:
            y["samtok"][r["heildarsamtok"]] += 1
        y["visitala_lok"] = r["visitala"]
        if r.get("visitala_samfella") not in ("", None):
            y["visitala_samfellu_lok"] = r["visitala_samfella"]
        if r.get("bil_manudir"):
            y["mesta_bil"] = max(y.get("mesta_bil", 0), int(r["bil_manudir"]))
    with open(UT_FELOG, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["felag_lykill", "felag_id", "felag",
                                          "markadur", "heildarsamtok",
                                          "fjoldi_haekkana", "fyrsta", "sidasta",
                                          "samfelld_fra", "samfelld_ar",
                                          "samfelld_punktar", "eldri_eydur",
                                          "visitala_lok", "visitala_samfellu_lok",
                                          "mesta_bil_manudir", "heilleiki"])
        w.writeheader()
        for k, y in sorted(yfirlit.items(), key=lambda kv: -kv[1]["n"]):
            w.writerow({"felag_lykill": k,
                        "felag_id": algengast(y["audkenni"]),
                        "felag": y.get("felag"),
                        "markadur": algengast(y["markadir"]),
                        "heildarsamtok": algengast(y["samtok"]),
                        "fjoldi_haekkana": y["n"], "fyrsta": y["fra"],
                        "sidasta": y["til"], "visitala_lok": y.get("visitala_lok"),
                        "samfelld_fra": (samfella.get(k) or {}).get("fra", ""),
                        "samfelld_ar": (samfella.get(k) or {}).get("ar", ""),
                        "samfelld_punktar": (samfella.get(k) or {}).get("n", ""),
                        "eldri_eydur": (samfella.get(k) or {}).get("eldri", ""),
                        "visitala_samfellu_lok": y.get("visitala_samfellu_lok", ""),
                        "mesta_bil_manudir": y.get("mesta_bil", ""),
                        "heilleiki": heilleiki({
                            **y,
                            "samfelld_n": (samfella.get(k) or {}).get("n", 0),
                            "samfelld_ar": (samfella.get(k) or {}).get("ar", 0)})})

    print(f"Hækkanir inn:          {len(radir)}")
    print(f"Línur í tímaröð:       {len(ut)}")
    print(f"Félög:                 {len(yfirlit)}")
    print(f"Tímabil:               {min(r['dagsetning'] for r in ut)} - "
          f"{max(r['dagsetning'] for r in ut)}")
    print(f"\n{UT_ROD}\n{UT_FELOG}")


if __name__ == "__main__":
    main()
