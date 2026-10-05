<title>Toegankelijkheidsonderzoek Wies</title>

<div class="cover">

# Onderzoek Wies

## Rijksorganisatie voor Ontwikkeling, Digitalisering en Innovatie

**WCAG 2.2 — Niveau AA**

Onderzoek afgerond op 30 september 2026 · versie 3.0

</div>

---

## Inhoudsopgave

- [Inleiding](#inleiding)
- [A. Informatie over de opdracht](#a-informatie-over-de-opdracht)
- [B. Informatie over het onderzoek](#b-informatie-over-het-onderzoek)
- [C. Informatie over de getoetste applicatie](#c-informatie-over-de-getoetste-applicatie)
- [Beoordeling per succescriterium](#beoordeling-per-succescriterium)
- [D. Resultaten van het onderzoek](#d-resultaten-van-het-onderzoek)
  - [Principe 1 Waarneembaar](#principe-1-waarneembaar)
  - [Principe 2 Bedienbaar](#principe-2-bedienbaar)
  - [Principe 3 Begrijpelijk](#principe-3-begrijpelijk)
  - [Principe 4 Robuust](#principe-4-robuust)
- [Bijlagen](#bijlagen)

---

## Inleiding

Het toegankelijkheidsonderzoek naar Wies is uitgevoerd op de live versie
(`main`) en afgerond op 30 september 2026. Alle 55 succescriteria van WCAG 2.2
op niveau A en AA zijn beoordeeld: met geautomatiseerde toetsing, met eigen
instrumentele metingen in drie browsers, en met de schermlezer VoiceOver. Dit
rapport laat zien in hoeverre de applicatie op dit moment voldoet aan de
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
> ontwikkelteam, met geautomatiseerde toetsing, instrumentele metingen en een
> toets met de schermlezer VoiceOver. Alle 55 succescriteria zijn beoordeeld.

---

---

## A. Informatie over de opdracht

| Onderdeel                         | Gegeven                                                                                                                                                                                          |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Onderzoeker**                   | R. Rouwhof, ontwikkelteam Wies, Rijksorganisatie voor Ontwikkeling, Digitalisering en Innovatie (ODI)                                                                                            |
| **Onderzoeksdatum**               | 30 september 2026                                                                                                                                                                                |
| **Opdrachtgever**                 | Rijksorganisatie voor Ontwikkeling, Digitalisering en Innovatie (ODI)                                                                                                                            |
| **Norm**                          | WCAG 2.2, niveau A en AA (via EN 301 549)                                                                                                                                                        |
| **Soort onderzoek**               | Volledig onderzoek van alle 55 succescriteria, intern uitgevoerd: geautomatiseerde toetsing, instrumentele metingen in drie browsers en een toets met schermlezer. Geen onafhankelijk onderzoek. |
| **Versie van dit document**       | 3.0                                                                                                                                                                                              |
| **Onderzochte versie applicatie** | `main`, stand 30 september 2026 (@ `c342ff2`)                                                                                                                                                    |

---

## B. Informatie over het onderzoek

### Evaluatiemethode

Dit onderzoek volgt de opzet van WCAG-EM (Website Accessibility Conformance
Evaluation Methodology): scope bepalen, steekproef samenstellen, per
succescriterium beoordelen en rapporteren. De stappen die toetsing met
gebruikers vereisen zijn **niet** uitgevoerd. Per succescriterium is de best
passende methode gebruikt: axe-core voor wat geautomatiseerd te toetsen is, eigen
meetscripts in Chromium, Edge en Firefox voor wat een browser kan meten
(contrast, koppen, focus, reflow, doelgrootte), en de schermlezer VoiceOver voor
wat alleen hoorbaar is; zie [Schermlezertoets](#schermlezertoets).

### Scope van het onderzoek

De ingelogde webapplicatie Wies. Buiten scope vallen: het Keycloak-inlogscherm
(andere leverancier), externe websites waarnaar wordt gelinkt, en de
beheerinterface van Django.

**Uitzonderingen en specifieke situaties.**

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

### Samenvatting

Alle 55 succescriteria zijn beoordeeld. Op **47 van de 55** wordt voldaan; de
overige acht zijn niet van toepassing. Er zijn geen afwijkingen gevonden.

De applicatie voldoet daarmee aan de vereisten voor WCAG 2.2, niveau AA, voor
zover dit onderzoek reikt.

Onderstaande tabel geeft per principe het aantal succescriteria waaraan wordt
voldaan, van alle 55 van WCAG 2.2 op niveau A en AA. De noemer telt ook de
criteria die niet van toepassing zijn; die zijn in de laatste kolom apart
vermeld. Elk criterium dat van toepassing is, voldoet.

| Principe         | Niveau A    | Niveau AA   | Totaal      | Waarvan n.v.t. |
| ---------------- | ----------- | ----------- | ----------- | -------------- |
| **Waarneembaar** | 5 / 9       | 9 / 11      | 14 / 20     | 6              |
| **Bedienbaar**   | 13 / 14     | 6 / 6       | 19 / 20     | 1              |
| **Begrijpelijk** | 7 / 7       | 5 / 6       | 12 / 13     | 1              |
| **Robuust**      | 1 / 1       | 1 / 1       | 2 / 2       | 0              |
| **Totaal**       | **26 / 31** | **21 / 24** | **47 / 55** | **8**          |

**Uitgeschreven.** Van de 55 succescriteria voldoen er 47. Acht zijn niet van
toepassing omdat de applicatie geen audio, video of bewegingsbediening bevat en
de authenticatie bij een externe leverancier ligt.

De aandacht ging in dit onderzoek vooral uit naar wat een schermlezer merkt van
een pagina die met htmx in delen ververst: waar de focus heen gaat (3.2.2), of
het aantal resultaten en de bevestiging na opslaan worden aangekondigd (4.1.3),
en of de foutmelding van een afgewezen formulier het veld bereikt over de
shadow-grens van het component heen (3.3.1, 3.3.3). Die vier zijn met VoiceOver
getoetst en voldoen.

#### Verdeling van de uitkomsten

| Uitkomst            | Aantal | Succescriteria                                         |
| ------------------- | ------ | ------------------------------------------------------ |
| Voldoet             | 47     | zie de hoofdstukken hieronder                          |
| Voldoet niet        | 0      |                                                        |
| Niet vastgesteld    | 0      |                                                        |
| Niet van toepassing | 8      | 1.2.1, 1.2.2, 1.2.3, 1.2.4, 1.2.5, 1.4.2, 2.5.4, 3.3.8 |
| **Totaal**          | **55** |                                                        |

#### Nieuw in WCAG 2.2

WCAG 2.2 voegt zes succescriteria toe op niveau A en AA, en laat 4.1.1 (Parsen)
vervallen. De nieuwe criteria zijn in dit onderzoek meegenomen:

| Succescriterium                              | Niveau | Status              |
| -------------------------------------------- | ------ | ------------------- |
| 2.4.11 Focus niet bedekt (minimaal)          | AA     | Voldoet             |
| 2.5.7 Sleepbewegingen                        | AA     | Voldoet             |
| 2.5.8 Doelgrootte (minimaal)                 | AA     | Voldoet             |
| 3.2.6 Consistente hulp                       | A      | Voldoet             |
| 3.3.7 Overbodige invoer                      | A      | Voldoet             |
| 3.3.8 Toegankelijke authenticatie (minimaal) | AA     | Niet van toepassing |

### Beoordeling per succescriterium

Alle 55 succescriteria van WCAG 2.2 op niveau A en AA, met het oordeel over
de onderzochte set pagina's. De onderbouwing per criterium staat in
[hoofdstuk D](#d-resultaten-van-het-onderzoek).

**Waarneembaar**

| Criterium | Omschrijving                                                  | Niveau | Resultaat           |
| --------- | ------------------------------------------------------------- | ------ | ------------------- |
| 1.1.1     | Niet-tekstuele content                                        | A      | Voldoet             |
| 1.2.1     | Louter-geluid en louter-videobeeld (vooraf opgenomen)         | A      | Niet van toepassing |
| 1.2.2     | Ondertiteling voor doven en slechthorenden (vooraf opgenomen) | A      | Niet van toepassing |
| 1.2.3     | Audiodescriptie of media-alternatief (vooraf opgenomen)       | A      | Niet van toepassing |
| 1.2.4     | Ondertiteling voor doven en slechthorenden (live)             | AA     | Niet van toepassing |
| 1.2.5     | Audiodescriptie (vooraf opgenomen)                            | AA     | Niet van toepassing |
| 1.3.1     | Info en relaties                                              | A      | Voldoet             |
| 1.3.2     | Betekenisvolle volgorde                                       | A      | Voldoet             |
| 1.3.3     | Zintuiglijke eigenschappen                                    | A      | Voldoet             |
| 1.3.4     | Oriëntatie                                                    | AA     | Voldoet             |
| 1.3.5     | Inputdoel identificeren                                       | AA     | Voldoet             |
| 1.4.1     | Gebruik van kleur                                             | A      | Voldoet             |
| 1.4.2     | Geluidsbediening                                              | A      | Niet van toepassing |
| 1.4.3     | Contrast (minimum)                                            | AA     | Voldoet             |
| 1.4.4     | Herschalen van tekst                                          | AA     | Voldoet             |
| 1.4.5     | Afbeeldingen van tekst                                        | AA     | Voldoet             |
| 1.4.10    | Dynamisch aanpassen (reflow)                                  | AA     | Voldoet             |
| 1.4.11    | Niet-tekstueel contrast                                       | AA     | Voldoet             |
| 1.4.12    | Tekstafstand                                                  | AA     | Voldoet             |
| 1.4.13    | Content bij aanwijzen of focussen                             | AA     | Voldoet             |

**Bedienbaar**

| Criterium | Omschrijving                          | Niveau | Resultaat           |
| --------- | ------------------------------------- | ------ | ------------------- |
| 2.1.1     | Toetsenbord                           | A      | Voldoet             |
| 2.1.2     | Geen toetsenbordval                   | A      | Voldoet             |
| 2.1.4     | Sneltoetsen tekentoets                | A      | Voldoet             |
| 2.2.1     | Timing aanpasbaar                     | A      | Voldoet             |
| 2.2.2     | Pauzeren, stoppen, verbergen          | A      | Voldoet             |
| 2.3.1     | Drie flitsen of beneden drempelwaarde | A      | Voldoet             |
| 2.4.1     | Blokken omzeilen                      | A      | Voldoet             |
| 2.4.2     | Paginatitel                           | A      | Voldoet             |
| 2.4.3     | Focus volgorde                        | A      | Voldoet             |
| 2.4.4     | Linkdoel (in context)                 | A      | Voldoet             |
| 2.4.5     | Meerdere manieren                     | AA     | Voldoet             |
| 2.4.6     | Koppen en labels                      | AA     | Voldoet             |
| 2.4.7     | Focus zichtbaar                       | AA     | Voldoet             |
| 2.4.11    | Focus niet bedekt (minimaal)          | AA     | Voldoet             |
| 2.5.1     | Bewegingen aanwijzer                  | A      | Voldoet             |
| 2.5.2     | Annulering aanwijzer                  | A      | Voldoet             |
| 2.5.3     | Label in naam                         | A      | Voldoet             |
| 2.5.4     | Bewegingsactivering                   | A      | Niet van toepassing |
| 2.5.7     | Sleepbewegingen                       | AA     | Voldoet             |
| 2.5.8     | Doelgrootte (minimum)                 | AA     | Voldoet             |

**Begrijpelijk**

| Criterium | Omschrijving                           | Niveau | Resultaat           |
| --------- | -------------------------------------- | ------ | ------------------- |
| 3.1.1     | Taal van de pagina                     | A      | Voldoet             |
| 3.1.2     | Taal van onderdelen                    | AA     | Voldoet             |
| 3.2.1     | Bij focus                              | A      | Voldoet             |
| 3.2.2     | Bij input                              | A      | Voldoet             |
| 3.2.3     | Consistente navigatie                  | AA     | Voldoet             |
| 3.2.4     | Consistente identificatie              | AA     | Voldoet             |
| 3.2.6     | Consistente hulp                       | A      | Voldoet             |
| 3.3.1     | Fout identificatie                     | A      | Voldoet             |
| 3.3.2     | Labels of instructies                  | A      | Voldoet             |
| 3.3.3     | Foutsuggestie                          | AA     | Voldoet             |
| 3.3.4     | Foutpreventie                          | AA     | Voldoet             |
| 3.3.7     | Overbodige invoer                      | A      | Voldoet             |
| 3.3.8     | Toegankelijke authenticatie (minimaal) | AA     | Niet van toepassing |

**Robuust**

| Criterium | Omschrijving      | Niveau | Resultaat |
| --------- | ----------------- | ------ | --------- |
| 4.1.2     | Naam, rol, waarde | A      | Voldoet   |
| 4.1.3     | Statusberichten   | AA     | Voldoet   |

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

De instrumentele metingen zijn gedaan op alle elf pagina's in Chromium, en op
pagina 1, 2, 3, 7 en 8 daarnaast in Edge en Firefox. De schermlezertoets volgde
de steekproef in de volgorde van de toetsronde: eerst pagina 1, 2, 3 en 7, waar
de bediening zit, daarna de tekstpagina's.

### Gebruikte browsers en software

| Software                 | Versie                                 | Gebruikt voor                                                                                                                                          |
| ------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Chromium                 | **140.0.7339.16** en **151.0.7922.34** | Geautomatiseerde toetsing en instrumentele metingen                                                                                                    |
| Microsoft Edge           | **152.0.4191.66**                      | Instrumentele metingen                                                                                                                                 |
| Firefox                  | **153.0**                              | Instrumentele metingen                                                                                                                                 |
| Playwright               | **1.55.0** en **1.62.0**               | Aansturing van de browsers                                                                                                                             |
| axe-core                 | **4.10.2**                             | Geautomatiseerde toetsing                                                                                                                              |
| Chrome DevTools Protocol | via Playwright                         | Uitlezen van de accessibility tree                                                                                                                     |
| Eigen meetscripts        | —                                      | Contrast (incl. shadow DOM), koppenstructuur, tabvolgorde, focus, focus na htmx-swap, reflow, doelgrootte, tekstafstand, focusinsluiting, dubbele ID's |

**Instellingen.** Alle metingen zijn uitgevoerd in een schone browsersessie zonder
extensies, met een weergavekader van 1440 × 900 pixels tenzij anders vermeld.
axe-core is beperkt tot de regelsets `wcag2a`, `wcag2aa`, `wcag21a` en `wcag21aa`.

**ACT Rules Format.** axe-core implementeert regels uit het ACT Rules Format van
het W3C en publiceert per regel de bijbehorende ACT-regel-identificatie. Daarmee
voldoet de gebruikte automatische toetsing aan de eis dat testtools op
ACT-algoritmen gebaseerd zijn. De eigen meetscripts implementeren geen
ACT-regels; hun uitkomsten zijn steeds met een tweede methode of visueel
geverifieerd.

| VoiceOver | macOS **14.4** | Schermlezertoets |
| Google Chrome | **153.0.8010.48** | Schermlezertoets, handmatige ronde |
| Google Chrome for Testing | **151.0.7922.34** via Playwright 1.62.0 | Schermlezertoets, geïnstrumenteerde ronde: toetsaanslagen via macOS, uitspraak van VoiceOver uitgelezen via zijn AppleScript-koppeling |

### Schermlezertoets

Veertien succescriteria zijn alleen vast te stellen met een schermlezer: wat er
wordt uitgesproken, is de meting. Die zijn met VoiceOver op macOS 14.4 getoetst,
op twee manieren die elkaar controleren.

**Handmatig.** De onderzoeker doorloopt de steekproef met VoiceOver in Chrome
153, met het scherm uit, en noteert per criterium wat hij hoort.

**Geïnstrumenteerd.** Dezelfde handelingen in Chrome for Testing 151 met
dezelfde VoiceOver, waarbij de toetsaanslagen via macOS gaan zodat VoiceOver ze
ziet zoals bij een gebruiker. Wat VoiceOver uitspreekt, is uitgelezen via zijn
AppleScript-koppeling (`last phrase`); die uitspraken staan in dit rapport
letterlijk aangehaald.

Vier criteria die geen schermlezer vragen (1.1.1, 1.3.2, 2.4.6, 3.1.2) zijn
beoordeeld op de toegankelijkheidsboom van alle elf pagina's; 1.4.11 is in het
donkere thema gemeten als pixelcontrast op schermafbeeldingen.

Twee eigenschappen van deze meetwijze zijn van belang bij het herhalen ervan.
VoiceOver reageert niet op toetsaanslagen die een testtool rechtstreeks in de
pagina stuurt: zijn cursor blijft dan op de adresbalk staan en de pagina is voor
hem stil. En een live region die verandert vlak na een volledige paginalading
wordt niet uitgesproken, beleefd noch assertief; de aankondiging van de nieuwe
pagina gaat voor.

---

## C. Informatie over de getoetste applicatie

### Basisniveau van toegankelijkheidsondersteuning

Wies zou moeten werken met alle gangbare browsers en gangbare hulpapparatuur.
Concreet gaat dit onderzoek uit van: Chromium-, Firefox- en Safari-gebaseerde
browsers in een actuele versie, in combinatie met schermlezers (JAWS, NVDA,
VoiceOver), schermvergroters en spraak- of schakelbediening. Er is bij dit
onderzoek van uitgegaan dat alle door het W3C uitgebrachte technieken door
hulpsoftware worden ondersteund en dus gebruikt mogen worden.

**Let op:** dit basisniveau is het uitgangspunt, niet het getoetste bereik. Er is
gemeten in Chromium, Edge en Firefox op macOS, zonder hulpsoftware (zie hierboven). Of het
gestelde basisniveau daadwerkelijk wordt gehaald, is met dit onderzoek **niet
vastgesteld**.

### Technologieën van de applicatie

Gebruikt zijn de technologieën HTML5, CSS, JavaScript (inclusief de frameworks
htmx en Lit voor webcomponenten), WAI-ARIA en de DOM inclusief Shadow DOM,
waarvoor technieken zijn gedocumenteerd in
https://www.w3.org/WAI/WCAG22/Techniques/. De applicatie maakt gebruik van de
componentbibliotheek @nldd/design-system. Er worden geen PDF-, SMIL- of
Silverlight-technologieën toegepast.

### Bereik van geautomatiseerde toetsing

Wies is opgebouwd uit NLDD-webcomponenten. Het overgrote deel van de interface
staat daardoor in een shadow root, buiten het bereik van standaard
toetsingsgereedschap.

| Waar                    | Aantal elementen |
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

---

## D. Resultaten van het onderzoek

Per succescriterium staat hieronder het oordeel: voldoet, voldoet niet, niet van
toepassing, of niet vastgesteld. Bij een afwijking staat wat precies is gevonden, op
welke pagina's, en hoe het op te lossen is. Elk criterium sluit af met een korte uitleg
van wat het vraagt.

### Principe 1 Waarneembaar

_Informatie en componenten van de gebruikersinterface moeten toonbaar zijn aan gebruikers op voor hen waarneembare wijze._

#### Richtlijn 1.1 Tekstalternatieven

_Lever tekstalternatieven voor alle niet-tekstuele content, zodat die veranderd kan worden in andere vormen die mensen nodig hebben._

##### Succescriterium 1.1.1 (Niveau A) — Niet-tekstuele content

Alle niet-tekstuele content die aan de gebruiker wordt gepresenteerd, heeft een
tekstalternatief dat een gelijkwaardig doel dient.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

De toegankelijkheidsboom van alle elf pagina's bevat geen
enkele afbeelding, icoon of knop zonder naam. De 265 SVG-elementen zonder naam
uit het eerste onderzoek zijn de iconen in shadow roots: naast een tekstlabel
zijn ze voor de schermlezer verborgen, en icoonknoppen zonder tekst hebben een
eigen naam ("Acties voor opdrachtgever", "Opdracht verwijderen"). Het logo heet
"Rijkswapen - Rijksoverheid"; het toegankelijkheidslabel heeft een beschrijvende
`alt`-tekst.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Alle belangrijke niet-tekstuele content zoals afbeeldingen, knoppen en
formulier-invoervelden moeten een tekstueel alternatief of naam hebben. Dan kan de
voorleessoftware van blinde bezoekers die informatie voorlezen. Iconen die naast
een tekstlabel staan en niets toevoegen, horen juist `aria-hidden="true"` te
krijgen, zodat ze niet dubbel worden voorgelezen.

</div>

#### Richtlijn 1.2 Op tijd gebaseerde media

De applicatie bevat geen audio en geen video. Gemeten op alle elf onderzochte
pagina's: `<video>` 0, `<audio>` 0, `<iframe>` 0. De onderstaande vijf
succescriteria zijn daarom alle niet van toepassing.

| Succescriterium                                                     | Niveau | Status              |
| ------------------------------------------------------------------- | ------ | ------------------- |
| 1.2.1 Louter-geluid en louter-videobeeld (vooraf opgenomen)         | A      | Niet van toepassing |
| 1.2.2 Ondertiteling voor doven en slechthorenden (vooraf opgenomen) | A      | Niet van toepassing |
| 1.2.3 Audiodescriptie of media-alternatief (vooraf opgenomen)       | A      | Niet van toepassing |
| 1.2.4 Ondertitels voor doven en slechthorenden (live)               | AA     | Niet van toepassing |
| 1.2.5 Audiodescriptie (vooraf opgenomen)                            | AA     | Niet van toepassing |

<div class="explain">

**Uitleg van deze succescriteria**

Voor video en audio gelden aparte eisen: ondertiteling voor dove en slechthorende
bezoekers, en audiodescriptie of een uitgeschreven transcript voor blinde
bezoekers. Zodra Wies video of audio gaat aanbieden (bijvoorbeeld een
instructiefilmpje bij de onboarding), worden deze criteria alsnog van toepassing
en moeten ze opnieuw worden beoordeeld.

</div>

#### Richtlijn 1.3 Aanpasbaar

_Creëer content die op verschillende manieren gepresenteerd kan worden zonder verlies van informatie of structuur._

##### Succescriterium 1.3.1 (Niveau A) — Info en relaties

Informatie, structuur en relaties overgebracht door presentatie kunnen door
software bepaald worden of zijn beschikbaar in tekst.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

De koppenreeks is sluitend en slaat geen niveau over.

</div>

De koppenstructuur is op alle pagina's van de steekproef gemeten, in de
toegankelijkheidsboom en in de broncode, op 1440 px en op 375 px. De reeks loopt
van `<h1>` naar `<h2>` zonder een niveau over te slaan. Op `/` en `/opdrachten/`
dragen de filtergroepen in de zijbalk `<h2>` en de kaarttitels eveneens `<h2>`,
onder de `<h1>` van de pagina:

```
H2: Opdrachtgever          ← zijbalk
H2: Rol
H1: Wie zit waar?          ← paginatitel
H2: Laura van Leeuwen      ← kaarten
H2: Laura Popov
```

VoiceOver spreekt ze uit als "heading level 2 Opdrachtgever", "heading level 2
Rol", "heading level 2 Expertise".

Dat de zijbalk in bronvolgorde vóór de `<h1>` staat, is een keuze van het
paginaraamwerk; met een sluitende koppenreeks is dat geen afwijking. Onder
768 px valt de zijbalk weg en begint de reeks bij de `<h1>`.

Verder zijn de lijsten, tabellen en formuliervelden op semantiek gecontroleerd:
lijsten gebruiken `<ul>`/`<li>`, de tabellen op de beheerpagina's hebben
kolomkoppen, en elk invoerveld heeft een label dat er programmatisch aan
vastzit.

**Bron:** `wies/core/jinja2/parts/filter_sidebar.html`,
`wies/core/jinja2/parts/placement_cards.html`,
`wies/core/jinja2/parts/assignment_card_rows.html`.

In Chromium, Edge en Firefox gelijk.

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

##### Succescriterium 1.3.2 (Niveau A) — Betekenisvolle volgorde

Als de volgorde waarin content wordt gepresenteerd van invloed is op zijn
betekenis, kan een betekenisvolle leesvolgorde door software bepaald worden.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Leesvolgorde uit de toegankelijkheidsboom: banner,
hoofdnavigatie, gebruikersmenu, hoofdinhoud met de zijbalk vóór de inhoud,
footer als laatste. In het zijpaneel: titelbalk, naam, gegevens. Dat komt
overeen met de visuele opbouw; de zijbalk vóór de paginatitel is de kwestie van
1.3.1. Bevestigd met VoiceOver.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Content dient in een betekenisvolle volgorde in de broncode te staan. De
voorleessoftware van blinde bezoekers leest namelijk de broncodevolgorde voor, niet
de visuele volgorde. Wordt iets met CSS visueel verplaatst, dan kan de voorgelezen
volgorde afwijken van wat op het scherm staat.

</div>

##### Succescriterium 1.3.3 (Niveau A) — Zintuiglijke eigenschappen

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

##### Succescriterium 1.3.4 (Niveau AA) — Oriëntatie

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

##### Succescriterium 1.3.5 (Niveau AA) — Inputdoel identificeren

Het doel van een invoerveld dat gegevens over de gebruiker verzamelt, kan door
software bepaald worden.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

De velden die over de gebruiker zelf gaan, dragen hun inputdoel.

</div>

De velden Voornaam en Achternaam achter "Naam wijzigen" op Mijn profiel gaan
over de gebruiker zelf en dragen `autocomplete="given-name"` respectievelijk
`autocomplete="family-name"`, de waarden uit de WCAG-lijst van inputdoelen.

Alle andere formulieren in Wies verzamelen gegevens over collega's, niet over de
ingelogde gebruiker, en vallen buiten het criterium; daar geldt de uitzondering.

**Bron:** `wies/core/forms.py`, `ProfileNameForm`.

<div class="explain">

**Uitleg van dit succescriterium**

Velden die om gegevens van de gebruiker zelf vragen (naam, e-mailadres,
telefoonnummer) horen een `autocomplete`-attribuut te hebben. Browsers en
hulpsoftware kunnen die velden dan automatisch invullen of van een herkenbaar icoon
voorzien. Dat scheelt typewerk voor mensen met een motorische beperking en helpt
mensen met een cognitieve beperking.

</div>

#### Richtlijn 1.4 Onderscheidbaar

_Maak het voor gebruikers gemakkelijker om content te horen en te zien._

##### Succescriterium 1.4.1 (Niveau A) — Gebruik van kleur

Kleur wordt niet als het enige visuele middel gebruikt om informatie over te
brengen.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Handmatig beoordeeld op Wie zit waar?, Aanvragen en Beheer
gebruikers: elke betekenis die met kleur wordt gegeven, staat ook in tekst of
vorm. Statuschips dragen een tekstlabel ("Beperkt zichtbaar", "Afgelopen"), de
actieve filterrij een vinkje, de gekozen weergave een ingedrukte knop.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Als informatie alleen door kleurverschil wordt overgebracht, kan die informatie
niet worden waargenomen door slechtziende of kleurenblinde bezoekers. Zorg dat een
link niet alleen aan kleur herkenbaar is maar ook aan onderstreping, en dat
foutmeldingen niet alleen "rood" zijn maar ook tekstueel worden benoemd.

</div>

##### Succescriterium 1.4.2 (Niveau A) — Geluidsbediening

Als een geluidsweergave op een webpagina automatisch meer dan 3 seconden speelt, is er of een mechanisme beschikbaar om de geluidsweergave te pauzeren of te stoppen, of er is een mechanisme beschikbaar om het geluidsvolume onafhankelijk van het overall systeemvolume te regelen.

<div class="verdict na">

**Dit succescriterium is niet van toepassing.**

Er is geen automatisch spelende audio aanwezig.

</div>

##### Succescriterium 1.4.3 (Niveau AA) — Contrast (minimum)

De visuele weergave van tekst en afbeeldingen van tekst heeft een
contrastverhouding van ten minste 4,5:1.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

| Meting                                           | Aantal  |
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

##### Succescriterium 1.4.4 (Niveau AA) — Herschalen van tekst

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

##### Succescriterium 1.4.5 (Niveau AA) — Afbeeldingen van tekst

Als de gebruikte technologieën de visuele weergave tot stand kunnen brengen, wordt tekst gebruikt in plaats van afbeeldingen van tekst om informatie over te brengen, behalve wanneer de afbeelding van tekst visueel aanpasbaar is of een specifieke weergave essentieel is.

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

##### Succescriterium 1.4.10 (Niveau AA) — Dynamisch aanpassen (reflow)

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

##### Succescriterium 1.4.11 (Niveau AA) — Niet-tekstueel contrast

De visuele weergave van componenten en grafische objecten heeft een
contrastverhouding van ten minste 3:1.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

In het lichte thema handmatig beoordeeld; in het donkere thema gemeten als
pixelcontrast op schermafbeeldingen van `/opdrachten/` (`data-scheme="dark"`), omdat de kleuren in shadow roots zitten:

| Element                | Licht | Donker |
| ---------------------- | ----- | ------ |
| Rand zoekveld          | 5,3:1 | 5,3:1  |
| Rand datumveld         | 4,9:1 | 5,8:1  |
| Rand checkbox          | 4,9:1 | 5,8:1  |
| Focusring op zoekveld  | 6,2:1 | 5,3:1  |
| Focusring op filterrij | 6,2:1 | 4,6:1  |

Alles boven de eis van 3:1. Chips en tags hebben een vulling van 1,1 tot 1,3:1
tegen de pagina, maar dragen hun betekenis in tekst en vallen daarom buiten het
criterium.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Niet alleen tekst moet voldoende contrast hebben. Ook de rand van een invoerveld,
het vinkje in een selectievakje, een icoon dat betekenis draagt en de focusring
moeten zich met ten minste 3:1 aftekenen tegen hun omgeving. Anders is voor
slechtziende gebruikers niet te zien waar een veld begint of eindigt.

</div>

##### Succescriterium 1.4.12 (Niveau AA) — Tekstafstand

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

##### Succescriterium 1.4.13 (Niveau AA) — Content bij aanwijzen of focussen

Wanneer aanvullende content zichtbaar wordt en daarna weer verborgen door hover
met de aanwijzer of focus met het toetsenbord, dan kan die content worden
gesloten, aangewezen en blijft ze zichtbaar tot de gebruiker haar sluit.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Handmatig beoordeeld: de tooltips op iconen en op de
privacy-chips sluiten met Escape zonder dat de focus verspringt, blijven staan
zolang de muis erop rust en bedekken niets dat nodig is.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Verschijnt er extra inhoud bij het aanwijzen of focussen (een tooltip, een
uitklapmenu), dan gelden drie eisen: de inhoud moet met Escape te sluiten zijn, de
muis moet er naartoe kunnen bewegen zonder dat hij verdwijnt, en hij moet zichtbaar
blijven tot de gebruiker wegbeweegt of hem sluit.

</div>

---

### Principe 2 Bedienbaar

_Componenten van de gebruikersinterface en navigatie moeten bedienbaar zijn._

#### Richtlijn 2.1 Toetsenbordtoegankelijk

##### Succescriterium 2.1.1 (Niveau A) — Toetsenbord

Alle functionaliteit van de content is bedienbaar via een toetsenbordinterface.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Alle interactieve elementen zijn met Tab bereikbaar. Getoetst via de
accessibility tree van de browser: op `/` 61 interactieve elementen, op
`/beheer/gebruikers/` 70, alle met een toegankelijke naam en rol.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Alle functionaliteit dient bediend te kunnen worden met het toetsenbord. Dit is te
toetsen door de hele applicatie alleen met Tab, Enter, spatie en de pijltoetsen te
bedienen, zonder muis.

</div>

##### Succescriterium 2.1.2 (Niveau A) — Geen toetsenbordval

Als de toetsenbordfocus met de toetsenbordinterface verplaatst kan worden naar een component van de pagina, dan kan de focus ook met alleen de toetsenbordinterface weer van dat component weg worden bewogen. En, als er meer nodig is dan de standaard pijl- of tabtoetsen, dan wordt de gebruiker geïnformeerd over de manier waarop de focus kan worden verplaatst.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Getoetst op de sheet "Merk toevoegen": deze opent als een echte `<dialog open>`,
de focus springt bij openen naar het eerste invoerveld, en van 12 opeenvolgende
tabstops bleven er 9 binnen de sheet: de focus loopt rond en verlaat het venster
niet.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Een bezoeker mag nooit met het toetsenbord "vast" komen te zitten. Bij een venster
of dialoog hoort de focus juist wél ingesloten te zijn zolang het open staat, maar
er moet altijd een weg naar buiten zijn, meestal met Escape of een sluitknop.

</div>

##### Succescriterium 2.1.4 (Niveau A) — Sneltoetsen tekentoets

Wanneer een sneltoets in content wordt geïmplementeerd door alleen letters, leestekens, cijfers of symbolen te gebruiken, dan kan die sneltoets worden uitgezet of opnieuw toegewezen, of is hij alleen actief wanneer de betreffende component de focus heeft.

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

#### Richtlijn 2.2 Genoeg tijd

##### Succescriterium 2.2.1 (Niveau A) — Timing aanpasbaar

Voor elke tijdslimiet die door de content wordt ingesteld, kan de gebruiker die uitzetten, aanpassen of verlengen, tenzij de limiet onderdeel is van een realtime gebeurtenis, essentieel is, of langer duurt dan 20 uur.

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

##### Succescriterium 2.2.2 (Niveau A) — Pauzeren, stoppen, verbergen

Voor alle bewegende, knipperende, scrollende of automatisch actualiserende informatie die automatisch start, langer dan vijf seconden duurt en parallel met andere content wordt getoond, is er een mechanisme om dit te pauzeren, te stoppen of te verbergen.

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

#### Richtlijn 2.3 Toevallen

##### Succescriterium 2.3.1 (Niveau A) — Drie flitsen of beneden drempelwaarde

Webpagina's bevatten niets wat meer dan drie keer flitst in enige periode van één seconde, of de flits is beneden de algemene flits- en rodeflitsdrempelwaarden.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er is geen flitsende content aanwezig.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Sterk flitsende content kan epileptische aanvallen veroorzaken. Vermijd content die
meer dan drie keer per seconde flitst.

</div>

#### Richtlijn 2.4 Navigeerbaar

##### Succescriterium 2.4.1 (Niveau A) — Blokken omzeilen

Er is een mechanisme beschikbaar om blokken content die op meerdere webpagina's
worden herhaald te omzeilen.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er is een skiplink "Ga naar hoofdinhoud" (`base.html`, regel 60). Geverifieerd: het
is de **eerste tabstop** op de pagina, hij wordt zichtbaar bij focus, en activeren
verplaatst de focus naar de hoofdinhoud.

</div>

> **Correctie op een bestaande melding.** Issue #600 in de projectadministratie
> meldt dat er géén skiplink zou zijn en dat de focus na het bijwerken van de
> pagina verloren gaat. Beide zijn **niet meer actueel**; zie ook 2.4.3.
> Aanbevolen het issue te sluiten.

<div class="explain">

**Uitleg van dit succescriterium**

Zorg dat toetsenbordgebruikers en blinde bezoekers herhalende blokken (menu's,
zoekveld, logo) kunnen overslaan om direct bij de hoofdinhoud te komen. De beste
manier is een skiplink bovenaan de pagina, die zichtbaar wordt zodra hij focus
krijgt.

</div>

##### Succescriterium 2.4.2 (Niveau A) — Paginatitel

Webpagina's hebben titels die het onderwerp of doel beschrijven.

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

##### Succescriterium 2.4.3 (Niveau A) — Focus volgorde

Focusbare componenten krijgen de focus in een volgorde waardoor betekenis en
bedienbaarheid behouden blijven.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Wies vervangt delen van de pagina zonder deze opnieuw te laden. Na zo'n swap
verplaatst `focus_restore.js` de focus naar het element waar de gebruiker was,
of naar een logisch startpunt binnen het vervangen fragment. `scripts/focus_swap.py`
geeft 9 van 9. Daarnaast zijn de volgende flows met het toetsenbord doorlopen in
Chromium, Edge en Firefox (`scripts/hertest_swap.py`); in alle drie landt de
focus op dezelfde plek.

</div>

| Flow                                       | Focus na de swap                                           |
| ------------------------------------------ | ---------------------------------------------------------- |
| Kaart openen (Enter) op Wie zit waar?      | Het zijpaneel (`dialog`)                                   |
| Zijpaneel sluiten (Escape)                 | Terug op de kaart die het opende                           |
| Updates-tab in het paneel                  | Blijft op de tab                                           |
| Inline bewerken openen                     | Het eerste invoerveld                                      |
| Filtergroep "Meer..." openen               | Het zoekveld in de modal; Escape brengt terug naar de knop |
| Weergave wisselen (Collega's / Opdrachten) | Blijft op de gekozen optie                                 |
| "Opdracht invoeren" op Aanvragen           | Het zijpaneel (`dialog`)                                   |

**Observatie, geen afwijking.** Firefox geeft elke pagina één tabstop extra aan het
begin: `nldd-page` is een scrollbare container en Firefox maakt die standaard met Tab
bereikbaar. Chromium en Edge doen dat niet. Het is een keuze van de browser en zit in
het design system, niet in Wies; het is te voorkomen met `tabindex="-1"` op
`nldd-page` in `@nldd/design-system`.

<div class="explain">

**Uitleg van dit succescriterium**

De tabvolgorde moet logisch zijn en aansluiten bij wat er op het scherm gebeurt.
Wordt een venster geopend, dan hoort de focus daarheen te gaan. Wordt een deel van
de pagina vervangen, dan hoort de focus mee te verhuizen en niet terug te vallen
naar het begin van de pagina.

</div>

##### Succescriterium 2.4.4 (Niveau A) — Linkdoel (in context)

Het linkdoel kan bepaald worden uit enkel de linktekst of uit de linktekst samen met zijn door software bepaalde linkcontext, behalve daar waar het doel van de link een dubbelzinnige betekenis zou kunnen hebben voor gebruikers in het algemeen.

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

##### Succescriterium 2.4.5 (Niveau AA) — Meerdere manieren

Er is meer dan één manier beschikbaar om een webpagina binnen een verzameling webpagina's te vinden, behalve wanneer de webpagina het resultaat is van, of een stap in, een proces.

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

##### Succescriterium 2.4.6 (Niveau AA) — Koppen en labels

Koppen en labels beschrijven het onderwerp of doel.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Toegankelijkheidsboom van alle elf pagina's: elke pagina één
h1 met de paginatitel, groepen als h2, kaarten en opdrachten als h3, en elk
zoek- en invoerveld met een label dat zegt wat er wordt verwacht. VoiceOver bij
de tabs van het zijpaneel: "Gegevens, selected tab, 1 of 2, Opdrachtdetails tab
group". Het niveau van de zijbalkkoppen is de kwestie van 1.3.1.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Koppen en labels moeten het onderwerp of doel beschrijven. Een kop als "Meer
informatie" kan beter "Meer informatie over voorleessoftware" heten. Blinde
bezoekers vragen vaak een overzicht van alle koppen op om snel een beeld van de
inhoud te krijgen.

</div>

##### Succescriterium 2.4.7 (Niveau AA) — Focus zichtbaar

Elke gebruikersinterface die met een toetsenbord te bedienen is, heeft een
bedieningswijze waarbij de indicator van de toetsenbordfocus zichtbaar is.

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

##### Succescriterium 2.4.11 (Niveau AA) — Focus niet bedekt (minimaal)

Wanneer een component toetsenbordfocus krijgt, wordt deze niet volledig verborgen
door content die door de auteur is toegevoegd.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Getoetst door 20 opeenvolgende tabstops te doorlopen op een venster van 1200 × 500
pixels, een hoogte waarbij vaste elementen het snelst in de weg zitten. Het
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

#### Richtlijn 2.5 Inputmodaliteiten

##### Succescriterium 2.5.1 (Niveau A) — Bewegingen aanwijzer

Alle functionaliteit waarmee bij de bediening gebruik wordt gemaakt van meerpunts- of padgebaseerde gebaren, kan worden bediend met een enkele aanwijzer zonder een padgebaseerd gebaar, tenzij een meerpunts- of padgebaseerd gebaar essentieel is.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Er zijn geen multipoint- of padgebaseerde bewegingen aangetroffen.

</div>

##### Succescriterium 2.5.2 (Niveau A) — Annulering aanwijzer

Voor functionaliteit die kan worden bediend met een enkele aanwijzer geldt dat het down-event niet wordt gebruikt om de functie uit te voeren, of dat de functie kan worden afgebroken of ongedaan gemaakt.

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

##### Succescriterium 2.5.3 (Niveau A) — Label in naam

Bij componenten van de gebruikersinterface met labels die tekst of afbeeldingen van tekst bevatten, bevat de naam de tekst die visueel wordt weergegeven.

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

##### Succescriterium 2.5.4 (Niveau A) — Bewegingsactivering

Functionaliteit die kan worden bediend door de beweging van een apparaat of beweging van een gebruiker, kan ook worden bediend met componenten van de gebruikersinterface. De reactie op de beweging kan worden uitgeschakeld om onbedoelde activering te voorkomen.

<div class="verdict na">

**Dit succescriterium is niet van toepassing.**

Er is geen functionaliteit die door beweging van het apparaat wordt geactiveerd.

</div>

##### Succescriterium 2.5.7 (Niveau AA) — Sleepbewegingen

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

##### Succescriterium 2.5.8 (Niveau AA) — Doelgrootte (minimum)

De grootte van het aanwijsgebied is ten minste 24 bij 24 CSS-pixels, behalve wanneer het doel inline in een zin staat, de grootte wordt bepaald door de user agent, of een equivalent alternatief beschikbaar is.

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

### Principe 3 Begrijpelijk

_Informatie en de bediening van de gebruikersinterface moeten begrijpelijk zijn._

#### Richtlijn 3.1 Leesbaar

##### Succescriterium 3.1.1 (Niveau A) — Taal van de pagina

De standaard menselijke taal van elke webpagina kan door software bepaald worden.

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

##### Succescriterium 3.1.2 (Niveau AA) — Taal van onderdelen

De menselijke taal van elke passage of zin in de content kan door software bepaald worden, behalve waar het gaat om eigennamen, technische termen, woorden uit een onbepaalde taal en woorden of zinsdelen die deel zijn gaan uitmaken van het jargon van de onmiddellijk omringende tekst.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Handmatig beoordeeld met VoiceOver in de Nederlandse stem: de
Engelse rolnamen ("UX designer", "Scrum Master", "Business Manager") worden
herkenbaar uitgesproken en zijn binnen de organisatie gangbaar jargon, zodat de
uitzondering voor ingeburgerde termen geldt. Er is geen term aangetroffen die
zó verminkt wordt dat hij onherkenbaar is.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Wordt ergens een andere taal gebruikt dan de hoofdtaal van de pagina, dan hoort dat
in de code te worden aangegeven met `lang`. Voor losse woorden en voor jargon dat is
ingeburgerd, hoeft dat niet.

</div>

#### Richtlijn 3.2 Voorspelbaar

##### Succescriterium 3.2.1 (Niveau A) — Bij focus

Als een component van de gebruikersinterface de focus krijgt, dan veroorzaakt dat geen contextwijziging.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Het focussen van een element veroorzaakt geen contextwijziging.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Er mag niets ingrijpends gebeuren zodra een element focus krijgt, dus vóór er
geklikt wordt. Een select die bij focus meteen naar een andere pagina springt, is
een klassiek voorbeeld van wat niet mag.

</div>

##### Succescriterium 3.2.2 (Niveau A) — Bij input

Het veranderen van de instelling van een component leidt niet automatisch tot een
contextwijziging, tenzij de gebruiker daarover vooraf is geïnformeerd.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

De focus blijft staan waar de gebruiker hem liet.

</div>

Een filter aanvinken ververst de lijst en de zijbalk in delen (htmx). Gemeten met
VoiceOver blijft de focus daarbij op de rij die de gebruiker aanvinkte:
"Directoraat-generaal Belastingdienst 16 unchecked checkbox, group list
Opdrachtgever 4 items", en na het aanvinken dezelfde rij, nu aangevinkt.

Hetzelfde is gemeten voor de overige plekken waar de pagina in delen ververst:
een kaart openen brengt de focus naar het zijpaneel dat verschijnt
(`nldd-sheet` → `dialog`), en Escape brengt hem terug naar de kaart waar hij
vandaan kwam. In geen van de gemeten gevallen valt de focus terug naar het begin
van de pagina.

Er treedt bij geen van deze handelingen een contextwijziging op die de gebruiker
niet zelf in gang zette.

**Bron:** `wies/core/static/js/focus_restore.js`,
`wies/core/jinja2/parts/filter_sidebar.html`.

<div class="explain">

**Uitleg van dit succescriterium**

Het invullen of wijzigen van een formulierveld mag niet automatisch een grote
verandering veroorzaken, zoals het laden van een nieuwe pagina, tenzij de
gebruiker daar vooraf over is geïnformeerd.

</div>

##### Succescriterium 3.2.3 (Niveau AA) — Consistente navigatie

Navigatiemechanismen, die op meerdere webpagina's binnen een verzameling webpagina's herhaald worden, komen elke keer dat ze worden herhaald in dezelfde relatieve volgorde voor, tenzij een verandering wordt geïnitieerd door de gebruiker.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

De hoofdnavigatie, het gebruikersmenu en de paginavoet staan op alle onderzochte
pagina's in dezelfde relatieve volgorde.

</div>

##### Succescriterium 3.2.4 (Niveau AA) — Consistente identificatie

Componenten die dezelfde functionaliteit hebben binnen een verzameling webpagina's worden consistent geïdentificeerd.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Componenten met dezelfde functie worden consistent aangeduid.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Een onderdeel van de interface hoort altijd met dezelfde naam te worden aangeduid.
Noem een knop niet op de ene pagina "Opslaan" en op de andere "Bewaren".

</div>

##### Succescriterium 3.2.6 (Niveau A) — Consistente hulp

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

Nieuw in WCAG 2.2. Biedt een website hulp (contactgegevens, een
veelgestelde-vragenpagina, een chatfunctie), dan moet die hulp op elke pagina op
dezelfde plek staan. Mensen met een cognitieve beperking hoeven dan niet op elke
pagina opnieuw te zoeken waar ze terechtkunnen.

</div>

#### Richtlijn 3.3 Assistentie bij invoer

##### Succescriterium 3.3.1 (Niveau A) — Fout identificatie

Als een invoerfout automatisch wordt ontdekt, wordt het onderdeel waar de fout
zit geïdentificeerd en wordt de fout in tekst aan de gebruiker meegedeeld.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Een afgewezen veld wordt benoemd, en de reden komt mee.

</div>

Elk formulier in de steekproef is leeg en met ongeldige waarden ingediend. Een
afgewezen veld draagt `invalid` en verwijst met `unmet` naar de bijbehorende
foutregel, die dat id draagt:

```html
<nldd-text-field name="name" required invalid unmet="error-name-1">
  <nldd-validation-item id="error-name-1"
    >Dit veld is verplicht.</nldd-validation-item
  ></nldd-text-field
>
```

Het veld geeft die foutlijst zelf door als beschrijving aan de invoer in zijn
shadow root, zodat de koppeling de shadow-grens overleeft. Gemeten met
VoiceOver: "Opdrachtnaam, Opdrachtnaam is verplicht, required, invalid data,
edit text". De focus gaat na afwijzing naar het eerste ongeldige onderdeel, ook
als dat een knop is, zoals bij de opdrachtgever-kiezer: "Opdrachtgever
toevoegen, Fout: Voeg minimaal 1 opdrachtgever toe., button".

Daarnaast vat één live region de fouten samen, zodat de gebruiker meteen hoort
dat het opslaan niet lukte en waarom: "Het formulier heeft 2 fouten:
Opdrachtnaam is verplicht. Voeg minimaal 1 opdrachtgever toe."

**Bron:** `wies/core/jinja2/forms/field.html`,
`wies/core/static/js/field_error_description.js`,
`wies/core/static/js/live_region.js`.

<div class="explain">

**Uitleg van dit succescriterium**

Zorg voor foutmeldingen die het veld benoemen waar de fout zit. Vermijd "dit veld is
verkeerd ingevuld"; noem de naam van het veld, zodat een blinde bezoeker weet waar
hij moet zijn.

</div>

##### Succescriterium 3.3.2 (Niveau A) — Labels of instructies

Als de content gebruikersinvoer vereist, dan worden labels of instructies geleverd.

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

##### Succescriterium 3.3.3 (Niveau AA) — Foutsuggestie

Als een invoerfout automatisch wordt ontdekt en suggesties voor verbetering
bekend zijn, dan worden die aan de gebruiker gegeven.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

De suggestie bij een fout benoemt wat er moet gebeuren.

</div>

De foutmeldingen benoemen wat er moet gebeuren in plaats van alleen dát er iets
mis is: "Voeg minimaal 1 opdrachtgever toe", "Opdrachtnaam is verplicht", en bij
een periode dat de einddatum na de startdatum moet liggen.

Ze bereiken een schermlezergebruiker langs dezelfde weg als bij 3.3.1: het veld
geeft zijn foutlijst door als beschrijving, en de live region vat ze samen. De
metingen staan daar.

<div class="explain">

**Uitleg van dit succescriterium**

Bied waar mogelijk een suggestie ter verbetering, bijvoorbeeld "controleer of het
e-mailadres het formaat naam@domein.nl heeft". Dat helpt vooral mensen met een
cognitieve beperking.

</div>

##### Succescriterium 3.3.4 (Niveau AA) — Foutpreventie

Voor webpagina's die wettelijke verplichtingen of financiële transacties voor de gebruiker uitvoeren, die door de gebruiker te beheren gegevens verwijderen of wijzigen, of die antwoorden van de gebruiker verzenden, geldt dat verzendingen omkeerbaar zijn, gecontroleerd worden op invoerfouten, of bevestigd kunnen worden.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Handmatig en geïnstrumenteerd beoordeeld: elke verwijdering
vraagt bevestiging in een dialoog. VoiceOver: "Gebruiker verwijderen? dialog
with 4 items"; Tab: "Behoud gebruiker, button"; Tab: "Verwijder gebruiker,
button"; Escape sluit de dialoog. Dezelfde dialoog staat op het verwijderen van
een opdracht, een label, een categorie en een merk. De annuleerknop heet
"Behoud gebruiker" in plaats van "Annuleren"; dat is een keuze in de tekst, geen
afwijking.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Bij handelingen met juridische of financiële gevolgen, of bij het wijzigen of
verwijderen van gegevens, moet de gebruiker de actie kunnen terugdraaien,
controleren of bevestigen.

</div>

##### Succescriterium 3.3.7 (Niveau A) — Overbodige invoer

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

##### Succescriterium 3.3.8 (Niveau AA) — Toegankelijke authenticatie (minimaal)

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

### Principe 4 Robuust

_Content moet voldoende robuust zijn om betrouwbaar geïnterpreteerd te worden door een breed scala van gebruikersagenten, waaronder hulptechnologieën._

#### Richtlijn 4.1 Compatibel

> **Succescriterium 4.1.1 (Parsen) is vervallen.** Dit criterium is in WCAG 2.2
> geschrapt, omdat moderne browsers zelf omgaan met kleine fouten in de opmaak.
> Ter informatie: er is wel op gecontroleerd, en op alle elf pagina's zijn
> **0 dubbele ID's** aangetroffen.

##### Succescriterium 4.1.2 (Niveau A) — Naam, rol, waarde

Voor alle componenten van de gebruikersinterface kunnen de naam en rol door software bepaald worden; toestanden, eigenschappen en waarden die door de gebruiker ingesteld kunnen worden, kunnen door software ingesteld worden; en kennisgeving van veranderingen in deze items is beschikbaar voor user agents, met inbegrip van hulptechnologieën.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Gemeten met VoiceOver, letterlijk: checkbox in de zijbalk
"Directoraat-generaal Belastingdienst 6, unchecked checkbox" en na activeren
"checked"; weergavekeuze "Persoon (30), selected radio button, Weergave radio
group" en na pijl rechts "Opdracht (21), selected radio button"; tabs in het
zijpaneel "Gegevens, selected tab, 1 of 2" en "Updates, selected tab, 2 of 2";
sorteerknop "Startdatum (nieuwste eerst), menu pop up collapsed, button", na
Enter "Startdatum (nieuwste eerst), checked menu item" en na pijl omlaag "Naam
(A-Z), menu item"; zijpaneel "Detail dialog with 2 items"; verwijderen
"Gebruiker verwijderen? dialog with 4 items". Naam, rol en toestand kloppen.

Waar de focus na een deelverversing heen gaat, valt onder 3.2.2 en niet onder
dit criterium, dat over naam, rol en waarde gaat. Kanttekening: de weergavekeuze meldt bij elke knop "1 of 1" in plaats van "1 of
2"; dat zit in `nldd-segmented-control` en is bij de componentbibliotheek te
melden.

</div>

<div class="explain">

**Uitleg van dit succescriterium**

Voor alle bedieningselementen moet hulpsoftware kunnen bepalen: wat is het (rol),
hoe heet het (naam) en in welke stand staat het (waarde). Bij zelfgebouwde
componenten (een eigen keuzelijst, een eigen schakelaar) gaat dit vaak mis, omdat
de browser die betekenis niet vanzelf kent.

</div>

##### Succescriterium 4.1.3 (Niveau AA) — Statusberichten

Statusberichten kunnen door software bepaald worden, zodat ze aan de gebruiker
kunnen worden voorgelezen zonder dat die de focus verliest.

<div class="verdict pass">

**De onderzochte set webpagina's voldoet aan dit succescriterium.**

Wat er verandert zonder paginalading, wordt uitgesproken.

</div>

De pagina draagt één live region (`role="status"`), die leeg in het document
staat en na elke deelverversing wordt gevuld. Dat een region al bestaat vóór de
tekst erin verschijnt, is wat een schermlezer nodig heeft: een region die
tegelijk met zijn inhoud verschijnt, blijft stil.

Drie soorten statusberichten zijn met VoiceOver getoetst:

- **Aantal resultaten na een filterwissel.** Gemeten: "16 collega's", direct na
  het aanvinken van een filter. Op de opdrachtenlijst evenzo het aantal
  opdrachten; is er niets gevonden, dan klinkt "Geen opdrachten gevonden".
- **Bevestiging na opslaan of verwijderen.** De notificatie wordt uitgesproken,
  bijvoorbeeld `Merk "Toetsmerk" is toegevoegd.` Opslaan, aanpassen en
  verwijderen van een gebruiker, label, categorie, merk, teamlid of opdracht
  geven elk zo'n bevestiging.
- **Foutmelding van een afgewezen formulier.** Zie 3.3.1.

**Afbakening.** Het criterium gaat over veranderingen terwijl de gebruiker op de
pagina blijft. Een bevestiging die verschijnt nadat een opslag de hele pagina
opnieuw laadt, is strikt genomen nieuwe pagina-inhoud en valt erbuiten. Die
gevallen zijn toch meegenomen: ook dan wil een gebruiker weten of het opslaan
gelukt is.

**Bron:** `wies/core/static/js/live_region.js`, `wies/core/jinja2/base.html`.

<div class="explain">

**Uitleg van dit succescriterium**

Verandert er iets op de pagina zonder dat de gebruiker daarheen navigeert ("12
resultaten gevonden", "opgeslagen", "er ging iets mis"), dan moet dat aan een
schermlezer worden aangekondigd via een live region. Anders merkt een blinde
gebruiker de verandering niet op.

</div>

---

---

## Bijlagen

### Geadviseerde vervolgstappen

| Stap                                                    | Waarom                                                                                       | Prioriteit |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------- |
| 1. Toegankelijkheidsverklaring 29132 bijwerken          | Alle 55 criteria zijn beoordeeld; dit rapport kan als onderbouwing worden ingediend          | Hoog       |
| 2. Toetsing met NVDA in Firefox en Chrome op Windows    | Het basisniveau belooft alle gangbare hulpapparatuur                                         | Middel     |
| 3. Toetsing met gebruikers van hulpapparatuur           | Het oordeel van wie de applicatie dagelijks zo gebruikt, is met geen instrument te vervangen | Middel     |
| 4. Twee punten melden bij de componentbibliotheek       | `aria-describedby` over de shadow-grens (3.3.1) en "1 of 1" in de weergavekeuze (4.1.2)      | Middel     |
| 5. axe-core en een koppenvolgordetoets in de bouwstraat | Voorkomt regressie in het gewone document                                                    | Middel     |
| 6. 404-pagina en processen alsnog toetsen               | Ontbraken in de steekproef                                                                   | Middel     |

---

<div class="footer-note">

**Herleidbaarheid.** Alle cijfers in dit rapport komen uit meetscripts die zijn
uitgevoerd tegen een draaiende instantie van `main` (stand 30 september 2026,
@ `c342ff2`), en uit de schermlezertoets, waarin de aangehaalde uitspraken van
VoiceOver letterlijk bewaard zijn. De scripts zijn beschikbaar bij het
ontwikkelteam, zodat de metingen herhaald kunnen worden.

</div>

<style>
body {
  /* border-box: anders telt de zijpadding bij de breedte op en scrolt de pagina
     op een smal scherm 32 px opzij (SC 1.4.10). */
  box-sizing: border-box;
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
