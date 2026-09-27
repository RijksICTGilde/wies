# Analyse: bedrijfsonderdelen per ministerie & plaatsing in het organogram

**Bron:** `organisaties.overheid.nl` XML-export (`exportOO.xml`, timestamp 2026-09-27)
**Organogrammen:** map `org_charts/` (12 ministeries, zie `metadata.md`)
**Gegenereerd:** 2026-09-27

Onderzocht zijn vier organisatietypen: **Agentschap**, **Zelfstandig bestuursorgaan (ZBO)**,
**Adviescollege** en **Inspectie**. Voor elk is bepaald (1) onder welk ministerie het valt via de
`relatieMetMinisterie` in de export, en (2) waar het orgaan op het gedownloade organogram van dat
ministerie staat — of dat het ontbreekt.

---

## Hoofdconclusies

1. **Alle 278 organen hebben een `relatieMetMinisterie`** in de export (247 actief na filteren op
   einddatum). De koppeling ministerie ↔ orgaan is dus 100% dekkend en betrouwbaar uit de XML te halen —
   je hebt de organogrammen niet nodig om te weten _bij welk_ ministerie iets hoort.

2. **De organogrammen zijn selectief.** Ze zijn geen 1-op-1 weergave van de export. Er zijn drie
   terugkerende keuzes:
   - **Agentschappen en inspecties worden vrijwel altijd getoond** (wisselende positie, zie patronen).
   - **ZBO's en adviescolleges worden vaak weggelaten of slechts gecureerd.** Meerdere charts zeggen dit
     letterlijk:
     - JenV: _"In dit overzicht zijn de zelfstandige bestuursorganen en de gefinancierde instellingen niet opgenomen."_
     - IenW: _"De raden, commissies, zbo's en instellingen zijn hier niet in opgenomen."_
   - **De export bevat veel privaatrechtelijke "ZBO's"** (zorgkantoren, keuringsinstanties,
     registratiecommissies, grondkamers, loodsencorporaties). Die zijn juridisch ZBO maar staan nooit op
     een organogram. Voorbeeld VWS: export 37 ZBO's, chart toont er 13 (de institutionele).

3. **Plaatsing is niet uniform** — er zijn vijf layout-patronen (hieronder). Voor een verbeterde
   org-chart in Wies is dit de kern: je kunt agentschappen/inspecties betrouwbaar positioneren, maar voor
   ZBO's/adviescolleges moet je een expliciete keuze maken (tonen als losse "gerelateerde organen"-laag,
   of verbergen zoals de rijksoverheid zelf doet).

---

## Plaatsingspatronen in de organogrammen

| Patroon                       | Waar de organen staan                                                                         | Ministeries                    |
| ----------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------ |
| **Peer-knopen**               | agentschappen/inspecties/planbureaus als top-level knopen náást de DG's                       | IenW                           |
| **Type-gegroepeerde panelen** | apart blok "Tot het ministerie behoren ook", box per type                                     | VWS                            |
| **Gemengd**                   | agentschappen genest onder DG's; inspectie als eigen blok; ZBO's/adviescolleges deels of niet | JenV, OCW, BZK, Financiën, SZW |
| **Kleurgecodeerd**            | knopen rond de SG, per type gekleurd via legenda                                              | EZK (incl. KGG)                |
| **Alleen intern / minimaal**  | enkel DG's/directies; externe organen ontbreken                                               | BZ, Defensie, AZ, LVVN(*)      |

(*) LVVN toont alleen de agentschappen/buitendiensten (NVWA, gedeelde EZK-onderdelen); geen ZBO's/adviescollege.

---

## Per ministerie

Aantallen = **actieve** organen uit de export. "Op chart" = staat het (als categorie) op het gedownloade organogram.

### Ministerie van Volksgezondheid, Welzijn en Sport — `vws.pdf`

**44 organen.** Pattern: type-gegroepeerde panelen (het duidelijkste voorbeeld).

- Agentschap (3): aCBG, CIBG, RIVM — **allemaal op chart**.
- Inspectie (1): IGJ — **op chart**.
- Adviescollege (3): Gezondheidsraad, NLsportraad, RVS — **allemaal op chart**.
- ZBO (37): chart toont **13** institutionele (CAK, CIZ, CBG, NZa, ZIN, ZonMw, CCMO, CSZ, Cdkb, Dopingautoriteit, Lcsh, PUR, BDz). De overige ~24 (zorgkantoren CZ/VGZ/Menzis/Zilveren Kruis…, keuringsinstanties, registratiecommissies) **niet op chart**.
- Chart toont ook een Planbureau (SCP) en Dienst (DUS-I) — buiten de vier onderzochte types.

