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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import motadilar  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOGN = os.path.join(ROT, "gogn")
# Sameinaða skráin er notuð þegar hún er til, annars aðeins heildarskráin.
_SAMEINAD = os.path.join(GOGN, "haekkanir_sameinad.csv")
INN = _SAMEINAD if os.path.exists(_SAMEINAD) else os.path.join(GOGN, "haekkanir.csv")
UT_ROD = os.path.join(GOGN, "launathroun_eftir_felagi.csv")
UT_FELOG = os.path.join(GOGN, "felog.csv")
UT_LINUR = os.path.join(GOGN, "samningslinur.csv")

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
            tviburi.update({k: r[k] for k in ("a_vid", "tegund", "skjal", "slod", "kronur")})
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


def lesa_stadfestar_eydur():
    """Eyður sem hafa verið yfirfarnar og staðfestar réttar.

    Félagið samdi ekki um hækkun á tímabilinu, svo bilið er raunverulegt en
    ekki gat í gögnunum - það á því ekki að rjúfa samfellu.
    """
    leid = os.path.join(os.path.dirname(UT_ROD), "stadfestar_eydur.csv")
    if not os.path.exists(leid):
        return set()
    with open(leid, encoding="utf-8-sig", newline="") as f:
        return {(samhaefa_heiti(r["felag"]), r["eyda_fra"], r["eyda_til"])
                for r in csv.DictReader(f)}


def lesa_stadfestar_eydur_med_motadila():
    """Staðfestar eyður með mótaðila; autt þýðir aðalsamningur félagsins."""
    leid = os.path.join(os.path.dirname(UT_ROD), "stadfestar_eydur.csv")
    if not os.path.exists(leid):
        return set()
    with open(leid, encoding="utf-8-sig", newline="") as f:
        return {(samhaefa_heiti(r["felag"]), (r.get("motadili") or "").strip(),
                 r["eyda_fra"], r["eyda_til"]) for r in csv.DictReader(f)}


def finna_samfellu(linur, mork: int = EYDUMORK, stadfestar=frozenset()):
    """Finnur hvenær samfelld röð félagsins hefst, talið aftur á bak frá endanum.

    Samfella er mæld frá nýjustu mælingu aftur að fyrsta rofi - ekki yfir alla
    söguna. Eyða frá 1991 á ekki að ógilda röð sem hefur verið samfelld síðan
    2004: gömul göt skipta engu máli fyrir greiningu á síðustu tveimur áratugum,
    en gamla skilgreiningin útilokaði slíkar raðir alfarið.

    Skilar (samfelld_fra, fjöldi punkta í samfellunni, fjöldi eldri eyða).
    """
    linur = sorted(linur, key=lambda r: r["dagsetning"])

    def er_rof(i):
        a, b = linur[i - 1]["dagsetning"], linur[i]["dagsetning"]
        return manudir_milli(a, b) > mork and (a, b) not in stadfestar

    rof = None
    for i in range(len(linur) - 1, 0, -1):
        if er_rof(i):
            rof = i
            break
    if rof is None:
        return linur[0]["dagsetning"], len(linur), 0
    eldri = sum(1 for i in range(1, rof) if er_rof(i))
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


LANDSSAMBOND = os.path.join(GOGN, "landssambond.csv")
ADALSAMNINGAR = os.path.join(GOGN, "adalsamningar.csv")

# Heildarsamtök opinberra starfsmanna: ríkið er sjálfgefinn aðalsamningur
OPINBER_SAMTOK = {"BSRB", "BHM", "KÍ"}

# Fyrirtækjasamningur sem endurtekur hækkun aðalsamnings innan þessa glugga
# er staðfesting á henni en ekki sjálfstæð hækkun
SAMRUNI_FYRIRTAEKJA_DAGAR = 31

# Eigin hækkun aðildarfélags víkur fyrir hækkun landssambands innan glugga
ERFD_GLUGGI_DAGAR = 45


