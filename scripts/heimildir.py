# -*- coding: utf-8 -*-
"""Skrá yfir vefheimildir þar sem kjarasamningar á Íslandi eru birtir sem PDF.

Hver færsla:
  kodi         : stutt auðkenni, notað sem undirmöppuheiti í samningar/
  heiti        : fullt heiti útgefanda
  vettvangur   : "almennur" | "opinber" | "blandad"
  byrjun       : listi af slóðum sem skrið hefst á
  hostar       : hýsingarlén sem má skríða/sækja af (undirstrengsprófun)
  dypt         : hámarksdýpt skriðs frá byrjunarslóðum
"""

HEIMILDIR = [
    # ------------------------------------------------------------------ #
    # Samtök atvinnurekenda                                              #
    # ------------------------------------------------------------------ #
    {
        "kodi": "sa",
        "heiti": "Samtök atvinnulífsins",
        "vettvangur": "almennur",
        "byrjun": [
            "https://sa.is/vinnumarkadsvefur/kjarasamningar",
            "https://sa.is/vinnumarkadsvefur/kjarasamningar/kaupgjaldsskra-sa/",
            "https://sa.is/vinnumarkadsvefur/kjarasamningar/adrir-samningar/",
        ],
        "hostar": ["sa.is", "prismic.io", "sa.vinnumarkadur.is", "vinnumarkadur.is"],
        "dypt": 3,
    },
    {
        "kodi": "fa",
        "heiti": "Félag atvinnurekenda",
        "vettvangur": "almennur",
        "byrjun": ["https://www.fa.is/kjaramal/kjarasamningar/"],
        "hostar": ["fa.is"],
        "dypt": 3,
    },
    # ------------------------------------------------------------------ #
    # Almenni vinnumarkaðurinn - stéttarfélög og landssambönd            #
    # ------------------------------------------------------------------ #
    {
        "kodi": "vr",
        "heiti": "VR",
        "vettvangur": "almennur",
        "byrjun": [
            "https://www.vr.is/kjaramal/kjarasamningar/",
            "https://www.vr.is/kjaramal/kjarasamningar/kjarasamningar-vid-sa-og-fa/",
            "https://www.vr.is/kjaramal/kjarasamningar/eldri-kjarasamningar/",
            "https://www.vr.is/kjaramal/kjarasamningar/adrir-samningar/",
            "https://www.vr.is/kjaramal/laun/launataxtar/",
            "https://old.vr.is/kjaramal/kjarasamningar/kjarasamningar-vid-sa-og-fa/",
        ],
        "hostar": ["vr.is"],
        "dypt": 3,
    },
    {
        "kodi": "efling",
        "heiti": "Efling stéttarfélag",
        "vettvangur": "blandad",
        "byrjun": [
            "https://www.efling.is/kjarasamningar-og-launatoflur",
            "https://www.efling.is/kjarasamningur/sa",
            "https://www.efling.is/kjarasamningur/sfv",
            "https://www.efling.is/kjarasamningur/rikid",
            "https://www.efling.is/kjarasamningur/reykjavikurborg",
            "https://www.efling.is/kjarasamningur/hotel-og-veitingahus",
        ],
        # PDF-skjölin liggja á CDN Duda-vefkerfisins
        "hostar": ["efling.is", "irp.cdn-website.com"],
        "dypt": 3,
    },
    {
        "kodi": "sgs",
        "heiti": "Starfsgreinasamband Íslands",
        "vettvangur": "blandad",
        "byrjun": [
            "https://www.sgs.is/kjaramal/kjarasamningar/",
            "https://www.sgs.is/kjaramal/kjarasamningar/eldri-samningar/",
        ],
        "hostar": ["sgs.is"],
        "dypt": 3,
    },
    {
        "kodi": "afl",
        "heiti": "AFL Starfsgreinafélag",
        "vettvangur": "blandad",
        "byrjun": [
            "https://www.asa.is/kjaramal/eldri-kjarassamningar-og-kauptaxtar",
            "https://www.asa.is/kjaramal/kjarasamningar-ymissa-starfshopa",
            "https://www.asa.is/kjaramal",
        ],
        "hostar": ["asa.is"],
        "dypt": 3,
    },
    {
        "kodi": "rsi",
        "heiti": "Rafiðnaðarsamband Íslands",
        "vettvangur": "blandad",
        "byrjun": [
            "https://www.rafis.is/kjarasamningar",
            "https://www.rafis.is/gamli/kjarasamningar",
            "https://www.rafis.is/gamli/kjaramal/kjarasamningar",
        ],
        "hostar": ["rafis.is"],
        "dypt": 3,
    },
    {
        "kodi": "samidn",
        "heiti": "Samiðn",
        "vettvangur": "blandad",
        "byrjun": ["https://samidn.is/kjarasamningar/"],
        "hostar": ["samidn.is"],
        "dypt": 3,
    },
    {
        "kodi": "vm",
        "heiti": "VM - Félag vélstjóra og málmtæknimanna",
        "vettvangur": "blandad",
        "byrjun": ["https://vm.is/kjaramal/kjarasamningar/", "https://vm.is/kjaramal/"],
        "hostar": ["vm.is"],
        "dypt": 3,
    },
    {
        "kodi": "matvis",
        "heiti": "MATVÍS",
        "vettvangur": "almennur",
        "byrjun": ["https://matvis.is/kjarasamningar/"],
        "hostar": ["matvis.is"],
        "dypt": 3,
    },
    {
        "kodi": "grafia",
        "heiti": "Grafía",
        "vettvangur": "almennur",
        "byrjun": ["https://grafia.is/kjarasamningar/"],
        "hostar": ["grafia.is"],
        "dypt": 3,
    },
    {
        "kodi": "ssf",
        "heiti": "Samtök starfsmanna fjármálafyrirtækja",
        "vettvangur": "almennur",
        "byrjun": ["https://www.ssf.is/kjaramal/kjarasamningar/", "https://www.ssf.is/kjaramal/"],
        "hostar": ["ssf.is"],
        "dypt": 3,
    },
    {
        "kodi": "eining-idja",
        "heiti": "Eining-Iðja",
        "vettvangur": "blandad",
        "byrjun": [
            "https://www.ein.is/is/kaup-kjor/kjarasamningar",
            "https://www.ein.is/is/kaup-kjor",
        ],
        "hostar": ["ein.is"],
        "dypt": 3,
    },
    {
        "kodi": "framsyn",
        "heiti": "Framsýn stéttarfélag",
        "vettvangur": "blandad",
        "byrjun": ["https://framsyn.is/kjarasamningar/", "https://framsyn.is/kjaramal/"],
        "hostar": ["framsyn.is"],
        "dypt": 3,
    },
    {
        "kodi": "vlfa",
        "heiti": "Verkalýðsfélag Akraness",
        "vettvangur": "blandad",
        "byrjun": ["https://vlfa.is/kjarasamningar/", "https://vlfa.is/kjaramal/"],
        "hostar": ["vlfa.is"],
        "dypt": 3,
    },
    {
        "kodi": "verkvest",
        "heiti": "Verkalýðsfélag Vestfirðinga",
        "vettvangur": "blandad",
        "byrjun": [
            "https://www.verkvest.is/",
            "https://www.verkvest.is/kjarasamningar/",
        ],
        "hostar": ["verkvest.is"],
        "dypt": 3,
    },
    {
        "kodi": "liv",
        "heiti": "Landssamband íslenzkra verzlunarmanna",
        "vettvangur": "almennur",
        "byrjun": ["https://liv.is/kjarasamningar/", "https://www.liv.is/"],
        "hostar": ["liv.is"],
        "dypt": 3,
    },
    {
        "kodi": "sjomenn",
        "heiti": "Sjómannasamband Íslands",
        "vettvangur": "almennur",
        "byrjun": ["https://ssi.is/kjarasamningar/", "https://www.ssi.is/"],
        "hostar": ["ssi.is"],
        "dypt": 3,
    },
    {
        "kodi": "asi",
        "heiti": "Alþýðusamband Íslands",
        "vettvangur": "almennur",
        "byrjun": [
            "https://www.asi.is/kjaramal/kjarasamningar/",
            "https://www.asi.is/utgafa/skyrslur-og-baeklingar/",
        ],
        "hostar": ["asi.is"],
        "dypt": 3,
    },
    # ------------------------------------------------------------------ #
    # Opinberi vinnumarkaðurinn                                          #
    # ------------------------------------------------------------------ #
    {
        "kodi": "rikid",
        "heiti": "Kjara- og mannauðssýsla ríkisins",
        "vettvangur": "opinber",
        "byrjun": [
            "https://www.stjornarradid.is/verkefni/mannaudsmal-rikisins/kjarasamningar-laun-og-starfskjor",
            "https://www.stjornarradid.is/verkefni/mannaudsmal-rikisins/",
            "https://www.stjornarradid.is/raduneyti/fjarmala-og-efnahagsraduneytid/skipulag/kjara-og-mannaudssysla-rikisins/",
        ],
        "hostar": ["stjornarradid.is"],
        "dypt": 3,
    },
    {
        "kodi": "samband",
        "heiti": "Samband íslenskra sveitarfélaga",
        "vettvangur": "opinber",
        "byrjun": [
            "https://www.samband.is/kjaramal",
            "https://www.samband.is/kjarasamningar",
        ],
        "hostar": ["samband.is", "prismic.io"],
        "dypt": 3,
    },
    {
        "kodi": "reykjavik",
        "heiti": "Reykjavíkurborg",
        "vettvangur": "opinber",
        "byrjun": [
            "https://reykjavik.is/kjarasamningar-og-launatoflur",
            "https://prod.reykjavik.is/kjarasamningar-og-launatoflur",
        ],
        "hostar": ["reykjavik.is"],
        "dypt": 3,
    },
    {
        "kodi": "bhm",
        "heiti": "Bandalag háskólamanna",
        "vettvangur": "opinber",
        "byrjun": [
            "https://www.bhm.is/kjaramal",
        ],
        "hostar": ["bhm.is", "prismic.io"],
        "dypt": 3,
    },
    {
        "kodi": "bsrb",
        "heiti": "BSRB",
        "vettvangur": "opinber",
        "byrjun": [
            "https://www.bsrb.is/is/kjaramal",
            "https://www.bsrb.is/is/skodun/stefna-bsrb/kjaramal",
        ],
        "hostar": ["bsrb.is"],
        "dypt": 3,
    },
    {
        "kodi": "ki",
        "heiti": "Kennarasamband Íslands",
        "vettvangur": "opinber",
        "byrjun": [
            "https://www.ki.is/kjaramal-og-styrkir/kjarasamningar/felag-grunnskolakennara/",
            "https://www.ki.is/kjaramal-og-styrkir/kjarasamningar/felag-framhaldsskolakennara/",
            "https://www.ki.is/kjaramal-og-styrkir/kjarasamningar/felag-leikskolakennara/",
            "https://www.ki.is/kjaramal-og-styrkir/kjarasamningar/felag-framhaldsskolakennara/fylgigogn-med-kjarasamningum/",
            "https://www.ki.is/kjaramal-og-styrkir/kjarasamningar/felag-framhaldsskolakennara/kjarasamningar-ff-og-fs-vid-riki/",
            "https://www.ki.is/kjaramal-og-styrkir/kjarasamningar/felag-framhaldsskolakennara/stofnanasamningar-launatoflur-og-onnur-fylgigogn/",
            "https://www.ki.is/adildarfelog/felag-grunnskolakennara/kjarasamningur-fg/",
            "https://www.ki.is/kjaramal-og-styrkir/kjarasamningar/",
        ],
        "hostar": ["ki.is", "prismic.io"],
        "dypt": 3,
    },
    {
        "kodi": "sameyki",
        "heiti": "Sameyki stéttarfélag í almannaþjónustu",
        "vettvangur": "opinber",
        "byrjun": [
            "https://www.sameyki.is/kaup-og-kjor/",
            "https://sameyki.is/kaup-og-kjor/allir-kjarasamningar/",
        ],
        "hostar": ["sameyki.is", "prismic.io"],
        "skjalamynstur": r"/library/\?itemid=",
        "dypt": 3,
    },
    {
        "kodi": "hjukrun",
        "heiti": "Félag íslenskra hjúkrunarfræðinga",
        "vettvangur": "opinber",
        "byrjun": [
            "https://www.hjukrun.is/kjaramal/kjarasamningar",
            "https://www.hjukrun.is/kjaramal",
        ],
        "hostar": ["hjukrun.is", "prismic.io"],
        "dypt": 3,
    },
    {
        "kodi": "lis",
        "heiti": "Læknafélag Íslands",
        "vettvangur": "opinber",
        "byrjun": [
            "https://www.lis.is/is/kjaramal",
            "https://www.lis.is/is/kjaramal/um-kjaramal/kjarasamningur-li",
        ],
        "hostar": ["lis.is"],
        "dypt": 3,
    },
    {
        "kodi": "fin",
        "heiti": "Félag íslenskra náttúrufræðinga",
        "vettvangur": "opinber",
        "byrjun": ["https://fin.is/kjarasamningar/", "https://www.fin.is/"],
        "hostar": ["fin.is"],
        "dypt": 3,
    },
    {
        "kodi": "vfi",
        "heiti": "Verkfræðingafélag Íslands / Stéttarfélag verkfræðinga",
        "vettvangur": "blandad",
        "byrjun": ["https://www.vfi.is/kjaramal/kjarasamningar/"],
        "hostar": ["vfi.is"],
        "dypt": 3,
    },
]


def eftir_kodum(kodar=None):
    if not kodar:
        return HEIMILDIR
    vil = {k.strip().lower() for k in kodar}
    return [h for h in HEIMILDIR if h["kodi"] in vil]
