# -*- coding: utf-8 -*-
"""Sækir gögnin af API-inu og teiknar launaþróun eftir stéttarfélagi.

Þetta er keyranlegt dæmi um notkun API-sins - ekkert af gögnunum er innbyggt
hér, allt er sótt yfir netið.

Uppsetning:
    pip install matplotlib requests

Notkun:
    python daemi/graf.py                       # fjögur félög með samfellda röð
    python daemi/graf.py vr samidnar efling    # tiltekin félög eftir auðkenni
    python daemi/graf.py --grunnur 2015        # allar raðir á sama grunn
    python daemi/graf.py vr --verdlag          # líka vísitala neysluverðs
    python daemi/graf.py --listi               # sýnir öll fáanleg auðkenni
    python daemi/graf.py --vista graf.png      # vistar í skrá í stað þess að birta

Án --grunnur hefst hver röð í 100 við sína eigin fyrstu mælingu, sem sýnir
heildarþróun hvers félags en gerir þau ekki samanburðarhæf innbyrðis. Með
--grunnur eru þær allar settar á 100 á sama degi, og þá er samanburður gildur
- líka við launavísitölu Hagstofunnar og, með --verdlag, vísitölu neysluverðs.
"""
from __future__ import annotations

import sys
from datetime import date

import requests
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

GRUNNUR = "https://kjarasamningar.kristinn.eu/api/v1"

# Litir í fastri röð. Þeir eru valdir svo aðgreining haldist fyrir
# litblindu og eru aldrei endurnýttir í hringi - fimmta félagið fær ekki
# aftur fyrsta litinn heldur er sleppt.
LITIR = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7", "#f50b3e", "#d14f9c", "#6b6660"]
VIDMID = "#9a948c"
VERDLAG = "#5c5a54"


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


def launavisitala():
    """Launavísitala Hagstofunnar sem (mánuður, gildi).

    Hún er höfð með sem viðmið því hún mælir aðra stærð: raunverulega
    launaþróun með launaskriði, ekki umsamdar hækkanir. Samningsraðirnar eiga
    því að liggja undir henni.
    """
    gogn = saekja("launavisitala/launavisitala_manadarleg.json")["gildi"]
    return sorted((g["Mánuður"], float(g["gildi"])) for g in gogn
                  if g["Eining"] == "Vísitölugildi")


def neysluverd():
    """Vísitala neysluverðs sem (mánuður, gildi).

    Hún mælir verðlag, ekki laun. Liggi félag ofan hennar hafa kauptaxtar
    hækkað umfram verðlag; liggi það undir henni hafa þeir rýrnað að raunvirði.
    """
    gogn = saekja("visitala_neysluverds.json")["gildi"]
    return sorted((g["Mánuður"], float(g["gildi"])) for g in gogn
                  if g["Vísitala"] == "Vísitala neysluverðs"
                  and g["Liður"] == "Vísitala")


def vidmid(rod, fra: str, til: str, grunndagur: date | None = None):
    """Mánaðarleg vísitala Hagstofunnar, endurgrunnuð á 100.

    Án `grunndagur` er grunnurinn fyrsti punktur tímabilsins; með honum er
    hann sá sami og raðirnar nota, svo allt sé samanburðarhæft.
    """
    innan = [(m, v) for m, v in rod
             if fra[:4] + "M" + fra[5:7] <= m <= til[:4] + "M" + til[5:7]]
    if not innan:
        return [], []
    if grunndagur is None:
        grunnur = innan[0][1]
    else:
        lykill = f"{grunndagur.year:04d}M{grunndagur.month:02d}"
        fyrir = [v for m, v in rod if m <= lykill]
        if not fyrir:
            return [], []
        grunnur = fyrir[-1]
    dagar = [date(int(m[:4]), int(m[5:]), 1) for m, _ in innan]
    return dagar, [v / grunnur * 100 for _, v in innan]


def lesa_grunndag(s: str) -> date:
    """Tekur við '2015', '2015-05' eða '2015-05-01'."""
    hlutar = s.split("-")
    try:
        ar = int(hlutar[0])
        man = int(hlutar[1]) if len(hlutar) > 1 else 1
        dagur = int(hlutar[2]) if len(hlutar) > 2 else 1
        return date(ar, man, dagur)
    except (ValueError, IndexError):
        sys.exit(f"Ólæsilegur grunndagur: {s!r}. Notaðu ÁÁÁÁ, ÁÁÁÁ-MM "
                 f"eða ÁÁÁÁ-MM-DD.")