def lesa_toflu(leid):
    if not os.path.exists(leid):
        return []
    with open(leid, encoding="utf-8-sig", newline="") as f:
        return [r for r in csv.DictReader(f)
                if any((v or "").strip() for v in r.values())]


def nafn_ur_lykli(lykill: str) -> str:
    return lykill.split(":", 1)[1] if lykill.startswith("nafn:") else lykill


def velja_adalsamninga(radir, landssambond, handstyrt):
    """Aðalsamningur hvers félags: mótaðilinn sem sjálfgefna röðin fylgir.

    Forgangur: handstýring í gogn/adalsamningar.csv, þá landssamband
    (aðildarfélög SGS fylgja samningi SGS við SA), þá heildarsamtök (opinberir
    starfsmenn: ríkið, ASÍ: SA) og loks flest skjöl síðustu tíu ár.
    Talningin ein dugar ekki: hún myndi velja Advania sem aðalsamning RSÍ.
    """
    from datetime import date
    talning = collections.defaultdict(collections.Counter)
    nylegt = collections.defaultdict(collections.Counter)
    samtok = collections.defaultdict(collections.Counter)
    markadir = collections.defaultdict(collections.Counter)
    tiu_ar = str(date.today().year - 10)
    for r in radir:
        lykill = lykill_felags(r)
        if r.get("heildarsamtok"):
            samtok[lykill][r["heildarsamtok"]] += 1
        if r.get("markadur"):
            markadir[lykill][r["markadur"]] += 1
        m = r.get("motadili") or ""
        if m in ("", motadilar.OTHEKKTUR):
            continue
        talning[lykill][m] += 1
        if r["gildir_fra"] >= tiu_ar:
            nylegt[lykill][m] += 1
    adal = {}
    for lykill in {lykill_felags(r) for r in radir}:
        nafn = nafn_ur_lykli(lykill)
        if nafn in handstyrt:
            adal[lykill] = handstyrt[nafn]
            continue
        if nafn in landssambond:
            adal[lykill] = landssambond[nafn]["motadili"]
            continue
        c = talning[lykill]
        if not c:
            adal[lykill] = motadilar.OTHEKKTUR
            continue
        hs = algengast(samtok[lykill])
        # Opinberir starfsmenn: ríkið. ASÍ-félög: SA, jafnvel þótt þau semji
        # líka við sveitarfélög. Sérfélög fylgja markaðnum sem þau starfa á.
        opinbert = hs in OPINBER_SAMTOK or (
            hs != "ASÍ" and algengast(markadir[lykill]) == "opinber")
        forgangur = (["riki", "sveitarfelog", "reykjavikurborg"] if opinbert
                     else ["sa"] if hs == "ASÍ" else ["sa", "riki"])
        nothaefir = {m for m, n in c.items() if n >= 3}
        adal[lykill] = next((m for m in forgangur if m in nothaefir),
                            max(c, key=lambda m: (nylegt[lykill][m], c[m])))
    return adal


def draga_saman(hopur, lykill, motadili, heiti):
    """Ein lína á hvern (félag, mótaðila, dag) úr öllum skjölum sem nefna hann."""
    besta = min(hopur, key=lambda r: FORGANGUR.index(r["a_vid"])
                if r["a_vid"] in FORGANGUR else len(FORGANGUR))
    vidmid = besta["a_vid"]
    sama = [r for r in hopur if r["a_vid"] == vidmid]
    prosentur = [float(r["prosenta"]) for r in sama if r["prosenta"]]
    kronur = [int(r["kronur"]) for r in sama if r["kronur"]]
    pros = statistics.median(prosentur) if prosentur else None
    kr = statistics.median(kronur) if kronur else None
    heitin = collections.Counter(r.get("motadili_heiti") for r in hopur
                                 if r.get("motadili_heiti"))
    motadili_heiti = (heitin.most_common(1)[0][0] if heitin
                      else motadilar.HEITI.get(motadili, motadili))
    return {
        "felag_lykill": lykill,
        "felag_id": besta.get("felag_id") or "",
        "felag": heiti.get(lykill, besta["felag"]),
        "markadur": besta.get("markadur") or "",
        "heildarsamtok": besta.get("heildarsamtok") or "",
        "motadili": motadili,
        "motadili_heiti": motadili_heiti,
        "dagsetning": besta["gildir_fra"],
        "a_vid": vidmid,
        "prosenta": round(pros, 2) if pros is not None else None,
        "kronur": int(kr) if kr is not None else None,
        "tegund": besta["tegund"],
        "upprunar": ",".join(sorted({r.get("uppruni") or "ríkissáttasemjari"
                                     for r in hopur})),
        "heimildir": len(hopur),
        "olik_gildi": len(set(prosentur)) if prosentur else 0,
        "skjal": besta["skjal"],
        "slod": besta.get("slod") or "",
        "erft_fra": "",
        "ur_serssamningi": "",
    }