### Ministerie van Justitie en Veiligheid — `jenv.pdf`

**42 organen.** Pattern: gemengd. Chart bevat ook Asiel & Migratie (aparte minister, DGM-kolom).

- Agentschap (7): DJI, IND, NFI, Justid, CJIB, NCSC, JUSTIS, DT&V, NOO/DISA — **genest onder de DG's** ("Baten-lastenagentschappen"-kolom + diensten onder DG's).
- Inspectie (2): Inspectie JenV **op chart** als blok; Rijksrecherche apart.
- ZBO (25) + Adviescollege (8): **niet op chart** (expliciet uitgesloten).

### Ministerie van Infrastructuur en Waterstaat — `ienw.pdf`

**40 organen.** Pattern: peer-knopen (wiel-layout).

- Agentschap (2): KNMI, Rijkswaterstaat — **als top-level knopen** naast de DG's.
- Inspectie (2): ILT **op chart** als knoop; ANVS **niet** (staat er niet bij).
- ZBO (35) + Adviescollege (1, Rli): **niet op chart** (expliciet uitgesloten). Bevat veel
  privaatrechtelijke ZBO's (loodsencorporaties, keuringsinstanties, CBR, RDW, LVNL…).
- Ook Planbureau voor de Leefomgeving (PBL) als knoop — buiten de vier types.

### Ministerie van Onderwijs, Cultuur en Wetenschap — `ocw.pdf`

**29 organen.** Pattern: gemengd.

- Agentschap (2): DUO (eigen DG-kolom), Nationaal Archief + RCE (onder DG Cultuur) — **op chart**.
- Inspectie (2): Inspectie van het Onderwijs, Inspectie Overheidsinformatie en Erfgoed — **op chart** (blokken rechtsboven).
- Adviescollege (3): Onderwijsraad, Raad voor Cultuur, AWTI — **op chart** als "Ondersteunend bureau [Raad]".
- ZBO (22): NWO, KNAW, NPO, KB, NVAO, Nuffic, SBB, cultuurfondsen, CvTE, CvdM… — **niet op chart**.

### Ministerie van Economische Zaken en Klimaat — `ezk.pdf`

**26 organen.** Pattern: kleurgecodeerd (legenda). Deelt bewindspersonen/DG's met Klimaat en Groene Groei (KGG).

- Agentschap (2): RVO, DICTU — **op chart** (buitendiensten).
- Inspectie (1): RDI — **op chart** (+ toezichthouders SodM, ACM, NEa gekleurd).
- Adviescollege (4): CPB, Productiviteitsraad, ATR-secretariaat, WKR — **op chart** (adviescollege-kleur).
- ZBO (19): CBS, KVK, TNO, RvA, IMG, ACM… — grotendeels **niet op chart** (behalve ACM/CBS-achtigen).

### Ministerie van Binnenlandse Zaken en Koninkrijksrelaties — `bzk.pdf`

**24 organen.** Pattern: gemengd. Chart bevat ook VRO (aparte minister).

