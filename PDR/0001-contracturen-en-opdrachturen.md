# 0001 - Contracturen en opdrachturen per consultant

**Status:** Idee
**Datum:** 2026-06-25

## Context

De business managers (BM-ers) van het RIG houden bezetting en beschikbaarheid van consultants nu bij in een Excel-bestand op een netwerkschijf — intern de "P-plaat" genoemd. Naast plaatsingsinformatie (opdracht naam, opdracht periode, consultant) staan daar contracturen per week per consultant en uren per opdracht in. Zolang die gegevens niet in Wies staan, moet het RIG twee boekhoudingen bijhouden en lopen we het risico dat de informatie in Wies out-of-date raakt.

Andere merken die na het RIG op Wies aansluiten, gebruiken voor capaciteits­planning OTYS — daar staan contracturen en opdracht­uren al in, en hoeven dus niet in Wies. Het RIG is daarmee de enige groep zonder een ander systeem voor deze gegevens. Er waren plannen dat ook het RIG naar OTYS zou overstappen, maar daar is al maanden geen voortgang op; tot die overstap gebeurt blijft de P-plaat in gebruik. Mocht het RIG alsnog naar OTYS overstappen, dan komt deze functionaliteit in Wies te vervallen.

Door deze gegevens in Wies te vangen, kan de P-plaat in de tussentijd worden uitgefaseerd. Omdat het om een uitbreiding van persoonsgegevens gaat, wordt deze PDR vooraf gedeeld met de CISO/Privacy Officer. Op de huidige dataset is een DPIA-prescan uitgevoerd met als uitkomst dat een DPIA niet nodig is. Deze PDR beschrijft de uitbreiding én motiveert waarom een nieuwe DPIA naar verwachting niet nodig is.

## Besluit

We breiden het datamodel uit met twee onderdelen:

**1. Nieuwe tabel `ContractPeriod`** — legt vast hoeveel uur per week een collega contractueel werkt, met historie. Een collega kan een opeenvolging van periodes hebben, zodat een wijziging (bv. van 32 naar 36 uur) traceerbaar blijft.

```
ContractPeriod
  colleague        -> Colleague
  hours_per_week   int (1–40)
  start_date       date
  end_date         date (leeg = lopend)
```

- Bewerken (periode toevoegen, lopende afsluiten, bestaande corrigeren): **Beheerder**
- Bekijken: Beheerder, BM-er, de collega zelf

**2. Nieuw veld `Placement.assignment_hours_per_week`** — het aantal uren per week dat een collega op een specifieke plaatsing werkt.

- Bewerken: **BM-er** (eigenaar van de bijbehorende opdracht)
- Bekijken: Beheerder, BM-er, de geplaatste collega
- Er wordt geen historie bewaard binnen één plaatsing. Wijzigen de afspraken (bv. van 20 naar 24 uur), dan sluit de BM de bestaande plaatsing af en maakt een nieuwe aan. De tijdslijn loopt zo via de plaatsings­keten zelf.

**3. Afgeleide inzichten** worden bovenop deze gegevens gebouwd: resterende uren per collega (contracturen − som van plaatsings­uren) en een bezettings­overzicht voor BM-ers. Deze inzichten introduceren géén nieuwe gegevens en geven niemand toegang tot uren-informatie die niet al via de bovenstaande regels zichtbaar is — de privacy-impact zit volledig in de twee gegevens­bronnen hierboven. De concrete vorm van de overzichten wordt iteratief met de RIG-BM-ers bepaald.

**Uitrol:** beschikbaar voor alle collega's en plaatsingen; velden blijven leeg tot ze ingevuld worden. Teams die de gegevens niet bijhouden, kunnen ze negeren. De eerste gebruikers zijn de BM-ers van het RIG.

## Motivatie

- **Past binnen bestaand verwerkingsdoel.** De privacyverklaring noemt al "inzicht bieden in beschikbaarheid en bezetting van collega's" als verwerkingsdoel. Uren-gegevens maken dat bestaande doel concreet meetbaar; er komt geen nieuw doel bij.
- **Geen bijzondere persoonsgegevens, zelfde grondslag.** Urenaantallen vallen niet in een gevoelige categorie (geen gezondheid, etniciteit, biometrie). De grondslag art. 6(1)(f) AVG (gerechtvaardigd belang — effectief inzetbeheer van consultants) die de huidige set dekt, dekt ook deze uitbreiding.
- **Vervangt schaduw­administratie.** Dezelfde gegevens worden nu al bijgehouden in een gedeeld Excel op een netwerkschijf. Verplaatsing naar Wies verbetert toegangscontrole (rolgebaseerd per veld), audit-trail en data­minimalisatie ten opzichte van de huidige situatie.
- **Strikte toegangsbeperking per veld.** Contracturen (en hun historie) alleen door Beheerders te bewerken, vergelijkbaar met hoe e-mailadres en rol nu al beheerd worden. Opdrachturen alleen door de BM-eigenaar van de opdracht, vergelijkbaar met de inzetperiode. Collega's zien hun eigen gegevens; verder zijn de velden niet zichtbaar.
- **Dataminimalisatie ondanks historie.** De `ContractPeriod`-tabel bewaart alleen wat nodig is om bezetting in het verleden te kunnen reconstrueren (een tijdreeks van urenaantallen), geen reden voor de wijziging of overige contractdetails.

## Gevolgen

- **Product:** één nieuwe tabel (`ContractPeriod`), één veld op `Placement`, bijbehorende permissieregels en bewerk-UI; plus resterende-uren- en bezettings­weergaves die op deze gegevens gebaseerd zijn.
- **Gebruikers (RIG):** kunnen de P-plaat na deze release uitfaseren.
- **Privacy:** de privacyverklaring krijgt een aanvulling dat onder "bezetting" ook contract- en opdrachturen vallen, en dat van contracturen een tijdreeks wordt bewaard. De pre-scan DPIA wordt bijgewerkt in overleg met de Privacy Officer ODI. Geen nieuwe volledige DPIA voorzien.
- **Bewaartermijn:** `ContractPeriod`-records horen bij een collega en blijven bestaan zolang de collega in Wies geregistreerd is; bij verwijdering van een collega gaan ze mee. `assignment_hours_per_week` hoort bij een plaatsing en volgt de bewaartermijn van plaatsings­gegevens. Geen aparte regelingen.
- **Andere merken:** ongewijzigd; velden blijven leeg en zijn niet verplicht. Merken die al OTYS gebruiken houden hun uren-administratie daar; deze functionaliteit is niet bedoeld om OTYS in Wies te dupliceren.
- **Toekomstige uitfasering:** als het RIG op termijn op OTYS overgaat, verdwijnt de noodzaak voor deze velden. Het datamodel is zo geïsoleerd opgezet (één tabel + één veld) dat verwijderen later weinig impact heeft.