def sama_haekkun(a, b, dagar: int) -> bool:
    if dagar_milli(a["dagsetning"], b["dagsetning"]) > dagar:
        return False
    if a["prosenta"] is not None and b["prosenta"] is not None:
        return abs(a["prosenta"] - b["prosenta"]) < 0.005
    return bool(a["kronur"] and b["kronur"] and a["kronur"] == b["kronur"])


# Hækkun telst almenn hjá mótaðila ef minnst svona mörg félög hafa hana
ALMENN_MORK = 3


def almennar_haekkanir(linur):
    """Hækkanir sem mörg félög hafa í línu sama mótaðila.

    Lífskjarasamningurinn gaf t.d. 17.000 kr 1. apríl 2019 í tugum SA-lína.
    Slík hækkun er almenn hækkun viðkomandi mótaðila og gagnast til að þekkja
    fyrirtækjasamning sem aðeins endurtekur hana.
    """
    teljari = collections.defaultdict(collections.Counter)
    for (_, m), rr in linur.items():
        if m.startswith("fy-") or m == motadilar.OTHEKKTUR:
            continue
        for k in {(r["dagsetning"], r["prosenta"], r["kronur"]) for r in rr}:
            teljari[m][k] += 1
    return {m: [{"dagsetning": d, "prosenta": p, "kronur": k}
                for (d, p, k), n in c.items() if n >= ALMENN_MORK]
            for m, c in teljari.items()}


def fella_fyrirtaekjasamninga(linur, adal):
    """Fyrirtækjasamningar sem endurtaka hækkun aðalsamnings falla undir hann.

    Samningur við einstakt fyrirtæki vísar oft í hækkanir almenns
    kjarasamnings. Slík hækkun er staðfesting á aðalsamningnum, ekki
    sjálfstæð hækkun, og bætist því við heimildir hans. Það sama gildir um
    hækkun með óþekktum mótaðila. Aðrar hækkanir fyrirtækjasamnings standa
    sem sérsamningur og eru ekki keðjaðar við aðalsamninginn.
    """
    almennar = almennar_haekkanir(linur)
    fellt = fyllt = 0
    for lina in list(linur):
        lykill, m = lina
        adal_lina = (lykill, adal.get(lykill))
        if lina == adal_lina:
            continue
        if motadilar.TEGUND.get(m, "fyrirtaeki") not in ("fyrirtaeki", "othekkt"):
            continue
        adal_rod = linur.setdefault(adal_lina, [])
        eftir = []
        for r in linur[lina]:
            passar = next((a for a in adal_rod
                           if sama_haekkun(a, r, SAMRUNI_FYRIRTAEKJA_DAGAR)), None)
            if passar is not None:
                passar["heimildir"] += r["heimildir"]
                passar["upprunar"] = ",".join(sorted(set(passar["upprunar"].split(","))
                                                     | set(r["upprunar"].split(","))))
                fellt += 1
                continue
            # Vanti aðalsamninginn hækkun sem fyrirtækjasamningurinn endurtekur
            # úr almennum samningi mótaðilans, fyllir hún í skarðið
            almenn = any(sama_haekkun(x, r, SAMRUNI_FYRIRTAEKJA_DAGAR)
                         for x in almennar.get(adal_lina[1], []))
            nalaeg = any(dagar_milli(a["dagsetning"], r["dagsetning"]) <= ERFD_GLUGGI_DAGAR
                         for a in adal_rod)
            if almenn and not nalaeg:
                adal_rod.append({**r, "motadili": adal_lina[1],
                                 "motadili_heiti": motadilar.HEITI.get(
                                     adal_lina[1], adal_rod[0]["motadili_heiti"]
                                     if adal_rod else adal_lina[1]),
                                 "ur_serssamningi": r["motadili_heiti"]})
                fyllt += 1
                continue
            eftir.append(r)
        if eftir:
            linur[lina] = eftir
        else:
            linur.pop(lina)
        if not adal_rod:
            linur.pop(adal_lina)
    return fellt, fyllt