def endurgrunna(punktar, grunndagur: date):
    """Færir tímaröð á 100 við `grunndagur`.

    Vísitalan er þrepafall - hún breytist aðeins þegar hækkun tekur gildi - svo
    gildið á grunndegi er síðasta mæling á undan honum. Röð sem hefst eftir
    grunndaginn er ekki hægt að endurgrunna án þess að giska á það sem á undan
    fór, og skilar því engu.
    """
    fyrir = [v for d, v in punktar if d <= grunndagur]
    if not fyrir:
        return None
    grunnur = fyrir[-1]
    if grunnur <= 0:
        return None
    eftir = [(d, v / grunnur * 100) for d, v in punktar if d > grunndagur]
    # Akkeri á grunndeginum sjálfum. Án þess hæfist línan við næstu hækkun á
    # eftir og virtist þá byrja yfir 100, þótt grunnurinn sé þar.
    return [(grunndagur, 100.0)] + eftir


def teikna(felog, vista=None, grunndagur=None, verdlag=False):
    radir = []
    for f in felog:
        gogn = saekja(f"felog/{f['audkenni']}.json")
        # Samfelldi hlutinn er notaður: keðjan yfir eyðu er einmitt sá hluti
        # sem ekki er treystandi. samfelld_fra segir hvenær hann hefst.
        # Aldrei lengra en til loka yfirstandandi árs: umsamdar hækkanir fram
        # í tímann eru ekki samanburðarhæfar milli félaga eða við Hagstofuna.
        lok = date(date.today().year, 12, 31)
        punktar = [(date.fromisoformat(h["dagsetning"]), h["visitala_samfella"])
                   for h in gogn["haekkanir"]
                   if h.get("innan_samfellu") and h.get("visitala_samfella")
                   and date.fromisoformat(h["dagsetning"]) <= lok]
        if len(punktar) <= 1:
            continue
        if grunndagur is not None:
            punktar = endurgrunna(punktar, grunndagur)
            if not punktar or len(punktar) < 2:
                print(f"  sleppi {gogn['felag']}: engin mæling fyrir "
                      f"{grunndagur.isoformat()}")
                continue
        radir.append((gogn["felag"], gogn["heilleiki"], punktar))

    if not radir:
        sys.exit("Engin nothæf tímaröð fannst.")

    fra = min(p[0] for _, _, ps in radir for p in ps).isoformat()
    til = max(p[0] for _, _, ps in radir for p in ps).isoformat()

    fig, ax = plt.subplots(figsize=(11, 5.5))

    # Viðmiðslínan á aðeins við þegar allar raðir deila grunni. Án --grunnur
    # er hver röð grunnuð á sinni eigin fyrstu mælingu, og þá getur ein
    # viðmiðslína ekki átt við fleiri en eina þeirra - hún myndi láta félag
    # með styttri sögu líta út fyrir að hafa dregist aftur úr. Viðmiðin
    # þekkjast á strikamynstri, ekki lit einum.
    vidmidin = [(launavisitala, "Launavísitala Hagstofunnar", VIDMID,
                 1.6, (0, (4, 3)))]
    if verdlag:
        vidmidin.append((neysluverd, "Vísitala neysluverðs", VERDLAG,
                         1.8, (0, (1, 2))))
    if grunndagur is None and len(radir) > 1:
        vidmidin = []
        print("Viðmiðslínum Hagstofunnar er sleppt: raðirnar hafa ekki sama "
              "grunn. Notaðu --grunnur ÁÁÁÁ til að setja þær á sama grunn.")
    for saekja_rod, heiti, litur, breidd, strik in vidmidin:
        if grunndagur is not None:
            hx, hy = vidmid(saekja_rod(), grunndagur.isoformat(), til, grunndagur)
        else:
            hx, hy = vidmid(saekja_rod(), radir[0][2][0][0].isoformat(), til)
        if hx:
            ax.plot(hx, hy, color=litur, linewidth=breidd, linestyle=strik,
                    label=f"{heiti} (viðmið)", zorder=1)

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
    if grunndagur is not None:
        ax.set_ylabel(f"Vísitala (100 = {grunndagur.isoformat()})", fontsize=9)
        ax.axhline(100, color="#e2ded8", linewidth=1)
    else:
        ax.set_ylabel("Vísitala (100 við upphaf samfellu hvers félags)",
                      fontsize=9)
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

    grunndagur = None
    if "--grunnur" in argv:
        i = argv.index("--grunnur")
        if i + 1 >= len(argv):
            sys.exit("--grunnur vantar dagsetningu, t.d. --grunnur 2015")
        grunndagur = lesa_grunndag(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]

    verdlag = "--verdlag" in argv
    argv = [a for a in argv if a != "--verdlag"]

    vista = None
    if "--vista" in argv:
        i = argv.index("--vista")
        vista = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
        matplotlib.use("Agg")

    audkenni = [a for a in argv if not a.startswith("--")]
    felog = velja_felog(audkenni)
    print("Sæki: " + ", ".join(f["felag"] for f in felog))
    teikna(felog, vista, grunndagur, verdlag)


if __name__ == "__main__":
    main(sys.argv[1:])
