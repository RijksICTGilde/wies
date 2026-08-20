<title>Toegankelijkheidsonderzoek Wies</title>

<div class="cover">

# Onderzoek Wies

## Rijksorganisatie voor Ontwikkeling, Digitalisering en Innovatie

**WCAG 2.2 — Niveau AA**

augustus 2026

</div>

---

## Inhoudsopgave

- [Inleiding](#inleiding)
- [Onderzoeksresultaat](#onderzoeksresultaat)
- [Uitzonderingen en specifieke situaties](#uitzonderingen-en-specifieke-situaties)
- [Principe 1 Waarneembaar](#principe-1-waarneembaar)
- [Principe 2 Bedienbaar](#principe-2-bedienbaar)
- [Principe 3 Begrijpelijk](#principe-3-begrijpelijk)
- [Principe 4 Robuust](#principe-4-robuust)
- [Onderzoeksgegevens](#onderzoeksgegevens)

---

## Inleiding

Het toegankelijkheidsonderzoek naar Wies is afgerond op 19 augustus 2026. Dit
onderzoek laat zien in hoeverre de applicatie op dit moment voldoet aan de
internationaal geaccepteerde toegankelijkheidsrichtlijnen (WCAG 2.2).

WCAG staat voor Web Content Accessibility Guidelines. Dit zijn de internationale
richtlijnen voor toegankelijkheid van webcontent. De richtlijnen zijn opgedeeld in
vier principes (Waarneembaar, Bedienbaar, Begrijpelijk en Robuust). Elke richtlijn
is vervolgens opgedeeld in meetbare succescriteria. Omdat WCAG
techniekonafhankelijk is opgesteld, kan hiermee de toegankelijkheid van alle
content op het web worden onderzocht.

De beschrijving van de succescriteria is in dit rapport ingekort. Volledige
beschrijvingen zijn te vinden in de WCAG-documentatie. In het rapport geven we bij
ieder succescriterium een algemene toelichting. Hoewel de WCAG-norm duidelijk
genoeg is om onderzoeken goed te kunnen uitvoeren, kan de beoordeling van
succescriteria op detailniveau de komende tijd veranderen.

In dit rapport worden slechts voorbeelden gegeven van aangetroffen problemen; dit
is echter geen compleet overzicht. Omdat het onderzoek uit een steekproef bestaat,
kan het zijn dat een probleem niet gesignaleerd wordt. Wanneer verbeteringen
worden doorgevoerd, dient er rekening mee gehouden te worden dat hierdoor nieuwe
toegankelijkheidsproblemen kunnen ontstaan.

> **Status van dit onderzoek.** Dit onderzoek is uitgevoerd door het eigen
> ontwikkelteam met geautomatiseerde en instrumentele toetsing. Het is **geen
> onafhankelijk onderzoek** en is **niet volledig**: er is niet getest met
> hulpsoftware (schermlezer, spraakbediening) en niet met gebruikers. Het kan een
> formeel onderzoek voor het register **niet vervangen**. Bij veertien
> succescriteria is daarom "niet vastgesteld" genoteerd in plaats van een oordeel.

---

## Onderzoeksresultaat

Uit het onderzoek is gebleken dat de applicatie op **twee succescriteria niet
voldoet**, beide op niveau A. Op **31 van de 55** succescriteria wordt voldaan.
Acht succescriteria zijn niet van toepassing. Bij **veertien succescriteria** kon
met de gebruikte methode geen uitspraak worden gedaan.

De applicatie voldoet op dit moment **niet** aan de vereisten voor WCAG 2.2,
niveau AA.

Onderstaande tabel geeft het aantal succescriteria waaraan op dit moment wordt
voldaan. Getoetst zijn alle 55 succescriteria van WCAG 2.2 op niveau A en AA.

|                  | Niveau A    | Niveau AA   | Totaal      |
| ---------------- | ----------- | ----------- | ----------- |
| **Waarneembaar** | 1 / 9       | 6 / 11      | 7 / 20      |
| **Bedienbaar**   | 12 / 14     | 5 / 6       | 17 / 20     |
| **Begrijpelijk** | 5 / 7       | 2 / 6       | 7 / 13      |
| **Robuust**      | 0 / 1       | 0 / 1       | 0 / 2       |
| **Totaal**       | **18 / 31** | **13 / 24** | **31 / 55** |

**Uitgeschreven.** Van de 55 succescriteria voldoen er 31. Twee voldoen niet
(1.3.1 en 2.4.3, beide niveau A). Acht zijn niet van toepassing omdat de
applicatie geen audio, video of bewegingsbediening bevat en de authenticatie bij
een externe leverancier ligt. Van veertien succescriteria kon de status niet
worden vastgesteld, omdat daarvoor toetsing met hulpsoftware nodig is.

De lage score bij Waarneembaar en Robuust komt vooral doordat binnen die
principes veel criteria niet konden worden vastgesteld of niet van toepassing
zijn; binnen Waarneembaar is één afwijking gevonden en binnen Robuust geen.

### Verdeling van de uitkomsten

| Uitkomst               | Aantal | Succescriteria                                                                                     |
| ---------------------- | ------ | -------------------------------------------------------------------------------------------------- |
| ✅ Voldoet             | 31     | zie de hoofdstukken hieronder                                                                      |
| ❌ Voldoet niet        | 2      | 1.3.1, 2.4.3                                                                                       |
| ⬜ Niet vastgesteld    | 14     | 1.1.1, 1.3.2, 1.3.5, 1.4.1, 1.4.11, 1.4.13, 2.4.6, 3.1.2, 3.2.2, 3.3.1, 3.3.3, 3.3.4, 4.1.2, 4.1.3 |
| ➖ Niet van toepassing | 8      | 1.2.1, 1.2.2, 1.2.3, 1.2.4, 1.2.5, 1.4.2, 2.5.4, 3.3.8                                             |
| **Totaal**             | **55** |                                                                                                    |

### Samenvatting van de bevindingen

| #   | Bevinding                                          | Succescriterium        | Niveau | Impact |
| --- | -------------------------------------------------- | ---------------------- | ------ | ------ |
| 1   | Koppenstructuur slaat een niveau over              | 1.3.1 Info en relaties | A      | Medium |
| 2   | Focus gaat verloren na het bijwerken van de pagina | 2.4.3 Focus volgorde   | A      | Medium |

### Nieuw in WCAG 2.2

WCAG 2.2 voegt zes succescriteria toe op niveau A en AA, en laat 4.1.1 (Parsen)
vervallen. De nieuwe criteria zijn in dit onderzoek meegenomen:

| Succescriterium                              | Niveau | Status                 |
| -------------------------------------------- | ------ | ---------------------- |
| 2.4.11 Focus niet bedekt (minimaal)          | AA     | ✅ voldoet             |
| 2.5.7 Sleepbewegingen                        | AA     | ✅ voldoet             |
| 2.5.8 Doelgrootte (minimaal)                 | AA     | ✅ voldoet             |
| 3.2.6 Consistente hulp                       | A      | ✅ voldoet             |
| 3.3.7 Overbodige invoer                      | A      | ✅ voldoet             |
| 3.3.8 Toegankelijke authenticatie (minimaal) | AA     | ➖ niet van toepassing |

> **Gevolg voor de toegankelijkheidsverklaring.** Op basis van dit onderzoek kan
> verklaring 29132 niet op status A of B worden gezet. Status A en B vereisen een
> **volledig** onderzoek waarin alle 55 succescriteria zijn beoordeeld; hier zijn
> er veertien niet vastgesteld. Zie ook
> [Beperkingen van dit onderzoek](#beperkingen-van-dit-onderzoek).

## Uitzonderingen en specifieke situaties

Bij dit onderzoek is uitgegaan van de Europese standaard voor
toegankelijkheidseisen, de EN 301 549-norm, waarin wordt verwezen naar de
internationale toegankelijkheidsrichtlijn WCAG 2.

**Op tijd gebaseerde media.** De applicatie bevat geen audio, video of iframes.
Gemeten op alle onderzochte pagina's: `<video>` 0, `<audio>` 0, `<iframe>` 0. De
succescriteria 1.2.1 tot en met 1.2.5 zijn daarom niet van toepassing.

**Documenten.** Er worden vanuit de applicatie geen PDF- of Office-bestanden
aangeboden. De CSV-export van plaatsingen valt buiten de scope van WCAG.

**Besloten applicatie.** Wies is alleen bereikbaar na aanmelding via OIDC. Het
inlogscherm wordt geleverd door Keycloak, valt onder een andere leverancier en is
niet meegenomen.

---

## Principe 1 Waarneembaar

_Informatie en componenten van de gebruikersinterface moeten toonbaar zijn aan gebruikers op voor hen waarneembare wijze._

### Richtlijn 1.1 Tekstalternatieven

_Lever tekstalternatieven voor alle niet-tekstuele content, zodat die veranderd kan worden in andere vormen die mensen nodig hebben._

#### Succescriterium 1.1.1 (Niveau A) — Niet-tekstuele content

Alle niet-tekstuele content die aan de gebruiker wordt gepresenteerd, heeft een
tekstalternatief dat een gelijkwaardig doel dient.

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

De enige inhoudelijke afbeelding — het toegankelijkheidslabel — heeft een
beschrijvende `alt`-tekst. Alle overige beelden zijn iconen binnen
webcomponenten. Op `/beheer/gebruikers/` zijn 265 SVG-elementen aangetroffen
zonder toegankelijke naam of `aria-hidden`. Vrijwel alle staan naast een
tekstlabel en zijn dus terecht decoratief, maar per icoon moet inhoudelijk worden
bepaald of het betekenis draagt.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Alle belangrijke niet-tekstuele content zoals afbeeldingen, knoppen en
formulier-invoervelden moeten een tekstueel alternatief of naam hebben. Dan kan de
voorleessoftware van blinde bezoekers die informatie voorlezen. Iconen die naast
een tekstlabel staan en niets toevoegen, horen juist `aria-hidden="true"` te
krijgen, zodat ze niet dubbel worden voorgelezen.

</div>

### Richtlijn 1.2 Op tijd gebaseerde media

De applicatie bevat geen audio en geen video. Gemeten op alle elf onderzochte
pagina's: `<video>` 0, `<audio>` 0, `<iframe>` 0. De onderstaande vijf
succescriteria zijn daarom alle niet van toepassing.

| Succescriterium                                                     | Niveau | Status                 |
| ------------------------------------------------------------------- | ------ | ---------------------- |
| 1.2.1 Louter-geluid en louter-videobeeld (vooraf opgenomen)         | A      | ➖ niet van toepassing |
| 1.2.2 Ondertiteling voor doven en slechthorenden (vooraf opgenomen) | A      | ➖ niet van toepassing |
| 1.2.3 Audiodescriptie of media-alternatief (vooraf opgenomen)       | A      | ➖ niet van toepassing |
| 1.2.4 Ondertitels voor doven en slechthorenden (live)               | AA     | ➖ niet van toepassing |
| 1.2.5 Audiodescriptie (vooraf opgenomen)                            | AA     | ➖ niet van toepassing |

<div class="explain">

**Uitleg van deze succescriteria**

Voor video en audio gelden aparte eisen: ondertiteling voor dove en slechthorende
bezoekers, en audiodescriptie of een uitgeschreven transcript voor blinde
bezoekers. Zodra Wies video of audio gaat aanbieden — bijvoorbeeld een
instructiefilmpje bij de onboarding — worden deze criteria alsnog van toepassing
en moeten ze opnieuw worden beoordeeld.

</div>

### Richtlijn 1.3 Aanpasbaar

_Creëer content die op verschillende manieren gepresenteerd kan worden zonder verlies van informatie of structuur._

#### Succescriterium 1.3.1 (Niveau A) — Info en relaties

Informatie, structuur en relaties overgebracht door presentatie kunnen door
software bepaald worden of zijn beschikbaar in tekst.

<div class="verdict fail">

**De onderzochte set webpagina's voldoet niet aan dit succescriterium.**

**Impact: medium** · Pagina's: `/opdrachten/`, `/beheer/gebruikers/`

</div>

De filtergroepen in de zijbalk staan als `<h3>` in de broncode en gaan vooraf aan
de `<h1>` van de pagina. De gemeten koppenreeks op `/opdrachten/`:

```
H3: Opdrachtgever          ← zijbalk, vóór de paginatitel
H3: Rol
H3: Beschikbaar vanaf
H1: Aanvragen              ← paginatitel
H3: Opzet Data Platform Onderwijs
H3: Proof of Concept Managementinformatie
```

Na de `<h1>` volgt direct een `<h3>`; niveau 2 ontbreekt. Wie met een schermlezer
door de koppen navigeert, krijgt een structuur voorgeschoteld die niet klopt met
de visuele opbouw, en begint bovendien in de zijbalk in plaats van bij de
paginatitel.

**Bron:** `wies/core/jinja2/parts/filter_sidebar.html`, regel 42 en 81.

**Geadviseerde oplossing.** Breng de filtergroepen naar `<h2>` en plaats de
zijbalk in de broncode ná de `<h1>`. Visueel kan de volgorde met CSS blijven zoals
hij nu is. Daarmee wordt de reeks H1 → H2 → H3 sluitend.

<div class="explain">

**Uitleg van dit succescriterium**

Alle informatie die visueel wordt overgedragen, dient ook tekstueel of semantisch
(in betekenisvolle code) te worden overgedragen. Op deze manier kan de informatie
ook aan blinde bezoekers worden voorgelezen. Let in het bijzonder op:

- Maak alle koppen correct op, namelijk met `<h1>` tot en met `<h6>`. Sla daarbij
  geen niveaus over: na een `<h1>` hoort een `<h2>`, niet meteen een `<h3>`.
- Gebruik correcte lijstopmaak: `<ul>` voor ongeordende en `<ol>` voor geordende
  lijsten, met `<li>` voor de items.
- Gebruik `<table>` voor datatabellen, met `<th>` voor rij- en kolomkoppen.
- Bied namen aan invoervelden en groepeer bij elkaar horende velden.

</div>

#### Succescriterium 1.3.2 (Niveau A) — Betekenisvolle volgorde

Als de volgorde waarin content wordt gepresenteerd van invloed is op zijn
betekenis, kan een betekenisvolle leesvolgorde door software bepaald worden.

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

De broncodevolgorde komt op de onderzochte pagina's overeen met de visuele
volgorde, met uitzondering van de zijbalk (zie 1.3.1). Een sluitend oordeel vraagt
beoordeling met een schermlezer.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Content dient in een betekenisvolle volgorde in de broncode te staan. De
voorleessoftware van blinde bezoekers leest namelijk de broncodevolgorde voor, niet
de visuele volgorde. Wordt iets met CSS visueel verplaatst, dan kan de voorgelezen
volgorde afwijken van wat op het scherm staat.

</div>

#### Succescriterium 1.3.3 (Niveau A) — Zintuiglijke eigenschappen

Instructies zijn niet alleen afhankelijk van zintuiglijke eigenschappen zoals
vorm, omvang, visuele locatie, oriëntatie of geluid.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er zijn geen instructies aangetroffen die uitsluitend verwijzen naar vorm,
omvang, locatie of geluid.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Instructies als "klik op het vierkante icoon" of "de instructies staan in de
rechterkolom" zijn niet te begrijpen voor blinde bezoekers. Benoem in plaats
daarvan het element bij zijn naam of label.

</div>

#### Succescriterium 1.3.4 (Niveau AA) — Oriëntatie

De weergave en bediening van content is niet beperkt tot een enkele schermstand.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Getoetst in staand (600 × 900) en liggend (900 × 600) formaat. In beide standen
geen verlies van content of functionaliteit, en geen horizontale schuifbalk.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Een website mag niet afdwingen dat een tablet of telefoon in één bepaalde stand
wordt gehouden. Mensen die hun apparaat in een houder of aan een rolstoel bevestigd
hebben, kunnen de stand vaak niet wijzigen.

</div>

#### Succescriterium 1.3.5 (Niveau AA) — Inputdoel identificeren

Het doel van elk invoerveld waarmee informatie over de gebruiker wordt verzameld,
kan door software worden bepaald.

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

Van de 13 invoervelden op `/beheer/gebruikers/` heeft er geen enkele een
`autocomplete`-attribuut. Het criterium geldt echter alleen voor velden die
gegevens over de _gebruiker zelf_ verzamelen. De formulieren in Wies verzamelen
gegevens over _andere_ personen (collega's). Of de uitzondering opgaat, vraagt een
inhoudelijke bevestiging.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Velden die om gegevens van de gebruiker zelf vragen (naam, e-mailadres,
telefoonnummer) horen een `autocomplete`-attribuut te hebben. Browsers en
hulpsoftware kunnen die velden dan automatisch invullen of van een herkenbaar icoon
voorzien. Dat scheelt typewerk voor mensen met een motorische beperking en helpt
mensen met een cognitieve beperking.

</div>

### Richtlijn 1.4 Onderscheidbaar

_Maak het voor gebruikers gemakkelijker om content te horen en te zien._

#### Succescriterium 1.4.1 (Niveau A) — Gebruik van kleur

Kleur wordt niet als het enige visuele middel gebruikt om informatie over te
brengen.

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

Statusinformatie wordt in Wies overgebracht met tekstlabels naast kleur
(bijvoorbeeld "Beperkt zichtbaar", "Afgelopen"). Een uitputtende controle van alle
statusweergaven en grafische elementen is niet uitgevoerd.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Als informatie alleen door kleurverschil wordt overgebracht, kan die informatie
niet worden waargenomen door slechtziende of kleurenblinde bezoekers. Zorg dat een
link niet alleen aan kleur herkenbaar is maar ook aan onderstreping, en dat
foutmeldingen niet alleen "rood" zijn maar ook tekstueel worden benoemd.

</div>

#### Succescriterium 1.4.2 (Niveau A) — Geluidsbediening

<div class="verdict na">

**Dit succescriterium is niet van toepassing.**

Er is geen automatisch spelende audio aanwezig.

</div>

#### Succescriterium 1.4.3 (Niveau AA) — Contrast (minimum)

De visuele weergave van tekst en afbeeldingen van tekst heeft een
contrastverhouding van ten minste 4,5:1.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

|                                                  |         |
| ------------------------------------------------ | ------- |
| Gemeten tekstelementen                           | **903** |
| Onder de norm (4,5:1, of 3,0:1 voor grote tekst) | **0**   |

</div>

Alle zichtbare tekst op de elf pagina's is gemeten, **inclusief de shadow roots
van de webcomponenten**. Kleuren zijn door de browser zelf omgezet via een canvas,
zodat moderne kleurnotaties (`oklch()`) correct oplossen. Doorzichtigheid van tekst
en van alle bovenliggende lagen is meegerekend.

De meetmethode is gevalideerd door contrastfouten te injecteren in zowel het gewone
document als in een shadow root; beide werden gedetecteerd (1,92:1).

<div class="explain">

**Uitleg van dit succescriterium**

Het doel is voldoende contrast tussen tekstkleur en achtergrondkleur, zodat de
tekst goed kan worden gelezen door kleurenblinde of slechtziende bezoekers. Grote
tekst (vanaf 24 px, of 18,66 px vet) mag een lager contrast hebben: 3:1 in plaats
van 4,5:1. Met het gratis programma Colour Contrast Analyser is het contrast
handmatig te meten.

</div>

#### Succescriterium 1.4.4 (Niveau AA) — Herschalen van tekst

Tekst kan zonder hulptechnologie tot 200 procent schalen zonder verlies van
content of functionaliteit.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Getoetst tot een weergavekader van 720 px, equivalent aan 200 % vergroting. Geen
verlies van content of functionaliteit en geen horizontale schuifbalk.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Voor slechtziende bezoekers is het belangrijk dat tekst tot 200 % kan worden
vergroot. Let erop dat daarbij geen informatie wegvalt: tekst die buiten een kader
valt of buiten beeld raakt zonder dat gescrold kan worden, is een probleem.

</div>

#### Succescriterium 1.4.5 (Niveau AA) — Afbeeldingen van tekst

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er is geen tekst als afbeelding aangetroffen. De enige afbeelding is het
toegankelijkheidslabel, dat als keurmerk is uitgezonderd.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Tekst hoort met HTML te worden geplaatst en niet als afbeelding. HTML-tekst is met
een eigen stylesheet aan te passen in kleur, lettertype en grootte, en blijft scherp
bij vergroting. Dit is eenvoudig te testen door alles op de pagina te selecteren
(Ctrl+A): wat niet oplicht, is een afbeelding.

</div>

#### Succescriterium 1.4.10 (Niveau AA) — Dynamisch aanpassen (reflow)

Content kan zonder verlies van informatie of functionaliteit en zonder te scrollen
in twee dimensies worden weergegeven.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

| Breedte                    | Horizontale schuifbalk |
| -------------------------- | ---------------------- |
| 1440 px                    | nee                    |
| 720 px                     | nee                    |
| **320 px** (de reflow-eis) | **nee**                |

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Content moet bruikbaar blijven bij een breedte van 320 CSS-pixels, gelijk aan een
beginbreedte van 1280 px bij 400 % zoom. De gebruiker mag dan niet in twee
richtingen tegelijk hoeven scrollen. Uitgezonderd zijn onderdelen die een
tweedimensionale lay-out vereisen, zoals kaarten en grote datatabellen.

</div>

#### Succescriterium 1.4.11 (Niveau AA) — Niet-tekstueel contrast

De visuele weergave van componenten en grafische objecten heeft een
contrastverhouding van ten minste 3:1.

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

De contrastmeting betrof tekst. Randen van invoervelden, iconen, focusindicatoren
en statuskleuren zijn niet systematisch gemeten; de meting die is uitgevoerd
bereikte slechts één component, omdat de meeste bedieningselementen hun kleuren in
een shadow root zetten.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Niet alleen tekst moet voldoende contrast hebben. Ook de rand van een invoerveld,
het vinkje in een selectievakje, een icoon dat betekenis draagt en de focusring
moeten zich met ten minste 3:1 aftekenen tegen hun omgeving. Anders is voor
slechtziende gebruikers niet te zien waar een veld begint of eindigt.

</div>

#### Succescriterium 1.4.12 (Niveau AA) — Tekstafstand

Er is geen verlies van content of functionaliteit wanneer regelhoogte,
letterafstand en woordafstand worden gewijzigd.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Getoetst met regelhoogte 1,5×, afstand tussen alinea's 2×, letterafstand 0,12em en
woordafstand 0,16em. Geen verlies van content, geen overlappende tekst en geen
horizontale schuifbalk.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Mensen met dyslexie of een visuele beperking passen soms met een eigen stylesheet
de regel-, letter- en woordafstand aan om tekst leesbaarder te maken. De pagina moet
daar tegen kunnen: tekst mag niet uit zijn kader lopen of achter andere elementen
verdwijnen.

</div>

#### Succescriterium 1.4.13 (Niveau AA) — Content bij aanwijzen of focussen

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

Wies bevat tooltips op iconen en op de privacy-chips. Of deze met Escape te sluiten
zijn, met de muis te bereiken zijn en blijven staan zolang dat nodig is, is niet
getoetst.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Verschijnt er extra inhoud bij het aanwijzen of focussen (een tooltip, een
uitklapmenu), dan gelden drie eisen: de inhoud moet met Escape te sluiten zijn, de
muis moet er naartoe kunnen bewegen zonder dat hij verdwijnt, en hij moet zichtbaar
blijven tot de gebruiker wegbeweegt of hem sluit.

</div>

---

## Principe 2 Bedienbaar

_Componenten van de gebruikersinterface en navigatie moeten bedienbaar zijn._

### Richtlijn 2.1 Toetsenbordtoegankelijk

#### Succescriterium 2.1.1 (Niveau A) — Toetsenbord

Alle functionaliteit van de content is bedienbaar via een toetsenbordinterface.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Alle interactieve elementen zijn met Tab bereikbaar. Getoetst via de
accessibility tree van de browser: op `/` 61 interactieve elementen, op
`/beheer/gebruikers/` 70 — alle met een toegankelijke naam en rol.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Alle functionaliteit dient bediend te kunnen worden met het toetsenbord. Dit is te
toetsen door de hele applicatie alleen met Tab, Enter, spatie en de pijltoetsen te
bedienen, zonder muis.

</div>

#### Succescriterium 2.1.2 (Niveau A) — Geen toetsenbordval

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Getoetst op de sheet "Merk toevoegen": deze opent als een echte `<dialog open>`,
de focus springt bij openen naar het eerste invoerveld, en van 12 opeenvolgende
tabstops bleven er 9 binnen de sheet — de focus loopt rond en verlaat het venster
niet.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Een bezoeker mag nooit met het toetsenbord "vast" komen te zitten. Bij een venster
of dialoog hoort de focus juist wél ingesloten te zijn zolang het open staat, maar
er moet altijd een weg naar buiten zijn — meestal met Escape of een sluitknop.

</div>

#### Succescriterium 2.1.4 (Niveau A) — Sneltoetsen tekentoets

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er zijn geen sneltoetsen geïmplementeerd die uit één teken bestaan.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Sneltoetsen die uit één letter of cijfer bestaan, kunnen per ongeluk worden
geactiveerd door mensen die met spraak werken of die trillen bij het typen. Zulke
sneltoetsen moeten uit te zetten of opnieuw toe te wijzen zijn.

</div>

### Richtlijn 2.2 Genoeg tijd

#### Succescriterium 2.2.1 (Niveau A) — Timing aanpasbaar

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er is geen `meta refresh` aangetroffen en geen tijdslimiet binnen de applicatie.
De sessieduur wordt beheerd door de authenticatievoorziening, die buiten de scope
valt.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Heeft een bezoeker beperkt de tijd om iets te lezen of te doen, dan moet die limiet
uit te zetten, aan te passen of te verlengen zijn. Dit is vooral belangrijk voor
blinde bezoekers en mensen met een cognitieve beperking, die meer tijd nodig hebben.

</div>

#### Succescriterium 2.2.2 (Niveau A) — Pauzeren, stoppen, verbergen

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er is geen bewegende, knipperende, scrollende of automatisch actualiserende content
aangetroffen.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Bewegende of automatisch bijwerkende content leidt af bij het gebruik van de rest
van de pagina. Duurt de beweging langer dan vijf seconden, dan moet die te
pauzeren, te stoppen of te verbergen zijn.

</div>

### Richtlijn 2.3 Toevallen

#### Succescriterium 2.3.1 (Niveau A) — Drie flitsen of beneden drempelwaarde

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er is geen flitsende content aanwezig.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Sterk flitsende content kan epileptische aanvallen veroorzaken. Vermijd content die
meer dan drie keer per seconde flitst.

</div>

### Richtlijn 2.4 Navigeerbaar

#### Succescriterium 2.4.1 (Niveau A) — Blokken omzeilen

Er is een mechanisme beschikbaar om blokken content die op meerdere webpagina's
worden herhaald te omzeilen.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er is een skiplink "Ga naar hoofdinhoud" (`base.html`, regel 60). Geverifieerd: het
is de **eerste tabstop** op de pagina, hij wordt zichtbaar bij focus, en activeren
verplaatst de focus naar de hoofdinhoud.

</div>

> **Correctie op een bestaande melding.** Issue #600 in de projectadministratie
> meldt dat er géén skiplink zou zijn. Dat deel is **niet meer actueel**.
> Aanbevolen het issue bij te werken zodat alleen het focusprobleem (2.4.3) open
> blijft staan.

<div class="explain">

**Uitleg van dit succescriterium**

Zorg dat toetsenbordgebruikers en blinde bezoekers herhalende blokken — menu's,
zoekveld, logo — kunnen overslaan om direct bij de hoofdinhoud te komen. De beste
manier is een skiplink bovenaan de pagina, die zichtbaar wordt zodra hij focus
krijgt.

</div>

#### Succescriterium 2.4.2 (Niveau A) — Paginatitel

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Alle elf pagina's hebben een beschrijvende, onderscheidende titel volgens het
patroon `<Pagina> · Wies`, bijvoorbeeld "Wie zit waar · Wies" en "Veelgestelde
vragen · Wies".

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Een goede paginatitel in het `<title>`-element is voor blinde bezoekers het eerste
wat wordt voorgelezen en helpt bij het schakelen tussen tabbladen. Zet het
specifieke deel vooraan, de sitenaam achteraan.

</div>

#### Succescriterium 2.4.3 (Niveau A) — Focus volgorde

Focusbare componenten krijgen de focus in een volgorde waardoor betekenis en
bedienbaarheid behouden blijven.

<div class="verdict fail">

**De onderzochte set webpagina's voldoet niet aan dit succescriterium.**

**Impact: medium** · Alle pagina's met panelen, sheets of inline bewerken

</div>

Wies vervangt delen van de pagina zonder deze opnieuw te laden. Staat de focus op
een element dat daarbij wordt vervangen, dan valt de focus terug op `<body>` en
begint de volgende Tab-toets weer bovenaan de pagina.

Dit treft elk zijpaneel, elke sheet en elke inline bewerking — de kern van de
applicatie. Voor wie met het toetsenbord werkt, betekent het dat na elke handeling
de weg terug opnieuw moet worden afgelegd. In een werkapplicatie die de hele dag
wordt gebruikt, loopt dat sterk op.

Deze bevinding is bekend in de projectadministratie als issue #600.

**Geadviseerde oplossing.** Verplaats na het vervangen van een fragment de focus
programmatisch naar dat fragment, of naar een logisch startpunt daarbinnen.

> **Status na dit onderzoek.** PR #638 voert deze oplossing uit, met één afwijking
> van het advies hierboven: de focus gaat naar een element _binnen_ het vervangen
> fragment en niet naar het fragment zelf. De container is een `nldd-page` en dus
> een shadow host, en daar bepaalt de `tabindex` van de host of zijn inhoud
> meedoet in de tabvolgorde — het fragment focusbaar maken brak de tabvolgorde
> van het zijpaneel.
>
> `scripts/focus_swap.py` meet deze bevinding; `focus.py` doet dat niet, want dat
> voert geen swaps uit. De meting geeft 9 van 9 met de wijziging en faalt zonder
> op de flow "inline bewerken openen", waar de focus dan op `<body>` blijft.
> Het oordeel hierboven beschrijft de stand op de onderzoeksdatum en blijft
> daarom staan tot de wijziging op `main` staat.

<div class="explain">

**Uitleg van dit succescriterium**

De tabvolgorde moet logisch zijn en aansluiten bij wat er op het scherm gebeurt.
Wordt een venster geopend, dan hoort de focus daarheen te gaan. Wordt een deel van
de pagina vervangen, dan hoort de focus mee te verhuizen en niet terug te vallen
naar het begin van de pagina.

</div>

#### Succescriterium 2.4.4 (Niveau A) — Linkdoel (in context)

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er zijn geen links met nietszeggende tekst ("lees meer", "klik hier", "hier")
aangetroffen. Externe links dragen sinds kort een icoon en verborgen tekst die
aankondigt dat ze in een nieuw tabblad openen.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Bied een duidelijke linktekst die aangeeft waar de link naartoe verwijst. Blinde
bezoekers vragen vaak een lijst van alle links op een pagina op; "lees meer" zegt
in zo'n lijst niets.

</div>

#### Succescriterium 2.4.5 (Niveau AA) — Meerdere manieren

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er zijn ten minste twee manieren om een pagina te bereiken: de hoofdnavigatie en de
zoekfunctie op het overzicht, aangevuld met filters op organisatie, rol en merk.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Elke pagina moet op minstens twee manieren te bereiken zijn, bijvoorbeeld via het
menu én via een zoekfunctie of sitemap. Stappen binnen een proces zijn hiervan
uitgezonderd.

</div>

#### Succescriterium 2.4.6 (Niveau AA) — Koppen en labels

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

De koppen zijn beschrijvend, maar de structuur klopt niet overal (zie 1.3.1). Een
inhoudelijk oordeel over de formulering van alle koppen en labels is niet gegeven.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Koppen en labels moeten het onderwerp of doel beschrijven. Een kop als "Meer
informatie" kan beter "Meer informatie over voorleessoftware" heten. Blinde
bezoekers vragen vaak een overzicht van alle koppen op om snel een beeld van de
inhoud te krijgen.

</div>

#### Succescriterium 2.4.7 (Niveau AA) — Focus zichtbaar

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Visueel geverifieerd: elementen met toetsenbordfocus krijgen een duidelijk
zichtbare ring.

</div>

> **Kanttekening bij de meting.** Een eerste geautomatiseerde meting meldde dat 8
> van de 10 tabstops geen zichtbare focusindicator hadden. Dat bleek **onjuist**:
> de indicator wordt getekend op een element ín de shadow root van het component,
> niet op het element dat de browser als "actief" teruggeeft. Visuele controle
> weerlegde de meting.

<div class="explain">

**Uitleg van dit succescriterium**

Zorg dat altijd visueel zichtbaar is waar de toetsenbordfocus zich bevindt. Dit is
te toetsen door de applicatie alleen met Tab te doorlopen en te kijken of steeds
duidelijk is welk element aan de beurt is.

</div>

#### Succescriterium 2.4.11 (Niveau AA) — Focus niet bedekt (minimaal)

Wanneer een component toetsenbordfocus krijgt, wordt deze niet volledig verborgen
door content die door de auteur is toegevoegd.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Getoetst door 20 opeenvolgende tabstops te doorlopen op een venster van 1200 × 500
pixels — een hoogte waarbij vaste elementen het snelst in de weg zitten. Het
element met focus bleef steeds volledig in beeld; de pagina scrolt het zo nodig in
zicht. Er is één `sticky` element aangetroffen (de filterzijbalk), dat de
hoofdinhoud niet overlapt.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Een vaste kopbalk, cookiebanner of chatvenster kan het element met toetsenbordfocus
afdekken. De gebruiker ziet dan niet waar hij is. Nieuw in WCAG 2.2: het element
met focus mag niet **volledig** verborgen zijn.

</div>

### Richtlijn 2.5 Inputmodaliteiten

#### Succescriterium 2.5.1 (Niveau A) — Bewegingen aanwijzer

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er zijn geen multipoint- of padgebaseerde bewegingen aangetroffen.

</div>

#### Succescriterium 2.5.2 (Niveau A) — Annulering aanwijzer

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Bediening vindt plaats op het loslaten van de muisknop (standaard klikgedrag), niet
op het indrukken.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Wordt een functie al uitgevoerd zodra de muisknop omlaag gaat, dan kan iemand met
een motorische beperking een onbedoelde klik niet meer terugnemen. Door pas bij het
loslaten te reageren, kan de gebruiker de muis nog wegbewegen.

</div>

#### Succescriterium 2.5.3 (Niveau A) — Label in naam

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er zijn geen elementen aangetroffen waarbij de toegankelijke naam de zichtbare
tekst niet bevat.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Staat er "Verzenden" op een knop, dan moet de toegankelijke naam die tekst ook
bevatten. Anders kan iemand die met spraakbediening werkt de knop niet aanroepen:
"klik Verzenden" werkt dan niet.

</div>

#### Succescriterium 2.5.4 (Niveau A) — Bewegingsactivering

<div class="verdict na">

**Dit succescriterium is niet van toepassing.**

Er is geen functionaliteit die door beweging van het apparaat wordt geactiveerd.

</div>

#### Succescriterium 2.5.7 (Niveau AA) — Sleepbewegingen

Alle functionaliteit die met slepen wordt bediend, kan ook met één aanwijzer
zonder slepen worden bediend.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er is geen functionaliteit aangetroffen die slepen vereist. De organisatieboom, de
filterlijsten en de kaarten worden met klikken bediend; er zijn geen
schuifregelaars of herschikbare lijsten.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Slepen is lastig of onmogelijk voor mensen met beperkte handfunctie, en voor wie
met oogbesturing of een schakelaar werkt. Nieuw in WCAG 2.2: er moet altijd een
alternatief zijn, bijvoorbeeld knoppen "omhoog" en "omlaag" naast een sleepbare
lijst.

</div>

#### Succescriterium 2.5.8 (Niveau AA) — Doelgrootte (minimum)

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Van de 61 gemeten bedieningselementen zijn er 5 kleiner dan 24 × 24 CSS-pixels.
Alle vijf zijn tekstlinks in de paginavoet ("Veelgestelde vragen", "Contact",
"Privacy", "Toegankelijkheid" en de versieregel). Deze vallen onder de uitzondering
**"inline"**: het doel bevindt zich in een zin of tekstblok.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Knoppen en andere bedieningselementen moeten minstens 24 × 24 CSS-pixels groot zijn,
zodat mensen met een motorische beperking of trillende handen ze kunnen raken.
Uitzonderingen zijn links binnen een lopende tekst en doelen die ver genoeg uit
elkaar staan.

</div>

---

## Principe 3 Begrijpelijk

_Informatie en de bediening van de gebruikersinterface moeten begrijpelijk zijn._

### Richtlijn 3.1 Leesbaar

#### Succescriterium 3.1.1 (Niveau A) — Taal van de pagina

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Op alle elf pagina's is `lang="nl"` aanwezig op het `<html>`-element.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Geef de taal van de pagina aan met een `lang`-attribuut, zodat voorleessoftware de
tekst met de juiste uitspraak voorleest. Zonder deze aanduiding leest een
Nederlandse tekst mogelijk met een Engelse uitspraak.

</div>

#### Succescriterium 3.1.2 (Niveau AA) — Taal van onderdelen

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

De interface bevat Engelse termen binnen Nederlandse tekst, met name rolnamen als
"UX designer", "Business Development Manager" en "Scrum Master". Deze zijn niet met
een `lang`-attribuut gemarkeerd. Voor vaktermen die deel zijn gaan uitmaken van het
Nederlandse jargon geldt een uitzondering; of die hier opgaat, vraagt een
inhoudelijk oordeel.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Wordt ergens een andere taal gebruikt dan de hoofdtaal van de pagina, dan hoort dat
in de code te worden aangegeven met `lang`. Voor losse woorden en voor jargon dat is
ingeburgerd, hoeft dat niet.

</div>

### Richtlijn 3.2 Voorspelbaar

#### Succescriterium 3.2.1 (Niveau A) — Bij focus

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Het focussen van een element veroorzaakt geen contextwijziging.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Er mag niets ingrijpends gebeuren zodra een element focus krijgt — dus vóór er
geklikt wordt. Een select die bij focus meteen naar een andere pagina springt, is
een klassiek voorbeeld van wat niet mag.

</div>

#### Succescriterium 3.2.2 (Niveau A) — Bij input

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

De filters in de zijbalk werken de lijst automatisch bij bij wijziging. Dat is een
verandering van content en geen contextwijziging in de zin van het criterium, maar
of de verandering voor een schermlezergebruiker begrijpelijk verloopt, is niet
getoetst. Zie ook 4.1.3.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Het invullen of wijzigen van een formulierveld mag niet automatisch een grote
verandering veroorzaken — zoals het laden van een nieuwe pagina — tenzij de
gebruiker daar vooraf over is geïnformeerd.

</div>

#### Succescriterium 3.2.3 (Niveau AA) — Consistente navigatie

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

De hoofdnavigatie, het gebruikersmenu en de paginavoet staan op alle onderzochte
pagina's in dezelfde relatieve volgorde.

</div>

#### Succescriterium 3.2.4 (Niveau AA) — Consistente identificatie

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Componenten met dezelfde functie worden consistent aangeduid.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Een onderdeel van de interface hoort altijd met dezelfde naam te worden aangeduid.
Noem een knop niet op de ene pagina "Opslaan" en op de andere "Bewaren".

</div>

#### Succescriterium 3.2.6 (Niveau A) — Consistente hulp

Als een pagina een manier biedt om hulp te vinden, staat die op elke pagina in
dezelfde relatieve volgorde.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Op **alle elf** onderzochte pagina's zijn de links "Veelgestelde vragen" en
"Contact" aanwezig, steeds in de paginavoet en steeds in dezelfde volgorde. De
contactpagina biedt zowel een e-mailadres als een verwijzing naar het
Mattermost-kanaal.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Nieuw in WCAG 2.2. Biedt een website hulp — contactgegevens, een
veelgestelde-vragenpagina, een chatfunctie — dan moet die hulp op elke pagina op
dezelfde plek staan. Mensen met een cognitieve beperking hoeven dan niet op elke
pagina opnieuw te zoeken waar ze terechtkunnen.

</div>

### Richtlijn 3.3 Assistentie bij invoer

#### Succescriterium 3.3.1 (Niveau A) — Fout identificatie

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

Formulierfouten worden server-side gerenderd en met `invalid` en `error-message`
aan het betreffende veld gekoppeld. Of de melding daadwerkelijk aan een schermlezer
wordt doorgegeven, is niet getoetst.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Zorg voor foutmeldingen die het veld benoemen waar de fout zit. Vermijd "dit veld is
verkeerd ingevuld"; noem de naam van het veld, zodat een blinde bezoeker weet waar
hij moet zijn.

</div>

#### Succescriterium 3.3.2 (Niveau A) — Labels of instructies

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Alle zichtbare invoervelden hebben in de accessibility tree een toegankelijke naam.
Voorbeeld: het zoekveld op `/beheer/gebruikers/` heeft de naam "Naam of e-mail
zoeken".

</div>

> **Kanttekening bij de meting.** Een eerste meting meldde 3 velden zonder label en
> 192 elementen zonder toegankelijke naam. Beide bleken **onjuist**: die elementen
> ontlenen hun naam aan inhoud die via een slot wordt doorgegeven, wat een eigen
> DOM-controle niet ziet. Toetsing via de accessibility tree van de browser gaf
> **0 zonder naam**.

<div class="explain">

**Uitleg van dit succescriterium**

Bied bij invoervelden duidelijke labels en instructies, zodat voor alle bezoekers
helder is wat er ingevuld moet worden. Een `placeholder` is geen label: die
verdwijnt zodra men begint te typen.

</div>

#### Succescriterium 3.3.3 (Niveau AA) — Foutsuggestie

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

Niet getoetst; vraagt het doorlopen van alle formulieren met foutieve invoer.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Bied waar mogelijk een suggestie ter verbetering, bijvoorbeeld "controleer of het
e-mailadres het formaat naam@domein.nl heeft". Dat helpt vooral mensen met een
cognitieve beperking.

</div>

#### Succescriterium 3.3.4 (Niveau AA) — Foutpreventie

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

Destructieve acties vragen bevestiging, maar een uitputtende controle van alle
wijzigende handelingen — waaronder het verwijderen van plaatsingen en gebruikers —
is niet uitgevoerd.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Bij handelingen met juridische of financiële gevolgen, of bij het wijzigen of
verwijderen van gegevens, moet de gebruiker de actie kunnen terugdraaien,
controleren of bevestigen.

</div>

#### Succescriterium 3.3.7 (Niveau A) — Overbodige invoer

Informatie die de gebruiker eerder heeft ingevoerd, wordt automatisch ingevuld of
is te kiezen, en hoeft niet opnieuw te worden ingetypt.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Bij het bewerken van een gebruiker zijn 12 van de 13 velden voorgevuld met de
bestaande gegevens; niets hoeft opnieuw te worden ingetypt. De applicatie kent
geen meerstapsformulieren waarin dezelfde gegevens twee keer worden gevraagd.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Nieuw in WCAG 2.2. Moet een gebruiker in stap 3 van een formulier nogmaals zijn
adres intypen dat hij in stap 1 al gaf, dan is dat overbodige invoer. Voor mensen
met een geheugenbeperking of een motorische beperking is dat een reële drempel.
Uitzonderingen gelden onder meer voor het opnieuw invoeren van een wachtwoord.

</div>

#### Succescriterium 3.3.8 (Niveau AA) — Toegankelijke authenticatie (minimaal)

Bij het inloggen is geen cognitieve test vereist, tenzij er een alternatief of
hulpmiddel beschikbaar is.

<div class="verdict na">

**Dit succescriterium is niet van toepassing.**

Wies kent geen eigen inlogformulier: de authenticatie verloopt via OIDC bij
Keycloak, dat onder een andere leverancier valt en buiten de scope van dit
onderzoek ligt. In de applicatie zelf zijn geen wachtwoordvelden en geen CAPTCHA
aangetroffen.

**Aanbeveling:** laat vaststellen of de Keycloak-inlogpagina aan dit criterium
voldoet, en leg dat vast in de toegankelijkheidsverklaring van die voorziening.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Nieuw in WCAG 2.2. Inloggen mag niet afhangen van een cognitieve test: een puzzel
oplossen, plaatjes herkennen, of een wachtwoord uit het hoofd overtypen zonder dat
plakken is toegestaan. Dat sluit mensen met een cognitieve beperking uit. Een
CAPTCHA die "vink alle stoplichten aan" vraagt, is het klassieke voorbeeld van wat
niet mag.

</div>

---

## Principe 4 Robuust

_Content moet voldoende robuust zijn om betrouwbaar geïnterpreteerd te worden door een breed scala van gebruikersagenten, waaronder hulptechnologieën._

### Richtlijn 4.1 Compatibel

> **Succescriterium 4.1.1 (Parsen) is vervallen.** Dit criterium is in WCAG 2.2
> geschrapt, omdat moderne browsers zelf omgaan met kleine fouten in de opmaak.
> Ter informatie: er is wel op gecontroleerd, en op alle elf pagina's zijn
> **0 dubbele ID's** aangetroffen.

#### Succescriterium 4.1.2 (Niveau A) — Naam, rol, waarde

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

Getoetst via de accessibility tree: **alle** interactieve elementen hebben een naam
en een rol (`/`: 61 van 61; `/beheer/gebruikers/`: 70 van 70). Dat is een sterke
aanwijzing. Het criterium vraagt echter ook dat _waarden_ en _statuswijzigingen_
correct worden doorgegeven — bij eigen componenten met een shadow root het meest
kwetsbare punt. Dit vraagt toetsing met hulpsoftware.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Voor alle bedieningselementen moet hulpsoftware kunnen bepalen: wat is het (rol),
hoe heet het (naam) en in welke stand staat het (waarde). Bij zelfgebouwde
componenten — een eigen keuzelijst, een eigen schakelaar — gaat dit vaak mis, omdat
de browser die betekenis niet vanzelf kent.

</div>

#### Succescriterium 4.1.3 (Niveau AA) — Statusberichten

<div class="verdict unknown">

**Over dit succescriterium kon geen uitspraak worden gedaan.**

Er zijn 20 live regions aangetroffen (`role="status"` en `role="alert"`), aangemaakt
door de componentbibliotheek. Of het aantal resultaten na het filteren en de
meldingen na het opslaan daadwerkelijk worden aangekondigd, is niet getoetst. Bij
een applicatie die lijsten bijwerkt zonder paginanavigatie is dit een reëel risico.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Verandert er iets op de pagina zonder dat de gebruiker daarheen navigeert — "12
resultaten gevonden", "opgeslagen", "er ging iets mis" — dan moet dat aan een
schermlezer worden aangekondigd via een live region. Anders merkt een blinde
gebruiker de verandering niet op.

</div>

---

## Onderzoeksgegevens

### A. Informatie over de opdracht

|                                   |                                                                                                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Onderzoeker**                   | Ontwikkelteam Wies, Rijksorganisatie voor Ontwikkeling, Digitalisering en Innovatie (ODI)                                                                           |
| **Opdrachtgever**                 | Rijksorganisatie voor Ontwikkeling, Digitalisering en Innovatie (ODI)                                                                                               |
| **Datum**                         | 19 augustus 2026                                                                                                                                                    |
| **Norm**                          | WCAG 2.2, niveau A en AA (via EN 301 549)                                                                                                                           |
| **Soort onderzoek**               | Volledig onderzoek van alle 55 succescriteria, uitgevoerd als **intern vooronderzoek**. Geen onafhankelijk onderzoek; niet alle criteria konden worden vastgesteld. |
| **Versie van dit document**       | 1.0                                                                                                                                                                 |
| **Onderzochte versie applicatie** | `main` @ `d072cf3b`                                                                                                                                                 |

> **Let op bij gebruik als onderbouwing.** DigiToegankelijk stelt eisen aan
> onderzoeksrapporten die als onderbouwing van een toegankelijkheidsverklaring
> dienen. Dit rapport voldoet aan de vormeisen (scope, steekproef,
> evaluatiemethode, browsers met versienummers, technologieën, score per
> succescriterium), maar **niet** aan de inhoudelijke eis dat alle 55
> succescriteria daadwerkelijk zijn beoordeeld: veertien konden niet worden
> vastgesteld. Daarnaast is het onderzoek niet onafhankelijk uitgevoerd. Voor
> status A of B van de verklaring is aanvullend, onafhankelijk onderzoek nodig.

### B. Informatie over het onderzoek

**Evaluatiemethode**
Dit onderzoek volgt de opzet van WCAG-EM (Website Accessibility Conformance
Evaluation Methodology): scope bepalen, steekproef samenstellen, per
succescriterium beoordelen en rapporteren. De stappen die toetsing met
hulpsoftware en met gebruikers vereisen zijn **niet** uitgevoerd; in zoverre is
de methode niet volledig gevolgd.

### Scope van het onderzoek

De ingelogde webapplicatie Wies. Buiten scope vallen: het Keycloak-inlogscherm
(andere leverancier), externe websites waarnaar wordt gelinkt, en de
beheerinterface van Django.

### Steekproef

| #   | Pagina                | URL                     | Kenmerken                                          |
| --- | --------------------- | ----------------------- | -------------------------------------------------- |
| 1   | Wie zit waar?         | `/`                     | Overzicht, filters, zoeken, zijpanelen, paginering |
| 2   | Aanvragen             | `/opdrachten/`          | Overzicht met filters en modals                    |
| 3   | Beheer — gebruikers   | `/beheer/gebruikers/`   | Tabel, formulier in modal                          |
| 4   | Beheer — labels       | `/beheer/labels/`       | Lijst met acties per rij                           |
| 5   | Beheer — merken       | `/beheer/merken/`       | Lijst, sheet met formulier                         |
| 6   | Beheer — organisaties | `/beheer/organisaties/` | Boomstructuur                                      |
| 7   | Mijn profiel          | `/profiel/`             | Detail met inline bewerken                         |
| 8   | Veelgestelde vragen   | `/faq/`                 | Tekst met accordeon                                |
| 9   | Contact               | `/contact/`             | Tekst met externe links                            |
| 10  | Privacy               | `/privacy/`             | Gegenereerde tekstpagina                           |
| 11  | Toegankelijkheid      | `/toegankelijkheid/`    | Tekst met afbeelding                               |

De 404-pagina is niet in de steekproef opgenomen. In de onderzoeksomgeving toont
Django zijn ontwikkelaarspagina; de productieversie gebruikt een eigen Nederlandse
foutpagina (`404.html`), die niet apart is getoetst.

### Gebruikte browsers en software

| Software                 | Versie                | Gebruikt voor                                                                                                                                          |
| ------------------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Chromium                 | **140.0.7339.16**     | Alle metingen                                                                                                                                          |
| Playwright               | **1.55.0**            | Aansturing van de browser                                                                                                                              |
| axe-core                 | **4.10.2**            | Geautomatiseerde toetsing                                                                                                                              |
| Chrome DevTools Protocol | via Playwright 1.55.0 | Uitlezen van de accessibility tree                                                                                                                     |
| Eigen meetscripts        | —                     | Contrast (incl. shadow DOM), koppenstructuur, tabvolgorde, focus, focus na htmx-swap, reflow, doelgrootte, tekstafstand, focusinsluiting, dubbele ID's |

**Instellingen.** Alle metingen zijn uitgevoerd in een schone browsersessie zonder
extensies, met een weergavekader van 1440 × 900 pixels tenzij anders vermeld.
axe-core is beperkt tot de regelsets `wcag2a`, `wcag2aa`, `wcag21a` en `wcag21aa`.

**ACT Rules Format.** axe-core implementeert regels uit het ACT Rules Format van
het W3C en publiceert per regel de bijbehorende ACT-regel-identificatie. Daarmee
voldoet de gebruikte automatische toetsing aan de eis dat testtools op
ACT-algoritmen gebaseerd zijn. De eigen meetscripts implementeren geen
ACT-regels; hun uitkomsten zijn steeds met een tweede methode of visueel
geverifieerd.

> **Niet gebruikt.** Er is niet getoetst met JAWS, NVDA, VoiceOver, ZoomText,
> spraakbediening of schakelbediening. Er is niet getoetst in Firefox, Safari of
> Edge, en niet op mobiele apparaten.

### C. Informatie over de getoetste applicatie

**Basisniveau van toegankelijkheidsondersteuning**

Wies zou moeten werken met alle gangbare browsers en gangbare hulpapparatuur.
Concreet gaat dit onderzoek uit van: Chromium-, Firefox- en Safari-gebaseerde
browsers in een actuele versie, in combinatie met schermlezers (JAWS, NVDA,
VoiceOver), schermvergroters en spraak- of schakelbediening. Er is bij dit
onderzoek van uitgegaan dat alle door het W3C uitgebrachte technieken door
hulpsoftware worden ondersteund en dus gebruikt mogen worden.

**Let op:** dit basisniveau is het uitgangspunt, niet het getoetste bereik. Er is
uitsluitend gemeten in Chromium en zonder hulpsoftware (zie hierboven). Of het
gestelde basisniveau daadwerkelijk wordt gehaald, is met dit onderzoek **niet
vastgesteld**.

**Technologieën van de applicatie**

Gebruikt zijn de technologieën HTML5, CSS, JavaScript (inclusief de frameworks
htmx en Lit voor webcomponenten), WAI-ARIA en de DOM inclusief Shadow DOM,
waarvoor technieken zijn gedocumenteerd in
https://www.w3.org/WAI/WCAG22/Techniques/. De applicatie maakt gebruik van de
componentbibliotheek @nldd/design-system. Er worden geen PDF-, SMIL- of
Silverlight-technologieën toegepast.

**Bereik van geautomatiseerde toetsing**

Wies is opgebouwd uit NLDD-webcomponenten. Het overgrote deel van de interface
staat daardoor in een shadow root, buiten het bereik van standaard
toetsingsgereedschap.

|                         | Aantal elementen |
| ----------------------- | ---------------- |
| In het gewone document  | 638              |
| In shadow roots         | **2.310**        |
| Aandeel in shadow roots | **≈ 78 %**       |

Dit is geverifieerd door bewust fouten te injecteren:

| Injectie                 | Locatie         | Gedetecteerd door axe-core |
| ------------------------ | --------------- | -------------------------- |
| `<img>` zonder `alt`     | gewone document | ja                         |
| Tekst met contrast 1,9:1 | gewone document | ja                         |
| Tekst met contrast 1,9:1 | shadow root     | **nee**                    |

Het resultaat "0 overtredingen" van axe-core geldt daarom uitsluitend voor de
± 22 % van de interface die in het gewone document staat, en is op zichzelf geen
bewijs van conformiteit. De contrast-, structuur- en naamgevingstoetsen zijn zo
uitgevoerd dat zij shadow roots wél doorlopen, respectievelijk via de accessibility
tree.

### Afhankelijke technologie

HTML5, CSS, WAI-ARIA, ECMAScript (htmx en Lit-webcomponenten), DOM inclusief
Shadow DOM.

### Beperkingen van dit onderzoek

**1. Geen onafhankelijk onderzoek.** Uitgevoerd door het eigen ontwikkelteam. Voor
het register is een onafhankelijk onderzoek vereist.

**2. Geen toetsing met hulpsoftware.** Er is niet getest met JAWS, NVDA, VoiceOver,
spraakbediening of schakelbediening. Tien succescriteria blijven daardoor open,
waaronder 4.1.2 en 4.1.3, die bij een applicatie van eigen webcomponenten juist het
kwetsbaarst zijn.

**3. Geen gebruikerstest.** Er zijn geen mensen met een beperking bij het onderzoek
betrokken.

**4. Steekproef niet volledig.** De 404-pagina ontbreekt, en van de processen
(opdracht aanmaken, teamlid toevoegen, onboarding) zijn alleen de beginpagina's
getoetst.

**5. Eén browser, één platform.** Chromium op desktop. Niet getoetst in Firefox,
Safari of Edge, en niet op mobiele apparaten.

**6. Meetfouten zijn opgetreden.** Zeven eigen metingen leverden onjuiste
bevindingen op, die pas bij verificatie sneuvelden. De laatste twee kwamen uit de
vervolgmeting van bevinding 2:

| Onjuiste meting                         | Werkelijkheid           | Oorzaak                                                                       |
| --------------------------------------- | ----------------------- | ----------------------------------------------------------------------------- |
| 910 contrastfouten                      | 0                       | `oklch()`-waarden als RGB gelezen                                             |
| 8 van 10 tabstops zonder focusring      | Alle zichtbaar          | Ring wordt in de shadow root getekend                                         |
| 192 elementen zonder toegankelijke naam | 0                       | Naam komt uit inhoud die via een slot wordt doorgegeven                       |
| Sheet sluit de focus niet in            | Sluit wel in (9 van 12) | Detectie kon de shadow-grens niet oversteken                                  |
| 16 tabstops met bedekte focus           | Geen enkele bedekt      | `elementFromPoint` gaf het omhullende component terug, niet een bedekker      |
| Focus staat niet in het geswapte paneel | Staat er wel in         | `#side-panel-content` zit _binnen_ de sheet; de check keek een niveau te laag |
| Updates-tab niet met Tab bereikbaar     | Werkt zoals bedoeld     | Roving tabindex: binnen een tabbar navigeer je met de pijltjes                |

Dat een geautomatiseerde uitkomst een plausibele vorm heeft, betekent niet dat hij
klopt. Elke bevinding in dit rapport is daarom tegen de werkelijkheid getoetst — via
een tweede meetmethode, visuele controle of de accessibility tree. Waar dat niet
lukte, staat "niet vastgesteld" in plaats van een oordeel.

### Geadviseerde vervolgstappen

| Stap                                            | Waarom                                              | Prioriteit |
| ----------------------------------------------- | --------------------------------------------------- | ---------- |
| 1. Bevinding 1 oplossen (koppenstructuur)       | Niveau A, kleine wijziging in één bestand           | Hoog       |
| 2. Bevinding 2 oplossen (focus na bijwerken)    | Niveau A, raakt de kern van de applicatie — PR #638 | Hoog       |
| 3. Toetsing met schermlezer (NVDA en VoiceOver) | Sluit de tien openstaande criteria                  | Hoog       |
| 4. Onafhankelijk WCAG-EM-onderzoek              | Vereist voor de toegankelijkheidsverklaring         | Hoog       |
| 5. Issue #600 bijwerken                         | Het skiplink-deel is achterhaald                    | Laag       |
| 6. axe-core opnemen in de bouwstraat            | Voorkomt regressie in het gewone document           | Middel     |
| 7. 404-pagina en processen alsnog toetsen       | Ontbraken in de steekproef                          | Middel     |

---

<div class="footer-note">

**Herleidbaarheid.** Alle cijfers in dit rapport komen uit meetscripts die zijn
uitgevoerd tegen een draaiende instantie van `main` @ `d072cf3b` op 19 augustus 2026. De scripts zijn beschikbaar bij het ontwikkelteam, zodat de metingen
herhaald kunnen worden.

</div>

<style>
body {
  max-width: 60rem;
  margin: 0 auto;
  padding: 3rem 1.5rem 6rem;
  font-family: "RijksSans", system-ui, -apple-system, sans-serif;
  line-height: 1.68;
  color: var(--fg);
  background: var(--bg);
}
:root {
  --bg: #ffffff; --fg: #1a1d21; --muted: #55627a; --rule: #d6dbe3;
  --accent: #154273; --accent-soft: #f0f4f9;
  --pass-bg: #eef7f0; --pass-br: #2b7a3d;
  --fail-bg: #fdf1f2; --fail-br: #a8202a;
  --unk-bg: #fff8e6;  --unk-br: #c99400;
  --na-bg: #f2f3f5;   --na-br: #8b95a5;
  --explain-bg: #f7f9fc;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #14171c; --fg: #e6e9ee; --muted: #a4aebd; --rule: #2c333d;
    --accent: #7cadde; --accent-soft: #1b222c;
    --pass-bg: #16241a; --pass-br: #4e9c62;
    --fail-bg: #2b1a1c; --fail-br: #c9646d;
    --unk-bg: #2a2413;  --unk-br: #a98a10;
    --na-bg: #1c2027;   --na-br: #6b7585;
    --explain-bg: #1a1f27;
  }
}
:root[data-theme="dark"] {
  --bg: #14171c; --fg: #e6e9ee; --muted: #a4aebd; --rule: #2c333d;
  --accent: #7cadde; --accent-soft: #1b222c;
  --pass-bg: #16241a; --pass-br: #4e9c62;
  --fail-bg: #2b1a1c; --fail-br: #c9646d;
  --unk-bg: #2a2413;  --unk-br: #a98a10;
  --na-bg: #1c2027;   --na-br: #6b7585;
  --explain-bg: #1a1f27;
}
.cover { padding: 3.5rem 0 2.5rem; border-bottom: 4px solid var(--accent); margin-bottom: .5rem; }
.cover h1 { font-size: 2.4rem; margin: 0 0 .3rem; letter-spacing: -0.015em; border: none; padding: 0; }
.cover h2 { font-size: 1.15rem; font-weight: 500; color: var(--muted);
  margin: 0 0 1.8rem; border: none; padding: 0; }
.cover p { margin: .25rem 0; }
h1 { font-size: 2.1rem; line-height: 1.2; }
h2 {
  font-size: 1.5rem; margin: 3.4rem 0 1rem; padding-top: 1.7rem;
  border-top: 3px solid var(--accent); letter-spacing: -0.01em;
}
h3 { font-size: 1.18rem; margin: 2.6rem 0 .6rem; color: var(--accent); }
h4 {
  font-size: 1.02rem; margin: 2.2rem 0 .5rem; padding-bottom: .35rem;
  border-bottom: 1px solid var(--rule);
}
p, li { font-size: .95rem; }
a { color: var(--accent); }
hr { border: 0; border-top: 1px solid var(--rule); margin: 2.8rem 0; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0 1.5rem; font-size: .9rem; }
th, td { text-align: left; padding: .55rem .7rem; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font-weight: 650; color: var(--muted); font-size: .83rem; letter-spacing: .02em; }
tbody tr:last-child td { border-bottom: none; }
.verdict {
  margin: 1rem 0; padding: .8rem 1rem; border-left: 4px solid; border-radius: 0 5px 5px 0;
  font-size: .93rem;
}
.verdict p:first-child { margin-top: 0; }
.verdict p:last-child { margin-bottom: 0; }
.verdict table { margin: .6rem 0 0; }
.verdict.pass { background: var(--pass-bg); border-color: var(--pass-br); }
.verdict.fail { background: var(--fail-bg); border-color: var(--fail-br); }
.verdict.unknown { background: var(--unk-bg); border-color: var(--unk-br); }
.verdict.na { background: var(--na-bg); border-color: var(--na-br); }
.explain {
  margin: 1.2rem 0 1.8rem; padding: .9rem 1.1rem;
  background: var(--explain-bg); border: 1px solid var(--rule); border-radius: 6px;
  font-size: .89rem;
}
.explain p:first-child { margin-top: 0; font-weight: 650; color: var(--muted); }
.explain p:last-child, .explain ul:last-child { margin-bottom: 0; }
.explain li { font-size: .89rem; }
blockquote {
  margin: 1.3rem 0; padding: .85rem 1.1rem;
  background: var(--unk-bg); border-left: 4px solid var(--unk-br);
  border-radius: 0 5px 5px 0;
}
blockquote p { margin: .3rem 0; font-size: .91rem; }
pre {
  background: var(--accent-soft); border: 1px solid var(--rule); border-radius: 6px;
  padding: .85rem 1rem; overflow-x: auto; font-size: .84rem; line-height: 1.55;
}
code { font-size: .88em; }
:not(pre) > code { background: var(--accent-soft); padding: .12em .35em; border-radius: 3px; }
.footer-note {
  margin-top: 3rem; padding-top: 1.2rem; border-top: 1px solid var(--rule);
  color: var(--muted); font-size: .87rem;
}
@media (max-width: 640px) {
  body { padding: 1.5rem 1rem 4rem; }
  table { font-size: .82rem; }
  .cover h1 { font-size: 1.8rem; }
}
</style>
