# -*- coding: utf-8 -*-
"""Sækir gögnin af API-inu og teiknar launaþróun eftir stéttarfélagi.

Þetta er keyranlegt dæmi um notkun API-sins - ekkert af gögnunum er innbyggt
hér, allt er sótt yfir netið.

Uppsetning:
    pip install matplotlib requests

Notkun:
    python daemi/graf.py                      # fjögur félög með samfellda röð
    python daemi/graf.py vr samidnar efling   # tiltekin félög eftir auðkenni
    python daemi/graf.py --listi              # sýnir öll fáanleg auðkenni
    python daemi/graf.py --vista graf.png     # vistar í skrá í stað þess að birta
"""
from __future__ import annotations

import sys
from datetime import date

import requests
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

GRUNNUR = "https://kristinnthor.github.io/kjarasamningar/api/v1"

# Litir í fastri röð. Þeir eru valdir svo aðgreining haldist fyrir
# litblindu og eru aldrei endurnýttir í hringi - fimmta félagið fær ekki
# aftur fyrsta litinn heldur er sleppt.
LITIR = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"]
VIDMID = "#9a948c"


def saekja(slod: str):
    svar = requests.get(f"{GRUNNUR}/{slod}", timeout=30)
    svar.raise_for_status()
    return svar.json()


def velja_felog(audkenni: list[str]):
    """Skilar félögum. Án röksemda: fjögur með lengstu samfelldu röðina."""
    felog = saekja("felog.json")["felog"]
    if audkenni:
        eftir_audkenni = {f["audkenni"]: f for f in felog}
        vantar = [a for a in audkenni if a not in eftir_audkenni]
        if vantar:
            sys.exit(f"Óþekkt auðkenni: {', '.join(vantar)}\n"
                     f"Keyrðu með --listi til að sjá hvað er í boði.")
        return [eftir_audkenni[a] for a in audkenni]
    samfelld = [f for f in felog if f["heilleiki"] == "samfelld"]
    samfelld.sort(key=lambda f: -f["fjoldi_haekkana"])
    return samfelld[:4]


def hagstofan(fra: str, til: str):
    """Launavísitala Hagstofunnar, endurgrunnuð á sama upphafspunkt.

    Hún er höfð með sem viðmið því hún mælir aðra stærð: raunverulega
    launaþróun með launaskriði, ekki umsamdar hækkanir. Samningsraðirnar eiga
    því að liggja undir henni.
    """
    gogn = saekja("launavisitala/launavisitala_manadarleg.json")["gildi"]
    rod = [(g["Mánuður"], float(g["gildi"])) for g in gogn
           if g["Eining"] == "Vísitölugildi"]
    rod.sort()
    innan = [(m, v) for m, v in rod
             if fra[:4] + "M" + fra[5:7] <= m <= til[:4] + "M" + til[5:7]]
    if not innan:
        return [], []
    grunnur = innan[0][1]
    dagar = [date(int(m[:4]), int(m[5:]), 1) for m, _ in innan]
    gildi = [v / grunnur * 100 for _, v in innan]
    return dagar, gildi


def teikna(felog, vista=None):
    radir = []
    for f in felog:
        gogn = saekja(f"felog/{f['audkenni']}.json")
        punktar = [(date.fromisoformat(h["dagsetning"]), h["visitala"])
                   for h in gogn["haekkanir"] if h["visitala"] is not None]
        if len(punktar) > 1:
            radir.append((gogn["felag"], gogn["heilleiki"], punktar))

    if not radir:
        sys.exit("Engin nothæf tímaröð fannst.")

    fra = min(p[0] for _, _, ps in radir for p in ps).isoformat()
    til = max(p[0] for _, _, ps in radir for p in ps).isoformat()

    fig, ax = plt.subplots(figsize=(11, 5.5))

    # Viðmiðslínan er aðeins dregin þegar eitt félag er sýnt. Hver röð er
    # grunnuð á 100 við sína eigin fyrstu mælingu, svo ein viðmiðslína getur
    # ekki átt við fleiri en eina þeirra - hún myndi láta félag sem hefur
    # styttri sögu líta út fyrir að hafa dregist aftur úr.
    if len(radir) == 1:
        hx, hy = hagstofan(radir[0][2][0][0].isoformat(), til)
        if hx:
            ax.plot(hx, hy, color=VIDMID, linewidth=1.6, linestyle=(0, (4, 3)),
                    label="Launavísitala Hagstofunnar (viðmið)", zorder=1)
    else:
        print("Viðmiðslína Hagstofunnar er sleppt: hún á aðeins við eitt félag "
              "í senn, því hver röð er grunnuð á sinni eigin fyrstu mælingu.")

    for i, (heiti, heilleiki, punktar) in enumerate(radir):
        litur = LITIR[i % len(LITIR)]
        x = [p[0] for p in punktar]
        y = [p[1] for p in punktar]
        merki = heiti if heilleiki == "samfelld" else f"{heiti} ({heilleiki})"
        ax.plot(x, y, color=litur, linewidth=2, solid_joinstyle="round",
                label=merki, zorder=3)
        # Bein merking við enda línunnar, svo auðkenni ráðist ekki af lit einum
        ax.annotate(f" {y[-1]:,.0f}".replace(",", "."), (x[-1], y[-1]),
                    color=litur, fontsize=9, fontweight="bold",
                    va="center", ha="left", zorder=4)
        ax.plot(x[-1], y[-1], "o", color=litur, markersize=6,
                markeredgecolor="white", markeredgewidth=1.5, zorder=4)

    ax.set_title("Umsamdar launahækkanir, keðjuð vísitala",
                 fontsize=13, loc="left", pad=14)
    ax.set_ylabel("Vísitala (100 við fyrstu mælingu)", fontsize=9)
    ax.xaxis.set_major_locator(mdates.YearLocator(base=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(axis="y", color="#e2ded8", linewidth=0.8)
    ax.set_axisbelow(True)
    for hlid in ("top", "right", "left"):
        ax.spines[hlid].set_visible(False)
    ax.spines["bottom"].set_color("#e2ded8")
    ax.tick_params(colors="#6b6660", labelsize=9, length=0)
    ax.margins(x=0.06)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    fig.tight_layout()

    if vista:
        fig.savefig(vista, dpi=160, bbox_inches="tight")
        print(f"Vistað í {vista}")
    else:
        plt.show()


def main(argv):
    if "--listi" in argv:
        for f in saekja("felog.json")["felog"]:
            print(f"{f['audkenni']:<42} {f['fjoldi_haekkana']:>3} hækkanir  "
                  f"{f['fyrsta']}–{f['sidasta']}  {f['heilleiki']}")
        return

    vista = None
    if "--vista" in argv:
        i = argv.index("--vista")
        vista = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
        matplotlib.use("Agg")

    audkenni = [a for a in argv if not a.startswith("--")]
    felog = velja_felog(audkenni)
    print("Sæki: " + ", ".join(f["felag"] for f in felog))
    teikna(felog, vista)


if __name__ == "__main__":
    main(sys.argv[1:])
