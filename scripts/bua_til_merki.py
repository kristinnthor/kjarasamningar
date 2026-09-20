# -*- coding: utf-8 -*-
"""Teiknar merki verkefnisins í þeim skráarsniðum sem vafrar og símar þurfa.

Merkið er þrepalína. Hún er ekki skraut heldur lýsing: laun hækka ekki jafnt
og þétt heldur í stökkum þegar samningar taka gildi, og vísitalan teiknar
nákvæmlega þetta form.

Teiknað er í fjórfaldri upplausn og minnkað með LANCZOS, því þrepalínan verður
kubbótt ef hún er teiknuð beint í 16 díla.

Notkun:
    python scripts/bua_til_merki.py
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROT, "docs")

BAKGRUNNUR = (122, 79, 44, 255)     # #7a4f2c - sami litur og áherslulitur vefsins
LINA = (247, 240, 230, 255)         # #f7f0e6

# Þrepin í 32x32 hnitakerfi, sömu og í favicon.svg. Þau eru þrjú en ekki
# fleiri: við 16 díla renna fjögur þrep saman í óskiljanlegt krot.
THREP = [(5, 25), (13, 25), (13, 18), (21, 18), (21, 11), (27, 11)]
LINUBREIDD = 4.0


def teikna(staerd: int, gegnsaett_bak: bool = False) -> Image.Image:
    yfir = 4                                  # yfirupplausn
    s = staerd * yfir
    mynd = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(mynd)

    kvardi = s / 32
    if not gegnsaett_bak:
        radius = int(7 * kvardi)
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=BAKGRUNNUR)

    punktar = [(x * kvardi, y * kvardi) for x, y in THREP]
    breidd = max(2, int(LINUBREIDD * kvardi))
    d.line(punktar, fill=LINA, width=breidd, joint="curve")
    # Ávalir endar - ImageDraw.line skilar beinum endum
    r = breidd / 2
    for x, y in (punktar[0], punktar[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=LINA)

    return mynd.resize((staerd, staerd), Image.LANCZOS)


def leturgerd(staerd: int, feitt: bool = False):
    """Finnur nothæfa leturgerð. Myndin er teiknuð hér og vistuð sem PNG,
    svo letrið þarf aðeins að vera til á þeirri vél sem keyrir forritið."""
    fyrir = ["segoeuib.ttf" if feitt else "segoeui.ttf",
             "arialbd.ttf" if feitt else "arial.ttf",
             "DejaVuSans-Bold.ttf" if feitt else "DejaVuSans.ttf"]
    for nafn in fyrir:
        for mappa in (os.path.join(os.environ.get("WINDIR", ""), "Fonts"),
                      "/usr/share/fonts/truetype/dejavu", "."):
            leid = os.path.join(mappa, nafn)
            if os.path.exists(leid):
                try:
                    return ImageFont.truetype(leid, staerd)
                except OSError:
                    pass
    return ImageFont.load_default()


def deilimynd(breidd=1200, haed=630) -> Image.Image:
    """Mynd sem birtist þegar hlekk á vefinn er deilt."""
    mynd = Image.new("RGBA", (breidd, haed), (23, 22, 20, 255))
    d = ImageDraw.Draw(mynd)

    # Þrepalínan stór og dauf hægra megin, sem bakgrunnsform
    kvardi = haed / 32 * 1.05
    xoff = breidd - 32 * kvardi + 40
    yoff = (haed - 32 * kvardi) / 2
    punktar = [(xoff + x * kvardi, yoff + y * kvardi) for x, y in THREP]
    d.line(punktar, fill=(122, 79, 44, 255), width=int(LINUBREIDD * kvardi),
           joint="curve")

    # Merkið sjálft, lítið, efst til vinstri
    merki = teikna(84)
    mynd.alpha_composite(merki, (72, 96))

    d.text((72, 226), "Kjarasamningar", font=leturgerd(76, True),
           fill=(247, 240, 230, 255))
    d.text((72, 322), "Umsamdar launahækkanir á Íslandi",
           font=leturgerd(36), fill=(195, 194, 183, 255))
    d.text((72, 384), "1974–2028  ·  146 stéttarfélög  ·  opið API",
           font=leturgerd(30), fill=(141, 139, 130, 255))

    return mynd.convert("RGB")


def main():
    os.makedirs(DOCS, exist_ok=True)
    skrifad = []

    # ICO með mörgum stærðum - eldri vafrar velja sjálfir
    ico = os.path.join(DOCS, "favicon.ico")
    teikna(64).save(ico, format="ICO",
                    sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    skrifad.append(ico)

    for staerd, nafn in ((180, "apple-touch-icon.png"),
                         (192, "icon-192.png"),
                         (512, "icon-512.png")):
        leid = os.path.join(DOCS, nafn)
        teikna(staerd).save(leid, format="PNG")
        skrifad.append(leid)

    deili = os.path.join(DOCS, "deilimynd.png")
    deilimynd().save(deili, format="PNG")
    skrifad.append(deili)

    for leid in skrifad:
        print(f"  {os.path.relpath(leid, ROT)}  "
              f"({os.path.getsize(leid) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
