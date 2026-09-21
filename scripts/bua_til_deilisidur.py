# -*- coding: utf-8 -*-
"""Býr til deilisíðu og deilimynd fyrir hvert félag.

Facebook, X og LinkedIn keyra ekki JavaScript þegar þau sækja forskoðun á
tengli - þau lesa aðeins og:-merkin í HTML-skránni. Samanburðarsíðan er
kyrrstæð og því getur hún ekki breytt merkjunum eftir því hvað er valið.

Lausnin er ein föst síða á félag, docs/deila/<audkenni>.html, með eigin
og:-merkjum og mynd (1200×630) sem sýnir samfelldu röðina og launavísitölu
Hagstofunnar yfir sama tímabil. Síðan vísar vafranum áfram á
samanburðarsíðuna með félagið valið, en samfélagsmiðlarnir sjá merkin.

Notkun (eftir byggja_api.py, les aðeins docs/api/v1):
    python scripts/bua_til_deilisidur.py
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import sys
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = os.path.join(ROT, "docs", "api", "v1")
UT = os.path.join(ROT, "docs", "deila")
VEFUR = "https://kristinnthor.github.io/kjarasamningar"

BG, TEXTI, TEXTI2, TEXTI3, LINA = "#fbfaf8", "#0b0b0b", "#52514e", "#86847e", "#e2ded8"
AKSER, ROD, VIDMID = "#7a4f2c", "#2a78d6", "#8d8b82"


def prosenta(x: float) -> str:
    return (f"{x:+.1f}%").replace(".", ",").replace("-", "−")


def hagstofa():
    with open(os.path.join(API, "launavisitala", "launavisitala_manadarleg.json"),
              encoding="utf-8") as f:
        gildi = json.load(f)["gildi"]
    rod = sorted((date(int(g["Mánuður"][:4]), int(g["Mánuður"][5:]), 1), float(g["gildi"]))
                 for g in gildi if g["Eining"] == "Vísitölugildi")
    return rod


def gildi_vid(rod, d):
    """Síðasta gildi á eða fyrir d (þrepafall)."""
    fyrir = [v for t, v in rod if t <= d]
    return fyrir[-1] if fyrir else None


def ein_sida(felag, hag, idag):
    punktar = [(date.fromisoformat(h["dagsetning"]), h["visitala_samfella"])
               for h in felag["haekkanir"]
               if h.get("innan_samfellu") and h.get("visitala_samfella")
               # Aldrei lengra en til loka yfirstandandi árs: umsamdar
               # hækkanir fram í tímann eru ekki samanburðarhæfar
               and h["dagsetning"] <= f"{date.today().year}-12-31"]
    if len(punktar) < 2:
        return None
    punktar.sort()
    upphaf, lok = punktar[0][0], punktar[-1][0]

    # Samanburður við Hagstofuna nær aðeins eins langt og hún mælir;
    # umsamdar hækkanir fram í tímann eru sýndar á myndinni en ekki bornar saman
    hag_lok = hag[-1][0]
    samanb_lok = min(lok, hag_lok)
    felag_samanb = gildi_vid(punktar, samanb_lok) / punktar[0][1] * 100 - 100
    h0, h1 = gildi_vid(hag, upphaf), gildi_vid(hag, samanb_lok)
    hag_breyting = (h1 / h0 * 100 - 100) if h0 and h1 else None
    heild = punktar[-1][1] / punktar[0][1] * 100 - 100

    nafn = felag["felag"]
    titill = f"{nafn}: umsamdar launahækkanir {upphaf.year}–{lok.year}"
    lysing = f"Umsamdar hækkanir {upphaf.year}–{samanb_lok.year}: {prosenta(felag_samanb)}."
    if hag_breyting is not None:
        lysing += f" Launavísitala Hagstofunnar sama tímabil: {prosenta(hag_breyting)}."
    if lok > hag_lok:
        lysing += f" Samið hefur verið um hækkanir til {lok.year}."

    # ---- Mynd 1200×630 ----
    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
    fig.patches.append(FancyBboxPatch((0.035, 0.885), 0.028, 0.053, boxstyle="round,pad=0,rounding_size=0.006",
                                      transform=fig.transFigure, facecolor=AKSER, edgecolor="none"))
    fig.lines.append(plt.Line2D([0.040, 0.047, 0.047, 0.054, 0.054, 0.058],
                                [0.897, 0.897, 0.910, 0.910, 0.924, 0.924],
                                transform=fig.transFigure, color="#f7f0e6", linewidth=2.2,
                                solid_capstyle="round", solid_joinstyle="round"))
    fig.text(0.072, 0.905, "Kjarasamningar", fontsize=13, color=TEXTI2, va="center")
    fig.text(0.035, 0.80, nafn if len(nafn) <= 48 else nafn[:46] + "…",
             fontsize=25, fontweight="bold", color=TEXTI, va="center")
    fig.text(0.035, 0.735, f"Umsamdar launahækkanir, keðjuð vísitala (100 = {upphaf.isoformat()})",
             fontsize=13, color=TEXTI2, va="center")

    ax = fig.add_axes([0.06, 0.12, 0.60, 0.55], facecolor=BG)
    x = [p[0] for p in punktar]
    y = [p[1] for p in punktar]
    if h0:
        hx = [t for t, _ in hag if upphaf <= t <= lok]
        hy = [v / h0 * 100 for t, v in hag if upphaf <= t <= lok]
        ax.plot(hx, hy, color=VIDMID, linewidth=2, linestyle=(0, (4, 3)), zorder=2)
    # Síðasta þrepið þarf breidd til að sjást, annars endar línan undir punktinum
    from datetime import timedelta
    ax.step(x + [lok + timedelta(days=45)], y + [y[-1]], where="post",
            color=ROD, linewidth=2.6, zorder=3)
    ax.plot(x[-1], y[-1], "o", color=ROD, markersize=8, markeredgecolor=BG, markeredgewidth=2, zorder=4)
    ax.axhline(100, color=LINA, linewidth=1, zorder=1)
    ax.grid(axis="y", color=LINA, linewidth=0.8)
    ax.set_axisbelow(True)
    for hlid in ("top", "right", "left"):
        ax.spines[hlid].set_visible(False)
    ax.spines["bottom"].set_color(LINA)
    ax.tick_params(colors=TEXTI3, labelsize=11, length=0)
    ar = max(1, (lok.year - upphaf.year) // 6)
    ax.xaxis.set_major_locator(mdates.YearLocator(base=ar))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.margins(x=0.02)

    # Lykiltölur hægra megin
    fig.text(0.70, 0.62, "Umsamdar hækkanir", fontsize=13, color=TEXTI2)
    fig.text(0.70, 0.535, prosenta(felag_samanb), fontsize=34, fontweight="bold", color=ROD)
    fig.text(0.70, 0.485, f"{upphaf.year}–{samanb_lok.year}", fontsize=12, color=TEXTI3)
    if hag_breyting is not None:
        fig.text(0.70, 0.37, "Launavísitala Hagstofunnar", fontsize=13, color=TEXTI2)
        fig.text(0.70, 0.285, prosenta(hag_breyting), fontsize=34, fontweight="bold", color=VIDMID)
        fig.text(0.70, 0.235, "sama tímabil", fontsize=12, color=TEXTI3)
    if lok > hag_lok:
        fig.text(0.70, 0.12, f"Með umsömdum hækkunum\ntil {lok.year}: {prosenta(heild)}",
                 fontsize=12, color=TEXTI2, linespacing=1.4)
    fig.text(0.035, 0.035, "kristinnthor.github.io/kjarasamningar · umsamdar hækkanir, ekki mæld launaþróun",
             fontsize=10.5, color=TEXTI3)
    if h0:
        fig.text(0.965, 0.035, "Launavísitala: Hagstofa Íslands", fontsize=10.5,
                 color=TEXTI3, ha="right")

    a = felag["audkenni"]
    myndslod = os.path.join(UT, f"{a}.png")
    fig.savefig(myndslod, dpi=100, facecolor=BG, metadata={"Software": None})
    plt.close(fig)
    # Útgáfunúmer myndar af innihaldi hennar: miðlar geyma forskoðun lengi, og
    # ný slóð þegar myndin breytist knýr fram nýja - en engin breyting annars.
    with open(myndslod, "rb") as f:
        utgafa = hashlib.sha1(f.read()).hexdigest()[:10]

    markmid = f"../skyrsla.html?felog={a}&hagstofa=1"
    e = html.escape
    sida = f"""<!DOCTYPE html>