def erfa_fra_landssambondum(linur, landssambond, heiti):
    """Aðildarfélög fá hækkanir landssambandsins við mótaðilann.

    Hækkun SGS við SA ræður fyrir aðildarfélögin: eigin hækkun félagsins
    innan glugga frá hækkun SGS víkur, en eigin hækkanir á öðrum dögum
    haldast þar sem SGS-röðin nær ekki til.
    """
    erft = 0
    for nafn, x in landssambond.items():
        felag, samband, m = f"nafn:{nafn}", f"nafn:{x['samband']}", x["motadili"]
        rod_sambands = linur.get((samband, m))
        felags_linur = [r for (lk, _), rr in linur.items() if lk == felag for r in rr]
        if not rod_sambands or not felags_linur:
            continue
        fyrirmynd = felags_linur[0]
        eigin = linur.get((felag, m), [])
        haldid = [r for r in eigin
                  if all(dagar_milli(r["dagsetning"], s["dagsetning"]) > ERFD_GLUGGI_DAGAR
                         for s in rod_sambands)]
        erfdar = [{**s,
                   "felag_lykill": felag,
                   "felag": fyrirmynd["felag"],
                   "felag_id": fyrirmynd["felag_id"],
                   "markadur": fyrirmynd["markadur"],
                   "heildarsamtok": fyrirmynd["heildarsamtok"],
                   "erft_fra": heiti.get(samband, x["samband"])}
                  for s in rod_sambands]
        linur[(felag, m)] = haldid + erfdar
        erft += len(erfdar)
    return erft


def kedja(linur):
    """Keðjuð vísitala einnar samningslínu, með mælingu á bilum."""
    linur.sort(key=lambda r: r["dagsetning"])
    visitala, sidasta = 100.0, None
    for r in linur:
        d = r["dagsetning"]
        if sidasta is None:
            r["visitala"], r["bil_manudir"] = 100.0, ""
            r["visitala_athugasemd"] = "grunnur"
            sidasta = d
            continue
        bil = manudir_milli(sidasta, d)
        r["bil_manudir"] = bil
        if not r.get("i_kedju", 1):
            r["visitala_athugasemd"] = "hliðarsamningur - ekki keðjað"
        elif r["prosenta"]:
            visitala *= (1 + r["prosenta"] / 100)
            r["visitala_athugasemd"] = "" if bil <= 24 else "löng eyða á undan"
        else:
            r["visitala_athugasemd"] = "krónutöluhækkun - vísitala stendur í stað"
        r["visitala"] = round(visitala, 2)
        sidasta = d


