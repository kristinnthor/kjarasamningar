# Kjarasamningar – gagnasett um launahækkanir á Íslandi

Markmið: gagnasett sem heldur utan um allar umsamdar launahækkanir samkvæmt
kjarasamningum á Íslandi, helst aftur til 1990.

Verkefnið er í þremur áföngum:

1. **Söfnun frumgagna** – sækja kjarasamninga á því formi sem þeir eru til,
   aðallega PDF. *Lokið.*
2. **Útdráttur** – lesa launaliðinn úr textanum: umsamdar hækkanir (prósentur og
   krónutölur) og launatöflur (fjárhæðir á launaflokk og þrep).
3. **Gagnasett og API** – gagnasett á aðgengilegu formi þar sem skoða má
   launaþróun yfir tíma eftir stéttarfélagi, síðar birt gegnum API svo nota megi
   það í skýrslugerð með öðrum gögnum.

## Hvað er geymt hér

Þetta geymsluhólf inniheldur **forritin og gagnasettið, ekki sóttu skjölin**.
Mappan `samningar/` er undanskilin í `.gitignore`; forritin í `scripts/` sækja
hana aftur frá upprunaheimildunum þegar þarf. Ástæðan er stærð (um 7 GB) og að
frumskjölin eiga sér þegar opinberan samastað hjá útgefendum sínum.

## Prófaðu gögnin

```bash
pip install matplotlib requests
python daemi/graf.py                          # fjögur félög með samfellda röð
python daemi/graf.py samidnar                 # eitt félag, með viðmiði Hagstofunnar
python daemi/graf.py vr efling sgs --grunnur 2019-04   # sami grunnur, samanburðarhæft
python daemi/graf.py --listi                  # öll fáanleg auðkenni
python daemi/graf.py vr --vista graf.png      # vista í skrá
```

Án `--grunnur` hefst hver röð í 100 við **sína eigin** fyrstu mælingu. Það sýnir
heildarþróun hvers félags en gerir þau ekki samanburðarhæf innbyrðis, því þau
byrja á ólíkum tíma. Með `--grunnur ÁÁÁÁ[-MM[-DD]]` eru allar raðir settar á 100
sama dag - og þá fyrst er samanburður gildur, líka við launavísitölu
Hagstofunnar. Félög sem hafa enga mælingu fyrir grunndaginn falla út með
skýringu, því ekki er hægt að endurgrunna þau án þess að giska.

Forritið sækir allt yfir netið af API-inu - ekkert af gögnunum er innbyggt í
það. Sjá [docs/index.html](https://kristinnthor.github.io/kjarasamningar/) fyrir
endapunktana og [sýnidæmi í vafra](https://kristinnthor.github.io/kjarasamningar/demo.html).

---

## Áfangi 1: söfnun

### Heimildir

| Kóði | Heimild | Aðferð |
|---|---|---|
| `rikissattasemjari` | Ríkissáttasemjari, [kjarasamningar.is](https://www.kjarasamningar.is/) | REST API |
| `sa` | [Samtök atvinnulífsins](https://sa.is/vinnumarkadsvefur/kjarasamningar) | vefskrið |
| `vr`, `sgs`, `efling`, `afl`, o.fl. | stéttarfélög | vefskrið |
| `asi`, `rafis`, `vm`, `samidn`, `grafia`, `matvis`, `ssf`, `framsyn`, `verkvest`, `liv` | stéttarfélög á WordPress | `wp-json` API |

**Ríkissáttasemjari er kjarnaheimildin.** Samkvæmt lögum nr. 80/1938 ber að senda
honum afrit af öllum kjarasamningum, og hann birtir þá í gagnagrunni ásamt
lýsigögnum (aðilar, kennitölur, gildistími, markaður, heildarsamtök) og
OCR-texta. Vefir stéttarfélaganna eru viðbót – þeir fylla upp í eyður og geyma
oft launatöflur og sérkjarasamninga sem ekki rata í skrána.

### Uppbygging möppu

```
samningar/
  _skra.csv                     lýsigögn um skjöl sem sótt voru með vefskriði
  _skra_wp.csv                  lýsigögn um skjöl sótt gegnum wp-json
  _villur.csv                   slóðir sem mistókst að sækja
  rikissattasemjari/
    lysigogn.json               öll lýsigögn úr API-inu, óbreytt
    lysigogn.csv                sama á töfluformi
    pdf/                        PDF-skjöl samninganna
    ocr_texti/                  OCR-texti samninganna (úr API-inu)
  sa/ vr/ sgs/ asi/ ...         PDF-skjöl eftir heimildum
```

### Keyrsla

```bash
python scripts/saekja_rikissattasemjara.py --texti --pdf
python scripts/saekja_samninga.py
python scripts/saekja_wp.py
```

Öll forritin eru endurræsanleg: þau sleppa því sem þegar er til, bera saman
SHA-256 til að forðast tvítök og skrá villur sérstaklega.

Til að skoða hvað fyndist án þess að sækja:

```bash
python scripts/saekja_samninga.py --kanna sa
python scripts/saekja_wp.py --kanna asi
```

---

## Athugasemd um tímabilið 1990–2005

Gagnagrunnur ríkissáttasemjara nær aftur til 1947 en er misþéttur:

| Tímabil | Fjöldi samninga í skránni |
|---|---|
| 1974–1989 | ~80 |
| 1990–1999 | ~66 |
| 2000–2009 | ~240 |
| 2010–2019 | ~620 |
| 2020– | ~545 |

Fyrir 10. áratuginn eru skjölin því of gisin til að hægt sé að byggja heildstæða
röð launahækkana eingöngu á þeim. Til að ná markmiðinu um 1990 þarf að bæta við:

- **Launavísitölu Hagstofunnar** (mánaðarleg frá janúar 1989) – mælir raunverulega
  launaþróun, ekki umsamdar hækkanir, en er samfelld.
- **Skýrslum kjaratölfræðinefndar** ([ktn.is](https://www.ktn.is/gagnasafn-og-fleira))
  – Excel-gögn um launaþróun eftir mörkuðum, en aðeins frá um 2019.
- **Tímarit.is** – samningar og yfirlit birt í dagblöðum og félagsritum.
- **Alþingisskjölum** – ýmis lög tengd kjarasamningum, t.d. þjóðarsáttinni 1990.

### Ákveðið

- **Launatöflur fylgja með.** Gagnasettið nær bæði yfir umsamdar hækkanir og
  raunverulegar taxtafjárhæðir úr launatöflum samninganna, svo lesa megi bæði
  breytingu og launastig.
- **Launavísitala Hagstofunnar kemur inn sem sjálfstæð röð** við hliðina á
  samningsgögnunum, til að brúa 10. áratuginn. Hún mælir raunlaunaþróun en ekki
  umsamdar hækkanir, og verður aðgreind sem slík í gagnasettinu.