- Agentschap (9): RVB, Logius, RvIG, SSC-ICT, ODI, RBL, FMH, O&P Rijk, DHC — **op chart**, als shared-service-clusters onder DG Vastgoed en Bedrijfsvoering Rijk / DG Digitalisering.
- ZBO (8): Kadaster, Huurcommissie, Huis voor Klokkenluiders, TloKB, SVWN, SAIP… — **op chart** in aparte kaderboxen onderaan.
- Adviescollege (7): Kiesraad, ACOI, Adviescollege ICT-toetsing, ROB, ARPA, ACVG, AC-NGT… — **op chart** in kaderboxen.
- (BZK is daarmee de uitzondering die ZBO's én adviescolleges wél toont.)

### Ministerie van Landbouw, Visserij, Voedselzekerheid en Natuur — `lvvn.pdf`

**21 organen.** Pattern: alleen agentschap. Sterk verweven met EZK (gedeelde onderdelen).

- Inspectie (1): NVWA — **op chart** (buitendienst).
- ZBO (19): grondkamers, NAK/KCB/BKD/COKZ (keuringsdiensten), Ctgb, Staatsbosbeheer, Skal, CCD… — **niet op chart**.
- Adviescollege (1): Adviescollege huis- en hobbydierenlijst — **niet op chart**.

### Ministerie van Sociale Zaken en Werkgelegenheid — `szw.png`

**6 organen.** Pattern: gemengd.

- Inspectie (1): Nederlandse Arbeidsinspectie — **op chart** als volwaardige DG-kolom (Inspecteur-generaal).
- Agentschap (0 in export als "Agentschap", maar chart toont Nederlandse Autoriteit Uitleenmarkt aan SG).
- ZBO (5): UWV, SVB, bedrijfstakpensioenfondsen, Blik op Werk, certificerende instellingen — **niet op chart** (ook SER ontbreekt).

### Ministerie van Financiën — `financien.pdf`

**5 organen.** Pattern: gemengd.

- Inspectie (1): Inspectie Belastingen, Toeslagen en Douane (IBTD) — **op chart** als blok onder SG. (Let op: "Inspectie der Rijksfinanciën" op de chart is een interne directie, geen los orgaan.)
- ZBO (4): DNB, AFM, Waarderingskamer, CEA — **niet op chart**.
- Agentschappen op chart (Agentschap Gen. Thesaurie, Auditdienst Rijk, Domeinen Roerende Zaken) staan in de export niet als los "Agentschap"-type maar als interne dienstonderdelen.

### Ministerie van Buitenlandse Zaken — `bz.pdf`

**3 organen.** Pattern: alleen intern.

- Adviescollege (3): AIV, CAVV, Staatscommissie IPR — **niet op chart** (chart toont enkel DG's, directies, Postennet).

### Ministerie van Defensie — `defensie.jpg`

**3 organen.** Pattern: minimaal/intern (militaire commandostructuur).

- Agentschap (1): Paresto — **niet zichtbaar** als zodanig.
- Inspectie (2): IGK, Inspectie Veiligheid Defensie — **niet zichtbaar** (chart toont CDS → krijgsmachtdelen, Marechaussee, Bestuursstaf).

### Ministerie van Algemene Zaken — `az.png`

**1 orgaan.** Pattern: minimaal.

- Agentschap (1): Dienst Publiek en Communicatie (DPC) — **niet op** de gedownloade versie (organogram uit 2023).

---

## Ministeries zonder eigen gedownload organogram

De export kent 15 ministeries; 3 daarvan staan op het organogram van een "moeder"-ministerie:

- **Asiel en Migratie** → staat als DGM-kolom op het **JenV**-organogram.
- **Klimaat en Groene Groei (KGG)** → gedeelde bewindspersonen/DG's op het **EZK**-organogram.
- **Volkshuisvesting en Ruimtelijke Ordening (VRO)** → aparte minister op het **BZK**-organogram.

Deze drie hebben in de export weinig tot geen eigen actieve organen van de vier types (ze zijn recent
afgesplitst); hun organen staan grotendeels nog onder BZK/EZK/JenV geregistreerd.

---

## Consequenties voor de org-chart in Wies

- **Betrouwbaar te automatiseren:** ministerie-koppeling (`relatieMetMinisterie`) en de vier typelabels
  komen rechtstreeks uit de sync — die staan al in `OrganizationUnit.related_ministry_tooi` en
  `organization_types`.
- **Positie binnen het ministerie is _niet_ in de export gecodeerd** (de export is een platte
  boom via `parent`; de organogram-positie "onder welk DG" staat er niet in). Wil je agentschappen onder
  het juiste DG hangen zoals JenV/BZK doen, dan is dat een handmatige/afgeleide mapping, niet uit de data.
- **Aanrader:** toon de vier types als een aparte **"gerelateerde organen"-laag** per ministerie
  (zoals VWS's "Tot het ministerie behoren ook"), gegroepeerd per type, i.p.v. te proberen ze in de
  DG-boom te nesten. Overweeg de privaatrechtelijke ZBO's (zorgkantoren, keuringsinstanties) standaard te
  verbergen — dat is precies wat de rijksoverheid zelf op de charts doet.

Zie `analysis.json` voor de volledige, machineleesbare lijst (ministerie → type → alle organen).
