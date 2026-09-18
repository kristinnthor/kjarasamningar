# Gagnasett

## haekkanir.csv

Ein lína á hverja umsamda launabreytingu sem fannst í texta kjarasamnings.

| Dálkur | Lýsing |
|---|---|
| `samningur_id`, `contract_id` | auðkenni samningsins í skrá ríkissáttasemjara |
| `felag_id` | stöðugt auðkenni stéttarfélags (til í ~77% tilvika) |
| `felag` | heiti launþegamegin, eins og það stendur í skránni |
| `atvinnurekandi` | viðsemjandi |
| `markadur` | `almennur` eða `opinber` |
| `heildarsamtok` | ASÍ, BHM, BSRB, KÍ eða sérfélög |
| `samningur_fra`, `samningur_til` | gildistími samningsins |
| `gildir_fra` | **hvenær hækkunin tók gildi** |
| `tegund` | prósenta, krónutala, eða samsett form |
| `prosenta` | hækkun í prósentum |
| `kronur` | hækkun í krónum |
| `a_vid` | við hvað hækkunin miðast (kauptaxtar, launatafla, almenn laun …) |
| `artal_stada` | hvort ártalið kom úr textanum, var ályktað eða leiðrétt |
| `heimild`, `skjal` | rekjanleiki |
| `tilvitnun` | textabútur kringum hækkunina, til sannreyningar |

### Hvað er síað frá

Útdrátturinn sleppir vísvitandi:

- **Launastigi** („mánaðarlaun skulu vera kr. 245.000", „breytist í 467.000 kr.").
  Þetta eru fjárhæðir, ekki hækkanir, og eiga heima í launatöflunum.
- **Álags- og hlutfallsákvæðum** („vaktaálag skal vera 33,33%"). Prósentan
  skilgreinir þar taxta en er ekki hækkun.
- **Greiðslum sem eru ekki laun**: iðgjöld, lífeyrisframlög, ferðapeningar,
  dagpeningar, vátryggingarfjárhæðir, desember- og orlofsuppbót.

### Þekktar takmarkanir

- Prósentur eru takmarkaðar við 0–15% og krónutölur við 500–100.000 kr. Þetta
  eru skynsamleg mörk fyrir umsamdar hækkanir en útiloka jaðartilvik.
- OCR-gæði eldri skjala eru misjöfn. Ártöl eru sannreynd gegn gildistíma
  samningsins og leiðrétt þegar ein augljós lagfæring er möguleg; `artal_stada`
  segir til um hvert tilvik.
- `a_vid` er `óskilgreint` í hluta tilvika þar sem orðalagið er ekki afdráttarlaust.
- Hver lína ber tilvitnun svo hægt sé að sannreyna hana handvirkt.
