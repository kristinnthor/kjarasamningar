# Gagnasett

Þrjú lög: hráar hækkanir úr samningum, tímaröð eftir stéttarfélagi, og
launavísitala Hagstofunnar sem sjálfstætt viðmið.

| Skrá | Inntak |
|---|---|
| `haekkanir.csv` | ein lína á hverja umsamda hækkun sem fannst í samningi |
| `haekkanir_vefskjol.csv` | sama úr PDF-um af vefjum félaganna, með veikari rakningu |
| `launathroun_eftir_felagi.csv` | ein lína á hvert (félag, dagsetning) með keðjaðri vísitölu |
| `felog.csv` | uppflettitafla félaga með mati á heilleika raðarinnar |
| `launavisitala_*.csv` | launavísitala Hagstofunnar |

---

## haekkanir.csv

Unnið úr OCR-texta heildarskrár ríkissáttasemjara, sem fylgja staðfest lýsigögn.

| Dálkur | Lýsing |
|---|---|
| `samningur_id`, `contract_id` | auðkenni samningsins í skrá ríkissáttasemjara |
| `felag_id` | stöðugt auðkenni stéttarfélags |
| `felag`, `atvinnurekandi` | samningsaðilar |
| `markadur` | `almennur` eða `opinber` |
| `heildarsamtok` | ASÍ, BHM, BSRB, KÍ eða sérfélög |
| `samningur_fra`, `samningur_til` | gildistími samningsins |
| `gildir_fra` | **hvenær hækkunin tók gildi** |
| `tegund` | prósenta, krónutala eða samsett form |
| `prosenta`, `kronur` | stærð hækkunarinnar |
| `a_vid` | við hvað hún miðast (kauptaxtar, launatafla, almenn laun …) |
| `artal_stada` | hvort ártalið kom úr textanum, var ályktað eða leiðrétt |
| `tilvitnun` | textabúturinn sjálfur, til sannreyningar |

### Hvað er síað frá

- **Launastig** („mánaðarlaun skulu vera kr. 245.000"). Fjárhæð, ekki hækkun.
- **Álagshlutföll** („vaktaálag skal vera 33,33%"). Skilgreinir taxta, ekki hækkun.
- **Skilyrðisdagsetningar** („starfsmenn sem hófu störf fyrir 1. febrúar 2014").
  Þær eru viðmiðunarmörk, ekki gildistökudagur.
- **Greiðslur sem eru ekki laun**: iðgjöld, lífeyrisframlög, ferðapeningar,
  vátryggingarfjárhæðir, desember- og orlofsuppbót.

Prósentur eru takmarkaðar við 0–15% og krónutölur við 500–100.000 kr.

---

## launathroun_eftir_felagi.csv

Ein lína á hvert (félag, dagsetning). Þegar fleiri samningar nefna sömu hækkun
er miðgildi tekið og `heimildir` segir hve margir þeir voru; `olik_gildi` er
hærra en 1 ef heimildum ber ekki saman.

`visitala` er keðjuð út frá prósentuhækkunum, með grunn 100 við fyrstu mælingu
hvers félags.

### Þetta er ekki launavísitala

Vísitalan leggur saman **þær hækkanir sem tókst að finna**. Hún er því aðeins
marktæk fyrir félög þar sem röðin er samfelld. Tvennt takmarkar hana:

1. **Eyður.** `bil_manudir` sýnir mánuði frá síðustu mælingu. Löng bil þýða að
   hækkanir vanti og vísitalan vanmeti þróunina.
2. **Krónutöluhækkanir.** Þær er ekki hægt að umbreyta í hlutfall án þess að
   vita launastigið, svo vísitalan stendur í stað og línan er merkt. Þetta
   leysist þegar launatöflurnar bætast við.

`felog.csv` gefur grófa einkunn á hvert félag:

| Heilleiki | Félög | Merking |
|---|---:|---|
| samfelld | 38 | mesta bil ≤ 18 mánuðir |
| eyður | 37 | mesta bil 19–48 mánuðir |
| stórar eyður | 42 | mesta bil > 48 mánuðir |
| of fáir punktar | 27 | færri en 3 mælingar |

Notið `felag_lykill` til að tengja töflurnar saman - hann sameinar
beygingarmyndir og skammstafanir sama félags.

---

## haekkanir_vefskjol.csv

Sama útdráttur á PDF-um sem sóttir voru af vefjum félaganna. Þeim fylgja engin
lýsigögn, svo samningsaðilar og gildistími eru lesin úr skjalinu sjálfu.
Dálkurinn `rakning` segir hvort aðilar fundust í skjalinu eða hvort aðeins er
vitað hvaðan skjalið kom. **Þessi skrá er höfð aðskilin** frá `haekkanir.csv`
því rakningin er veikari; sameinið aðeins þær línur sem standast skoðun.

---

## launavisitala_*.csv

Launavísitala Hagstofunnar, sótt gegnum PX-Web API.

| Skrá | Tímabil | Tíðni |
|---|---|---|
| `launavisitala_manadarleg.csv` | 1989M01– | mánuðir |
| `launavisitala_hopar_1990_2000.csv` | 1990–2000 | ársfjórðungar |
| `launavisitala_hopar_2000_2006.csv` | 2000–2006 | ársfjórðungar |
| `launavisitala_hopar_2005_2022.csv` | 2005–2022 | ársfjórðungar |
| `launavisitala_hopar_fra_2015.csv` | 2015– | mánuðir |

**Vísitalan skiptist eftir markaði, ekki eftir stéttarfélagi** - almennur
markaður, ríki, sveitarfélög. Hún er því viðmið við hliðina á samningsgögnunum,
ekki staðgengill fyrir þau. Hún mælir líka annað: raunverulega launaþróun með
launaskriði, ekki umsamdar hækkanir.

Grunnárin eru ólík milli taflna og því þarf að keðja þær saman til að fá
samfellda röð frá 1990.
