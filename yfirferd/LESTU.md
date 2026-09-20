# Yfirferð á eyðum

Eyða þýðir að langt líður milli skráðra hækkana hjá félagi. Tvennt getur
valdið því og vélin getur ekki greint þar á milli:

- **Hækkun vantar** í gögnin — samningur fannst ekki, OCR mistókst, eða
  útdrátturinn missti af ákvæðinu.
- **Félagið samdi ekki** á tímabilinu — eyðan er rétt og engu þarf að breyta.

## Skrárnar

| Skrá | Til hvers |
|---|---|
| `eydur.md` | til að skanna hratt, ein tafla á hvert félag |
| `eydur.csv` | **skráin sem þú fyllir út** |

## Hvernig þú fyllir út

Fremstu sjö dálkarnir eru auðir og ætlaðir þér. Hinir eru samhengi.

| Dálkur | Hvað á að setja |
|---|---|
| `stada` | `vantar` ef hækkun vantar · `rétt` ef engin hækkun var · `óvíst` |
| `dagsetning` | gildistökudagur hækkunarinnar, á forminu `2025-01-01` |
| `prosenta` | t.d. `3,5` — auður reitur ef aðeins var samið um krónutölu |
| `kronur` | t.d. `23750` |
| `a_vid` | `almenn laun`, `kauptaxtar`, `launatafla`, `lágmarkstekjur`, `byrjunarlaun` eða `óskilgreint` |
| `heimild` | slóð eða skjalsheiti, svo hægt sé að sannreyna |
| `athugasemd` | frjáls texti |

Vanti fleiri en eina hækkun í sömu eyðu: afritaðu línuna og fylltu út aftur.
Línur sem eru látnar standa auðar eru einfaldlega ekki yfirfarnar enn.

### Samhengisdálkarnir

`haekkun_a_undan` og `haekkun_a_eftir` sýna hvað var skráð sitt hvorum megin
við eyðuna. `algengt_hja_odrum` sýnir hvað **önnur félög** sömdu um á sama
tímabili — íslenskir kjarasamningar fylgjast að, svo sjáist að tugir félaga
hækkuðu um 3,50% þann 1. janúar 2025 en ekkert sé skráð hjá þessu félagi er
líklegt að hækkun vanti. Það er vísbending en ekki sönnun.

## Þegar þú ert búin(n)

```bash
python scripts/nota_leidrettingar.py --kanna   # sýnir hvað yrði fest
python scripts/nota_leidrettingar.py           # festir
python scripts/sameina.py
python scripts/launathroun.py
python scripts/byggja_api.py
```

Leiðréttingarnar fara í `gogn/handvirkar_leidrettingar.csv` og lifa þannig af
endurkeyrslu útdráttarins. Þær bera `uppruni = handvirk leiðrétting` í
gagnasettinu, svo alltaf sé ljóst hvað var vélrænt lesið og hvað lagfært.