def main():
    radir = [r for r in lesa() if r["artal_stada"] in TRAUST]
    heiti = samraema_felog(radir)
    landssambond = {r["felag"].strip(): r for r in lesa_toflu(LANDSSAMBOND)}
    handstyrt = {r["felag"].strip(): r["motadili"].strip()
                 for r in lesa_toflu(ADALSAMNINGAR)}
    adal = velja_adalsamninga(radir, landssambond, handstyrt)

    # Hver hækkun fær samningslínu (félag, mótaðili). Handvirk leiðrétting
    # án mótaðila og hækkun með óþekktum mótaðila af vef félagsins sjálfs
    # fara í aðalsamninginn; aðrar óþekktar standa sér.
    hopar = collections.defaultdict(list)
    for r in radir:
        lykill = lykill_felags(r)
        m = (r.get("motadili") or "").strip()
        if not m or (m == motadilar.OTHEKKTUR and str(r.get("af_felagsvef")) == "1"):
            m = adal[lykill]
        hopar[(lykill, m, r["gildir_fra"])].append(r)

    linur = collections.defaultdict(list)
    for (lykill, m, _), hopur in hopar.items():
        linur[(lykill, m)].append(draga_saman(hopur, lykill, m, heiti))

    fellt, fyllt = fella_fyrirtaekjasamninga(linur, adal)
    erft = erfa_fra_landssambondum(linur, landssambond, heiti)

    stadfestar = lesa_stadfestar_eydur_med_motadila()
    ut, felld_alls, samfella = [], 0, {}
    for lina, rodin in linur.items():
        lykill, m = lina
        er_adal = m == adal.get(lykill)
        merkja_hlidarsamninga(rodin)
        haldid, felld = fella_saman_tvitok(rodin)
        felld_alls += felld
        kedja(haldid)
        nafn = samhaefa_heiti(haldid[0]["felag"])
        eigin = {(a, b) for fl, mm, a, b in stadfestar
                 if fl == nafn and (mm == m or (not mm and er_adal))}
        fra, n, eldri = finna_samfellu(haldid, stadfestar=eigin)
        sidasta = max(r["dagsetning"] for r in haldid)
        samfella[lina] = {"fra": fra, "n": n, "eldri": eldri,
                          "ar": int(sidasta[:4]) - int(fra[:4])}
        # Vísitala endurgrunnuð á upphaf samfellunnar. Það er talan sem má
        # nota - keðjan yfir eyðuna er einmitt sá hluti sem ekki er treystandi.
        grunnur = next((r["visitala"] for r in haldid if r["dagsetning"] >= fra), None)
        for r in haldid:
            innan = r["dagsetning"] >= fra
            r["innan_samfellu"] = int(innan)
            r["visitala_samfella"] = (round(r["visitala"] / grunnur * 100, 2)
                                      if innan and grunnur else "")
            r["adalsamningur"] = int(er_adal)
        ut.extend(haldid)

    ut.sort(key=lambda r: (r["felag"] or "", -r["adalsamningur"],
                           r["motadili"], r["dagsetning"]))

    dalkar = ["felag_lykill", "felag_id", "felag", "markadur", "heildarsamtok",
              "motadili", "motadili_heiti", "adalsamningur", "erft_fra",
              "ur_serssamningi",
              "dagsetning", "a_vid", "prosenta", "kronur", "tegund",
              "visitala", "visitala_samfella", "innan_samfellu", "i_kedju",
              "bil_manudir", "visitala_athugasemd",
              "heimildir", "olik_gildi", "sameinad", "upprunar", "skjal", "slod"]
    with open(UT_ROD, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=dalkar, extrasaction="ignore")
        w.writeheader()
        w.writerows(ut)

    # Samningslínur: ein á hvern (félag, mótaðila)
    eftir_linu = collections.defaultdict(list)
    for r in ut:
        eftir_linu[(r["felag_lykill"], r["motadili"])].append(r)

    def lysing(lina, rr):
        sf = samfella.get(lina) or {}
        y = {"samfelld_n": sf.get("n", 0), "samfelld_ar": sf.get("ar", 0)}
        return {
            "felag_lykill": lina[0], "motadili": lina[1],
            "motadili_heiti": rr[0]["motadili_heiti"],
            "tegund": motadilar.TEGUND.get(lina[1], "fyrirtaeki"),
            "adalsamningur": rr[0]["adalsamningur"],
            "erft_fra": next((r["erft_fra"] for r in rr if r["erft_fra"]), ""),
            "fjoldi_haekkana": len(rr),
            "fyrsta": min(r["dagsetning"] for r in rr),
            "sidasta": max(r["dagsetning"] for r in rr),
            "samfelld_fra": sf.get("fra", ""), "samfelld_ar": sf.get("ar", ""),
            "samfelld_punktar": sf.get("n", ""), "eldri_eydur": sf.get("eldri", ""),
            "visitala_samfellu_lok": next((r["visitala_samfella"] for r in reversed(rr)
                                           if r["visitala_samfella"] not in ("", None)), ""),
            "heilleiki": heilleiki(y),
        }

    samningslinur = [lysing(l, sorted(rr, key=lambda r: r["dagsetning"]))
                     for l, rr in eftir_linu.items()]
    samningslinur.sort(key=lambda x: (x["felag_lykill"], -x["adalsamningur"],
                                      -x["fjoldi_haekkana"]))
    with open(UT_LINUR, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(samningslinur[0]))
        w.writeheader()
        w.writerows(samningslinur)

    # Uppflettitafla félaga. Tölur hennar miðast við aðalsamninginn; markaður
    # og heildarsamtök eru algengasta gildið yfir allar línur félagsins.
    flokkun = collections.defaultdict(lambda: {"markadir": collections.Counter(),
                                               "samtok": collections.Counter(),
                                               "audkenni": collections.Counter()})
    for r in ut:
        y = flokkun[r["felag_lykill"]]
        if r["felag_id"]:
            y["audkenni"][r["felag_id"]] += 1
        if r["markadur"]:
            y["markadir"][r["markadur"]] += 1
        if r["heildarsamtok"]:
            y["samtok"][r["heildarsamtok"]] += 1
    linur_felags = collections.defaultdict(list)
    for x in samningslinur:
        linur_felags[x["felag_lykill"]].append(x)

    felog_ut = []
    for lykill, xx in linur_felags.items():
        a = next((x for x in xx if x["adalsamningur"]), xx[0])
        rr = sorted(eftir_linu[(lykill, a["motadili"])], key=lambda r: r["dagsetning"])
        bil = [int(r["bil_manudir"]) for r in rr if r.get("bil_manudir") not in ("", None)]
        y = flokkun[lykill]
        felog_ut.append({
            "felag_lykill": lykill,
            "felag_id": algengast(y["audkenni"]),
            "felag": rr[0]["felag"],
            "markadur": algengast(y["markadir"]),
            "heildarsamtok": algengast(y["samtok"]),
            "adalsamningur": a["motadili"],
            "adalsamningur_heiti": a["motadili_heiti"],
            "fjoldi_samninga": len(xx),
            "fjoldi_haekkana": a["fjoldi_haekkana"],
            "fjoldi_haekkana_alls": sum(x["fjoldi_haekkana"] for x in xx),
            "fyrsta": a["fyrsta"], "sidasta": a["sidasta"],
            "samfelld_fra": a["samfelld_fra"], "samfelld_ar": a["samfelld_ar"],
            "samfelld_punktar": a["samfelld_punktar"], "eldri_eydur": a["eldri_eydur"],
            "visitala_lok": rr[-1]["visitala"],
            "visitala_samfellu_lok": a["visitala_samfellu_lok"],
            "mesta_bil_manudir": max(bil) if bil else "",
            "heilleiki": a["heilleiki"],
        })
    felog_ut.sort(key=lambda x: -x["fjoldi_haekkana"])
    with open(UT_FELOG, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(felog_ut[0]))
        w.writeheader()
        w.writerows(felog_ut)

    print(f"Hækkanir inn:                   {len(radir)}")
    print(f"Fyrirtækjahækkanir í aðalsamn.: {fellt} staðfestu, {fyllt} fylltu í")
    print(f"Erfðar frá landssambandi:       {erft}")
    print(f"Tvítalningar felldar saman:     {felld_alls}")
    print(f"Línur í tímaröð:                {len(ut)}")
    print(f"Samningslínur:                  {len(samningslinur)}")
    print(f"Félög:                          {len(felog_ut)}")
    print(f"\n{UT_ROD}\n{UT_LINUR}\n{UT_FELOG}")


if __name__ == "__main__":
    main()
