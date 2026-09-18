# -*- coding: utf-8 -*-
"""Skriður um vefi stéttarfélaga og atvinnurekenda og sækir PDF-kjarasamninga.

Notkun:
    python scripts/saekja_samninga.py                 # allar heimildir
    python scripts/saekja_samninga.py sa vr sgs       # aðeins valdar heimildir
    python scripts/saekja_samninga.py --kanna sa      # aðeins kanna, ekkert sótt

Útkoma:
    samningar/<kodi>/<skjal>.pdf
    samningar/_skra.csv      - lýsigögn um hvert sótt skjal
    samningar/_villur.csv    - slóðir sem mistókst að sækja
"""
from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import sys
import time
import unicodedata
from collections import deque
from datetime import date
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heimildir import eftir_kodum  # noqa: E402

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMNINGAR = os.path.join(ROT, "samningar")
SKRA_CSV = os.path.join(SAMNINGAR, "_skra.csv")
VILLUR_CSV = os.path.join(SAMNINGAR, "_villur.csv")

HAUSAR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "is,en;q=0.8",
}

# Slóðir sem vert er að elta áfram innan vefjar
ELTA_ORD = (
    "kjarasamning", "kjaramal", "kjaramál", "samningur", "samningar",
    "kaup-kjor", "kaup-og-kjor", "launatafla", "launataxt", "launatoflur",
    "taxt", "eldri", "kjor", "kjör", "media", "skjol", "utgafa", "sidur",
    "vinnumarkadsvefur", "kauptaxt", "kaupgjald", "samthykkt", "bokun",
    "kaup-og-kjor", "mannaudsmal", "starfskjor", "fylgigogn", "library",
    "stofnanasamning", "adildarfelog", "felag-", "launatoflur", "riki",
)

# Skjöl sem eru augljóslega ekki kjarasamningar
SLEPPA_ORD = (
    "umsokn", "umsóknar", "eydublad", "eyðublað", "arsskyrsla", "ársskýrsla",
    "arsreikning", "ársreikning", "fundargerd", "fundargerð", "logreglusamthykkt",
    "personuvernd", "persónuvernd", "sjodfelagi", "styrktarsjod", "sjukrasjod",
    "sjúkrasjóð", "orlofs", "logbok", "lögbók", "samthykktir-felagsins",
)

MAX_SKJAL = 120 * 1024 * 1024  # 120 MB þak á stakt skjal

# Margir vefir (Next.js, Umbraco, Prismic o.fl.) fela skjalaslóðirnar inni í
# JSON-farmi síðunnar í stað þess að hafa þær í <a href>. Þetta nær þeim líka.
PDF_I_TEXTA = re.compile(
    r"""(?:https?://[^\s"'<>\\]+?|/[^\s"'<>\\]+?)\.pdf""", re.I)


def hreinsa_nafn(s: str, hamark: int = 130) -> str:
    """Búa til skráarheiti sem virkar á Windows en heldur íslenskum stöfum."""
    s = unquote(s)
    s = unicodedata.normalize("NFC", s)
    s = s.replace("+", " ")
    s = re.sub(r"[\\/:*?\"<>|\r\n\t]", "-", s)
    s = re.sub(r"\s+", " ", s).strip(" .-_")
    if len(s) > hamark:
        s = s[:hamark].rstrip(" .-_")
    return s or "skjal"


def er_pdf_slod(u: str, skjalamynstur=None) -> bool:
    p = urlparse(u).path.lower()
    if p.endswith(".pdf"):
        return True
    # Sumir vefir afhenda skjöl gegnum niðurhalsslóð án .pdf-endingar
    # (t.d. Blazor-vefur Sameykis: library/?itemid=<guid>)
    return bool(skjalamynstur and skjalamynstur.search(u))


def hostur_leyfdur(u: str, hostar) -> bool:
    h = (urlparse(u).netloc or "").lower()
    return any(x in h for x in hostar)


def vert_ad_elta(u: str) -> bool:
    lagt = u.lower()
    if any(lagt.endswith(e) for e in (".jpg", ".png", ".gif", ".svg", ".zip",
                                      ".docx", ".doc", ".xlsx", ".xls", ".mp4",
                                      ".css", ".js", ".ico", ".webp")):
        return False
    return any(o in lagt for o in ELTA_ORD)


