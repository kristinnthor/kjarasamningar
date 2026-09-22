# -*- coding: utf-8 -*-
"""Staðlar mótaðila (viðsemjendur) kjarasamninga.

Stéttarfélag semur við marga mótaðila: aðalkjarasamning við samtök
atvinnurekenda eða hið opinbera, og sérsamninga við einstök fyrirtæki og
stofnanir. Hækkanir úr ólíkum samningum má ekki keðja saman, svo hver hækkun
þarf að bera staðlað auðkenni mótaðila.

Heitin koma úr tveimur áttum:

  - Skrá ríkissáttasemjara: hrein heiti ("Samtök atvinnulífsins, SA").
  - Vefskjöl: aðilar lesnir úr texta, í eignarfalli og hástöfum og oft með
    rusli ("SAMTAKA ATVINNULÍFSINS", "Samtaka atvinnulífsins", "fylgiskjöl").

Forverar eru felldir undir arftaka svo samningslína haldist samfelld yfir
nafnabreytingar: VSÍ og VMS urðu SA 1999, Samninganefnd bankanna og SFF
sömdu fyrir fjármálafyrirtæki áður en SA tók við.
"""
from __future__ import annotations

import re
import unicodedata

# (auðkenni, heiti, tegund, mynstur). Röðin skiptir máli: fyrsta mynstur sem
# passar ræður, svo sértækari aðilar koma á undan almennari.
# Tegundir: riki, sveitarfelag, samtok (samtök atvinnurekenda), fyrirtaeki.
MOTADILAR = [
    ("riki", "Ríkið", "riki", [
        r"r[ií]kiss?j[oó]ð", r"fj[aá]rm[aá]la\W*(og efnahags)?r[aá]ðherr",
        r"\bsnr\b", r"samninganefnd r[ií]kisins", r"^r[ií]ki[ðd]$",
        r"\bfjarmalaraduneyti", r"\brikid\b", r"\bog r[ií]kisins\b"]),
    ("reykjavikurborg", "Reykjavíkurborg", "sveitarfelag", [
        r"reykjav[ií]kurborg", r"\brvk\b"]),
    ("sveitarfelog", "Samband íslenskra sveitarfélaga", "sveitarfelag", [
        r"samband\w* [ií]slenskra sveitarf[eé]lag", r"launanefnd sveitarf",
        r"\bsambands?\W+islenskra\W+sveitarfelaga", r"\bsns\b"]),
    ("sfs", "Samtök fyrirtækja í sjávarútvegi", "samtok", [
        r"sj[aá]var[uú]tveg", r"[uú]tvegsmann", r"\bl[ií][uú]\b", r"\bsfs\b",
        r"botnv[oö]rpuskip"]),
    ("fa", "Félag atvinnurekenda", "samtok", [
        r"atvinnurekenda", r"st[oó]rkaupmann", r"\bf[ií]s\b"]),
    ("sfv", "Samtök fyrirtækja í velferðarþjónustu", "samtok", [
        r"velfer[ðd]ar(þ|th)j[oó]nust"]),
    ("smabatar", "Landssamband smábátaeigenda", "samtok", [
        r"sm[aá]b[aá]taeig"]),
    ("bgs", "Bílgreinasambandið", "samtok", [
        r"b[ií]lgreinasamband"]),
    ("sa", "Samtök atvinnulífsins", "samtok", [
        r"atvinnul[ií]f", r"^sa$", r"^sa\W", r"\Wsa$", r"\bsa\b",
        r"vinnuveitendasamband", r"\bvs[ií]\b", r"vinnum[aá]lasamband",
        r"rafverktak", r"\bsart\b", r"fer[ðd]a(þ|th)j[oó]nust", r"\bsaf\b",
        r"i[ðd]na[ðd]arins", r"meistarasamband", r"meistaraf[eé]lag",
        r"samninganefnd bankanna", r"fj[aá]rm[aá]lafyrirt", r"\bsff\b",
        r"verslunar og (þ|th)j[oó]nustu", r"\bsv(þ|th)\b",
        r"veitinga\W*og\W*gistih", r"samvinnuf[eé]lag"]),
]

HEITI = {a: h for a, h, _, _ in MOTADILAR}
TEGUND = {a: t for a, _, t, _ in MOTADILAR}
_MYNSTUR = [(a, [re.compile(m) for m in mm]) for a, _, _, mm in MOTADILAR]

# Vefir viðsemjenda: skjal þaðan er samningur við eiganda vefsins
VEFIR_MOTADILA = {"sa": "sa", "fa": "fa", "rikid": "riki",
                  "samband": "sveitarfelog", "reykjavik": "reykjavikurborg"}

OTHEKKTUR = "othekktur"
HEITI[OTHEKKTUR] = "Óþekktur mótaðili"
TEGUND[OTHEKKTUR] = "othekkt"

# Lagaform og viðskeyti sem skipta ekki máli fyrir hver aðilinn er
_LAGAFORM = re.compile(r"\b(ohf|hf|ehf|sf|ses|bs|slf|svf)\b\.?", re.I)

