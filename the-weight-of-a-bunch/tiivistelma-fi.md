# The Weight of a Bunch — hallinnollinen tiivistelmä (suomeksi)

**Teos:** *The Weight of a Bunch — A Novel* (suom. "Tertun paino" — työnimi; englanninkielinen alkuteos)
**Muoto:** Itsenäinen englanninkielinen pienoisromaani, ei käännös
**Laajuus:** ~18 600 sanaa, 24 numeroitua lukua, 5 osaa
**Lähdeaineisto:** kolme tässä säilössä (repository) olevaa suomenkielistä kronikkaa — *Bannanivaltio* (2026), *Puijon piiritys* (2028–2033) ja *Puijon terttu* (BANA:n tarkastuskertomus 1/IX) — yhteensä ~13 300 sanaa, jotka on luettu kokonaan ennen kirjoittamista
**Toimitusmuoto:** `the-weight-of-a-bunch.epub` (EPUB 3, kansi + sisällysluettelo + NCX), Markdown-lähdetiedostot, stdlib-only-pakointiskripti (`build_epub.py`), kannen luontiskripti (`cover_gen.py`)

---

## 1. Teoksen suhde lähdeaineistoon

Kuten projektin luontevaatimuksessa sovittiin, teos **ei ole käännös** eikä se lainaa lähdetekstejä lauseitasolla. Se on *inspiraationsa saanut* itsenäinen teos ("close homage"):

| Säilytetty (tunnistettava kunnianosoitus) | Uusi (itsenäinen teos) |
| --- | --- |
| Paikka: Mustakorpi, Puijo, Kuopio, 61° N | Kaikki henkilöhahmot ovat uusia |
| Kasvihuone 3, rivi 14, terttu 1/2033 | Uusi juoni ja uusi loppu |
| Valtio, BANA, EBK-R-luokan velkasysteemi, 412 kuormaa, 2,4 mrd BY | Kertoja: Akseli Hämäläinen, nuori hallintovirkailija (Frost Maintenance Office) |
| Puijo kapusiiniyhdistys ry, "syöty on syöty", lumiukko ja porkkana | Näkökulma: virkamies reunalla, ei komiteapöytäkirjat |
| Pysyvä komitea, Ruotsin panttisuhde, satelliittimittaukset | Kielikuva: pakkasrintama vs. raportointi |

## 2. Juonirunko

**I The Data of Ice.** Datakeskusinsinööri Akseli Hämäläinen palaa Kuopioon ja saa viran: hän mittaa kolmensadan hehtaarin lasikuvun pakkasrintamaa 32 pisteestä. Hän oppii valtion perusrakenteen: lämpö, kirjanpito ja apinat — ja että valtion ainoa kirjanpitonsa vastaava rivi on kuolleelle tavaralle merkitty rivi.

**II The Warm Moss.** Pohjoisportin lumiukko paljastuu mittalaitteeksi: sulamisvyöhyke kertoo lasiseinän lämmöstä. Luonnonvarainen verso kasvaa hukkalämpöputken juuressa. Yhdistys pitää kevätkokouksen ja toteaa, että terttu kypsyy aikaisemmin kuin valtion ennuste. Naapurintyttö Anniina kysyy läpivalaisevan kysymyksen: *mitä varten terttu on, jos kukaan ei syö, myy tai poimi sitä?*

**III The Receipts.** Valtion tilastoissa viedään 2,3 miljoonaa banaania; kapusiinien Laiturin kirja laskee yhden kuoren. Kuormat ajavat Tornioon tyhjinä ja palaavat täysinä — lastina selvityksiä. Brysselin pysyvä komitea vahvistaa kahdesti vuodessa, että tilanne on ennallaan; wieniläinen satelliitti mittaa lasiseinän lämmöksi +31 °C lokakuussa ja arkistoi havainnon asian vierestä.

**IV The Nameless Day.** Terttu kypsyy 27.10.; valtion korjuupöytäkirjan menettely lykkää korjuuta. Nimettömänä päivänä 7.11. Akseli, yksin laiturilla 4, syö yhden banaanin. Kapusiinit laskevat: 142 → 141. Ruotsalainen tullitutkija A. Strömberg selvittää tapauksen ja toteaa kirjan täsmävän ensimmäistä kertaa.

**V The Winter Account.** Valtio joutuu laatimaan lomakkeen syödyn banaanin ilmoittamiseksi eikä löydä sille lokeroa; BANA luo kategorian EATEN. Työryhmä yrittää nimetä nimettömän päivän. Yhdistys kieltäytyy laskuttamasta totuuttaan, ja valtion kirjanpito täsmää kolmannen kerran historiassaan — lahjana. Narvikin satamapäällikön 11. tiedusteluun vastataan lopullisesti: "There is no shipment." Rivi 14:n juurelta nousee verso: *el hijo*.

## 3. Teema ja merkittävyys

Teos jatkaa lähteen satiiria ("tuotantokyky ei ole sama asia kuin huoltovarmuus") proosamuotoon siirrettynä: se kertoo siitä, mitä tapahtuu valtiolle, joka kirjaa tulevaisuutensa kulutetuksi ennen kuin se on kypsä, ja siitä, mikä jää jäljelle, kun yksi ihminen tekee ensimmäisen todellisen tapahtuman. Kertojan sininen muistikirja on koko teoksen ainoa luotettava rekisteri — ja teoksen viimeinen tase on kolmen rivin mittainen:

> What is eaten is eaten. What is grown, grows. And the pot at the window is not a forecast.

## 4. Tekniset laatuselvitykset

- `python3 build_epub.py` rakentaa 34 dokumentin paketin (kansi + 24 lukua + 5 osavalilehteä + alkusanat + loppu), kansi `cover.jpg` (1600×2560, luonteeltaan ohjelmallisesti piirretty: talviyö, lasiseinä, riippuva tertun käsi, lumiukko).
- Kaikki paketin XML-tiedostot on validoitu: 0 virheitä.
- Oikoluku ja uudelleentarkastus: toistuvat sanat, merkistöartefaktit, tekstihäiriöt — 0 havaintoa.
- Lukujen numerointi ja osarakenne määritellään `build_epub.py`-tiedoston `PARTS`-listassa; uudet luvut lisätään sinne, ei käsin numeroimalla.