def ma_sleppa(u: str, texti: str) -> bool:
    saman = (unquote(u) + " " + texti).lower()
    return any(o in saman for o in SLEPPA_ORD)


class Safnari:
    def __init__(self, kanna_adeins: bool = False):
        self.s = requests.Session()
        self.s.headers.update(HAUSAR)
        self.kanna_adeins = kanna_adeins
        self.skra: list[dict] = []
        self.villur: list[dict] = []
        self.sedir_hasar: set[str] = set()   # sha256 -> forðast tvítök
        self.sottar_slodir: set[str] = set()
        self._les_fyrri()

    # ---------------------------------------------------------------- #
    def _les_fyrri(self):
        """Lesa fyrri keyrslu svo hægt sé að halda áfram án tvítöku."""
        if os.path.exists(SKRA_CSV):
            with open(SKRA_CSV, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    self.skra.append(r)
                    self.sottar_slodir.add(r["slod"])
                    if r.get("sha256"):
                        self.sedir_hasar.add(r["sha256"])
            print(f"  (les {len(self.skra)} fyrri færslur úr _skra.csv)")

    def saekja_sidu(self, u: str):
        try:
            r = self.s.get(u, timeout=45, allow_redirects=True)
        except Exception as e:
            self.villur.append({"slod": u, "villa": f"{type(e).__name__}: {e}"})
            return None
        if r.status_code >= 400:
            self.villur.append({"slod": u, "villa": f"HTTP {r.status_code}"})
            return None
        ct = r.headers.get("Content-Type", "")
        if "html" not in ct.lower():
            return None
        return r

    # ---------------------------------------------------------------- #
    def skrida(self, h: dict):
        kodi, hostar, dypt = h["kodi"], h["hostar"], h["dypt"]
        skjalamynstur = re.compile(h["skjalamynstur"]) if h.get("skjalamynstur") else None
        mappa = os.path.join(SAMNINGAR, kodi)
        os.makedirs(mappa, exist_ok=True)

        heimsott: set[str] = set()
        pdf_fundin: dict[str, tuple[str, str]] = {}  # url -> (texti, fundið á síðu)
        bid = deque((u, 0) for u in h["byrjun"])

        while bid:
            u, d = bid.popleft()
            u = u.split("#")[0]
            if u in heimsott:
                continue
            heimsott.add(u)
            r = self.saekja_sidu(u)
            if r is None:
                continue
            sup = BeautifulSoup(r.text, "lxml")
            grunnur = r.url
            for a in sup.find_all("a", href=True):
                nyr = urljoin(grunnur, a["href"].strip()).split("#")[0]
                if not nyr.lower().startswith("http"):
                    continue
                texti = " ".join(a.get_text(" ", strip=True).split())
                if er_pdf_slod(nyr, skjalamynstur):
                    if hostur_leyfdur(nyr, hostar) and nyr not in pdf_fundin:
                        if not ma_sleppa(nyr, texti):
                            pdf_fundin[nyr] = (texti, u)
                elif d < dypt and hostur_leyfdur(nyr, hostar) and vert_ad_elta(nyr):
                    if nyr not in heimsott:
                        bid.append((nyr, d + 1))

            # Slóðir sem liggja í JSON-farmi síðunnar en ekki í <a href>
            for hrar in set(PDF_I_TEXTA.findall(r.text)):
                nyr = urljoin(grunnur, hrar.replace("\\/", "/")).split("#")[0]
                if (nyr not in pdf_fundin and hostur_leyfdur(nyr, hostar)
                        and not ma_sleppa(nyr, "")):
                    pdf_fundin[nyr] = ("", u)
            time.sleep(0.25)

        print(f"  {kodi}: {len(heimsott)} síður skoðaðar, {len(pdf_fundin)} PDF-slóðir fundnar")
        if self.kanna_adeins:
            for u, (t, _) in sorted(pdf_fundin.items()):
                print(f"     - {t[:70]!r} {u}")
            return

        nytt = 0
        for u, (texti, fundid_a) in sorted(pdf_fundin.items()):
            if u in self.sottar_slodir:
                continue
            if self.saekja_pdf(h, mappa, u, texti, fundid_a):
                nytt += 1
            time.sleep(0.25)
        print(f"  {kodi}: {nytt} ný skjöl sótt")

    # ---------------------------------------------------------------- #
    def saekja_pdf(self, h, mappa, u, texti, fundid_a) -> bool:
        try:
            r = self.s.get(u, timeout=120, stream=True)
            if r.status_code >= 400:
                self.villur.append({"slod": u, "villa": f"HTTP {r.status_code}"})
                return False
            buf = io.BytesIO()
            for hluti in r.iter_content(65536):
                buf.write(hluti)
                if buf.tell() > MAX_SKJAL:
                    self.villur.append({"slod": u, "villa": "of stórt skjal"})
                    return False
            gogn = buf.getvalue()
        except Exception as e:
            self.villur.append({"slod": u, "villa": f"{type(e).__name__}: {e}"})
            return False

        if not gogn.startswith(b"%PDF"):
            self.villur.append({"slod": u, "villa": "ekki gilt PDF"})
            return False

        sha = hashlib.sha256(gogn).hexdigest()
        if sha in self.sedir_hasar:
            self.sottar_slodir.add(u)
            return False

        stigur = urlparse(u).path
        if stigur.lower().endswith(".pdf"):
            grunnnafn = hreinsa_nafn(os.path.basename(stigur)[:-4])
        else:
            # slóð án .pdf - reyna að lesa heiti úr Content-Disposition
            cd = r.headers.get("Content-Disposition", "")
            m = re.search(r'filename\*?=(?:UTF-8'')?"?([^\";]+)', cd)
            heiti = m.group(1) if m else (texti or os.path.basename(stigur) or "skjal")
            grunnnafn = hreinsa_nafn(re.sub(r"\.pdf$", "", heiti, flags=re.I))
        skraarnafn = f"{grunnnafn}.pdf"
        leid = os.path.join(mappa, skraarnafn)
        i = 2
        while os.path.exists(leid):
            skraarnafn = f"{grunnnafn} ({i}).pdf"
            leid = os.path.join(mappa, skraarnafn)
            i += 1
        with open(leid, "wb") as f:
            f.write(gogn)

        self.sedir_hasar.add(sha)
        self.sottar_slodir.add(u)
        self.skra.append({
            "kodi": h["kodi"],
            "heimild": h["heiti"],
            "vettvangur": h["vettvangur"],
            "skra": os.path.relpath(leid, SAMNINGAR).replace("\\", "/"),
            "tengilstexti": texti,
            "slod": u,
            "fundid_a": fundid_a,
            "staerd_bæti": len(gogn),
            "sha256": sha,
            "sott": date.today().isoformat(),
        })
        return True

    # ---------------------------------------------------------------- #
    def vista_skrar(self):
        if self.kanna_adeins:
            return
        dalkar = ["kodi", "heimild", "vettvangur", "skra", "tengilstexti", "slod",
                  "fundid_a", "staerd_bæti", "sha256", "sott"]
        with open(SKRA_CSV, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=dalkar, extrasaction="ignore")
            w.writeheader()
            w.writerows(self.skra)
        if self.villur:
            with open(VILLUR_CSV, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["slod", "villa"])
                w.writeheader()
                w.writerows(self.villur)


def main(argv):
    kanna = "--kanna" in argv
    kodar = [a for a in argv if not a.startswith("--")]
    os.makedirs(SAMNINGAR, exist_ok=True)
    heimildir = eftir_kodum(kodar)
    print(f"Sæki úr {len(heimildir)} heimildum"
          f"{' (aðeins könnun)' if kanna else ''}\n")
    safnari = Safnari(kanna_adeins=kanna)
    for h in heimildir:
        print(f"[{h['kodi']}] {h['heiti']}")
        try:
            safnari.skrida(h)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"  !! {type(e).__name__}: {e}")
        safnari.vista_skrar()
    safnari.vista_skrar()
    print(f"\nSamtals í skrá: {len(safnari.skra)} skjöl, {len(safnari.villur)} villur")


if __name__ == "__main__":
    main(sys.argv[1:])