# Beygingar- og ritmyndir sama fyrirtækis í skránni
_SAMHEITI_FYRIRTAEKJA = {
    "simans": "siminn",
    "flugfelags-islands": "flugfelag-islands",
    "landsvirkjunar": "landsvirkjun",
    "nordurorku": "nordurorka",
}

_STAFIR = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ý": "y",
           "þ": "th", "æ": "ae", "ö": "o", "ð": "d"}


def _ascii(s: str) -> str:
    s = (s or "").lower()
    s = "".join(_STAFIR.get(c, c) for c in s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _hreinsa(s: str) -> str:
    s = (s or "").lower().replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


def thekktur(texti: str) -> str | None:
    """Auðkenni þekkts mótaðila sem nefndur er í texta, annars None."""
    t = _hreinsa(texti)
    if not t:
        return None
    a = _ascii(t)
    for audkenni, mynstur in _MYNSTUR:
        for m in mynstur:
            if m.search(t) or m.search(a):
                return audkenni
    return None


def fyrirtaeki_audkenni(nafn: str) -> str:
    """Auðkenni fyrirtækis eða stofnunar úr heiti eins og skráin nefnir það."""
    n = _LAGAFORM.sub("", nafn or "")
    n = re.sub(r"\(.*?\)", "", n)
    n = re.split(r",", n)[0]
    s = re.sub(r"[^a-z0-9]+", "-", _ascii(n)).strip("-")[:48]
    s = _SAMHEITI_FYRIRTAEKJA.get(s, s)
    return f"fy-{s}" if s else OTHEKKTUR


def ur_skra(nafn: str) -> tuple[str, str]:
    """(auðkenni, heiti) mótaðila úr skrá ríkissáttasemjara."""
    a = thekktur(nafn)
    if a:
        return a, HEITI[a]
    if not (nafn or "").strip():
        return OTHEKKTUR, HEITI[OTHEKKTUR]
    heiti = re.split(r",", _LAGAFORM.sub("", nafn))[0].strip() or nafn.strip()
    return fyrirtaeki_audkenni(nafn), heiti


class Fyrirtaekjaskra:
    """Fyrirtæki og stofnanir úr skránni, til að þekkja þau í vefskjölum.

    Vefskjöl nefna fyrirtæki í eignarfalli ("Landsvirkjunar", "Norðurorku
    hf"), svo borið er saman við stofn heitisins en ekki heitið allt.
    """

    def __init__(self, nofn, stettarfelog=()):
        # Stéttarfélög rata stundum í reit atvinnurekanda í skránni. Þau eru
        # ekki mótaðilar og mega ekki þekkjast sem fyrirtæki í vefskjölum.
        felagsstofnar = {s for s in (self._stofn(n) for n in stettarfelog) if len(s) >= 5}
        self.stofnar = []
        for nafn in set(nofn):
            if thekktur(nafn) or not (nafn or "").strip():
                continue
            stofn = self._stofn(nafn)
            er_felag = any(stofn.startswith(f) or f.startswith(stofn)
                           for f in felagsstofnar)
            if len(stofn) >= 5 and not er_felag:
                self.stofnar.append((stofn, fyrirtaeki_audkenni(nafn), ur_skra(nafn)[1]))
        # Lengri stofnar fyrst, svo "landsnet" vinni ekki "landsvirkjun" o.s.frv.
        self.stofnar.sort(key=lambda x: -len(x[0]))

    @staticmethod
    def _stofn(nafn: str) -> str:
        fyrsta = _ascii(_LAGAFORM.sub("", nafn or "")).split()
        if not fyrsta:
            return ""
        ord_ = re.sub(r"[^a-z0-9]", "", fyrsta[0])
        return ord_ if len(ord_) < 6 else ord_[:-1]

    def leita(self, texti: str):
        a = " " + re.sub(r"[^a-z0-9]+", " ", _ascii(texti)) + " "
        for stofn, audkenni, heiti in self.stofnar:
            if f" {stofn}" in a:
                return audkenni, heiti
        return None


def ur_vefskjali(adili_1: str, adili_2: str, skjal: str,
                 fyrirtaeki: Fyrirtaekjaskra | None = None,
                 vefur: str = "") -> tuple[str, str]:
    """(auðkenni, heiti) mótaðila vefskjals, eða óþekktur.

    Aðilareitirnir ganga fyrir skráarheitinu: þeir eru lesnir úr
    inngangsorðum samningsins, en skráarheitið nefnir stundum bæði
    samtök og félag ("kjarasamningur-sgs-og-sambands-islenskra-sveitarfelaga").
    """
    for texti in (adili_1, adili_2, skjal.rsplit("/", 1)[-1] if skjal else ""):
        a = thekktur(texti)
        if a:
            return a, HEITI[a]
    if fyrirtaeki:
        for texti in (adili_1, adili_2, skjal.rsplit("/", 1)[-1] if skjal else ""):
            f = fyrirtaeki.leita(texti or "")
            if f:
                return f
    if vefur in VEFIR_MOTADILA:
        a = VEFIR_MOTADILA[vefur]
        return a, HEITI[a]
    return OTHEKKTUR, HEITI[OTHEKKTUR]