<html lang="is">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(titill)}</title>
<meta name="description" content="{e(lysing)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Kjarasamningar">
<meta property="og:title" content="{e(titill)}">
<meta property="og:description" content="{e(lysing)}">
<meta property="og:url" content="{VEFUR}/deila/{a}.html">
<meta property="og:image" content="{VEFUR}/deila/{a}.png?v={utgafa}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(lysing)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(titill)}">
<meta name="twitter:description" content="{e(lysing)}">
<meta name="twitter:image" content="{VEFUR}/deila/{a}.png?v={utgafa}">
<link rel="icon" href="../favicon.svg" type="image/svg+xml">
<style>body{{font:16px/1.6 system-ui,sans-serif;background:{BG};color:{TEXTI};max-width:640px;margin:48px auto;padding:0 16px}}a{{color:{AKSER}}}img{{max-width:100%;border:1px solid {LINA};border-radius:8px}}</style>
</head>
<body>
<h1>{e(nafn)}</h1>
<p>{e(lysing)}</p>
<p><img src="{a}.png" alt="{e(lysing)}"></p>
<p><a href="{e(markmid)}">Opna gagnvirka grafið</a></p>
<script>location.replace({json.dumps(markmid)});</script>
</body>
</html>
"""
    # Samfélagsmiðlar keyra ekki JavaScript, svo þeir sjá merkin hér að ofan;
    # fólk fer beint á grafið. Engin meta refresh - sumir miðlar fylgja henni.
    with open(os.path.join(UT, f"{a}.html"), "w", encoding="utf-8") as f:
        f.write(sida)
    return a


def main():
    os.makedirs(UT, exist_ok=True)
    with open(os.path.join(API, "felog.json"), encoding="utf-8") as f:
        felog = json.load(f)["felog"]
    hag = hagstofa()
    idag = date.today().isoformat()
    gerdar = []
    for x in felog:
        with open(os.path.join(API, "felog", f"{x['audkenni']}.json"), encoding="utf-8") as f:
            felag = json.load(f)
        if ein_sida(felag, hag, idag):
            gerdar.append(x["audkenni"])
    # Síður félaga sem eiga ekki lengur nothæfa röð eru fjarlægðar
    for n in os.listdir(UT):
        if n != "index.json" and os.path.splitext(n)[0] not in gerdar:
            os.remove(os.path.join(UT, n))
    # Listi sem samanburðarsíðan les til að vita hvaða félög eiga deilisíðu
    with open(os.path.join(UT, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"felog": gerdar}, f)
    staerd = sum(os.path.getsize(os.path.join(UT, n)) for n in os.listdir(UT))
    print(f"Deilisíður: {len(gerdar)} af {len(felog)} félögum ({staerd / 1e6:.1f} MB) í {UT}")


if __name__ == "__main__":
    main()
