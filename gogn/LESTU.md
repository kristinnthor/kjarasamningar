# Gagnasett

Þrjú lög: hráar hækkanir úr samningum, tímaröð eftir stéttarfélagi, og
launavísitala Hagstofunnar sem sjálfstætt viðmið.

| Skrá | Inntak |
|---|---|
| `haekkanir.csv` | ein lína á hverja umsamda hækkun sem fannst í samningi |
| `haekkanir_vefskjol.csv` | sama úr PDF-um af vefjum félaganna, með veikari rakningu |
| `haekkanir_sameinad.csv` | hvort tveggja sameinað, aðeins það sem tókst að rekja til félags |
| `launathroun_eftir_felagi.csv` | ein lína á hvert (félag, dagsetning) með keðjaðri vísitölu |
| `felog.csv` | uppflettitafla félaga með mati á heilleika raðarinnar |
| `launatoflur.csv.gz` | fullar launatöflur: fjárhæð á launaflokk og þrep |
| `taxtahaekkanir.csv` | hækkanir mældar beint úr töflunum, óháð texta |
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
- **Framlög í sjóði** („Atvinnurekendur greiða 0,13% í VIRK-Starfsendurhæfingar-
  sjóð"). Hlutfall af launum, ekki launabreyting.
- **Orlofsréttindi** („skal hann fá 13,04%"). Orlofsprósentan fer eftir
  starfsaldri og er réttur, ekki hækkun.
- **Persónuálag** („Frá 1. apríl 2027 — 1,8%"). Álagsstig, ekki breyting.

### Hvers vegna síurnar eru mismunandi víðar

Hver regla fær þann samhengisglugga sem hún þolir, og það er ekki
smekksatriði:

- Reglur sem leita að orðum sem geta staðið hvar sem er í setningu halda sig
  við þröngan glugga. Víkkun um 100 stafi felldi 114 fullgildar hækkanir.
- Reglur sem krefjast þess að orðið standi við sjálfa töluna
  („orlofslaunum sem nema 13,04%") mega leita víðar og þurfa þess.
- Persónuálagsreglan horfir **aðeins aftur fyrir** töluna. Persónuálagsgrein
  stendur iðulega beint á eftir hækkanalista, svo leit í báðar áttir felldi
  alla áfanga 2024-2027 hjá tugum félaga.

`scripts/profa_utdratt.py` ver þetta með 18 aðhvarfsprófum: níu tilvik sem
eiga að falla og níu sem verða að lifa af, þar á meðal öll þrjú ofangreind.

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
| samfelld | 39 | mesta bil ≤ 18 mánuðir |
| eyður | 37 | mesta bil 19–48 mánuðir |
| stórar eyður | 44 | mesta bil > 48 mánuðir |
| of fáir punktar | 27 | færri en 3 mælingar |

Notið `felag_lykill` til að tengja töflurnar saman - hann sameinar
beygingarmyndir og skammstafanir sama félags.

---

## haekkanir_vefskjol.csv

Sama útdráttur á PDF-um sem sóttir voru af vefjum félaganna. Þeim fylgja engin
lýsigögn, svo samningsaðilar og gildistími eru lesin úr skjalinu sjálfu.
Dálkurinn `rakning` segir hvort aðilar fundust í skjalinu eða hvort aðeins er
vitað hvaðan skjalið kom. **Þessi skrá er höfð aðskilin** frá `haekkanir.csv`
því rakningin er veikari.

Skjöl sem líta út eins og samningar en eru það ekki - félagsblöð, fréttabréf
og ársskýrslur - eru útilokuð. Þau fjalla oft um gamla kjarasamninga í
sögulegu samhengi, svo dagsetningarnar í þeim eiga við frásögnina en ekki
gildandi ákvæði. 719 skjöl féllu á því prófi.

## haekkanir_sameinad.csv

`scripts/sameina.py` rekur hverja vefskjalsfærslu til stéttarfélags í þremur
þrepum, og `rakning` segir hvaða þrep skilaði henni:

| Rakning | Línur | Merking |
|---|---:|---|
| staðfest lýsigögn | 2.640 | úr heildarskrá ríkissáttasemjara |
| vefur félagsins | 785 | skjalið kom af vef félagsins sjálfs |
| aðili úr skjali | 178 | samningsaðili í skjalinu passar við þekkt félag |
| *órakið* | *427* | *fellur út - fer ekki í tímaraðirnar* |

Órakti hlutinn kemur nær allur af vefjum viðsemjenda (SA, Reykjavíkurborg,
ríkið), sem geyma samninga við tugi ólíkra félaga. Þar dugar ekki að vita
hvaðan skjalið kom.

**Vefskjölin ná ekkert aftur fyrir 2000.** Félagsvefirnir geyma nær eingöngu
gildandi og nýlega samninga, svo allt eldra hvílir á heildarskránni.

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

---

## launatoflur.csv.gz

257.582 taxtalínur úr 303 skjölum: fjárhæð á hvert (skjal, tafla, launaflokkur,
starfsaldursþrep) ásamt gildistökudegi. Aðeins mánaðarlaun - tímakaup, yfirvinna
og álög eru afleidd af þeim og þrefölduðu umfangið án þess að bæta við neinu.

Skráin er þjöppuð því hún er 43 MB óþjöppuð. Hún er endurgeranleg með
`scripts/utdrattur_launatoflur.py`.

Þrennt heldur töflunum aðgreindum, og án þess eru tölurnar merkingarlausar:

- `gildir_fra` - hvenær taflan tók gildi
- `tafla_nr` - samningur geymir iðulega eina töflu á hvert ár samningstímans,
  og eitt skjal getur borið töflur fyrir ólíka viðsemjendur. Ný tafla er greind
  þegar dálkahaus, mælikvarði eða dagsetning breytist, eða þegar sami
  launaflokkur kemur fyrir öðru sinni.
- `threp_nr` / `threp` - starfsaldursþrep dálkanna

`athugasemd` er merkt þegar fjárhæð er lægri en næsta þrep á undan innan sama
launaflokks. Það brýtur innri reglu töflunnar og bendir til OCR-villu eða
rangrar þáttunar. 1.188 línur af 257.582 (0,46%) bera slíka athugasemd.

## taxtahaekkanir.csv

Hækkanir **mældar beint úr töflunum**: sami launaflokkur og sama þrep borið
saman milli tveggja dagsettra taflna í sama skjali. Þetta er sjálfstæð mæling
á sömu stærð og textaútdrátturinn gefur, og því raunverulegt viðmið.

Samanburður er alltaf innan sama skjals. Milli skjala er hann ótækur því eitt
skjal geymir oft ósambærilegar töflur - eina fyrir sveitarfélög, aðra fyrir
almenna markaðinn.

| Dálkur | Lýsing |
|---|---|
| `fra_dags`, `til_dags` | töflurnar tvær sem bornar eru saman |
| `prosenta` | miðgildi mældrar hækkunar yfir alla flokka og þrep |
| `spennt` | munur á hæstu og lægstu mældu hækkun |
| `samraemd` | 1 þegar `spennt` er 0,5 prósentustig eða minna |

Almenn prósentuhækkun mælist eins í öllum launaflokkum. Mikil dreifing þýðir
að taflan breyttist að gerð en ekki bara að fjárhæð, og þá er mælingin ekki
hrein hækkun. Af 102 mældum hækkunum eru 28 samræmdar.

### Þegar töflunni og textanum ber ekki saman

Mælingin úr töflunni er oft hærri en prósentan í textanum. Það er ekki
ósamræmi heldur eðli samninganna:

> AFL, 1. janúar 2025 — textinn segir „3,50% eða 23.750 kr.", taflan mælir 5,58%.
> Á lægstu töxtunum er krónutalan hærri en prósentan: 23.750 af 425.600 kr. eru
> einmitt 5,58%.

Textinn gefur því **umsamda formúlu**, taflan **raunverulega útkomu**. Hvort
tveggja á rétt á sér; notið það sem spurningin kallar á.
