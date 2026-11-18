# BIO-checklist Wies

Hoe Wies voldoet aan de Baseline Informatiebeveiliging Overheid (BIO), per
maatregel: de status, de toelichting en waar het bewijs staat. Bewijs in de
vorm van een screenshot staat op de O-schijf in de map BIO.

Statussen: **Voldoet**, **Deels**, **Onderhanden**, **n.v.t.**

## 5.03 Toegang tot bedrijfsmiddelen

**Er zijn maatregelen getroffen die onbedoelde of ongeautoriseerde toegang tot
bedrijfsmiddelen waarnemen of voorkomen.** — Voldoet

RBAC met 3 rollen (Beheerder, Consultant, BDM). Permission engine op veld-niveau
(`permission_engine.py`). LoginRequiredMiddleware actief. Email-domein whitelist
(@rijksoverheid.nl, @minbzk.nl).

Bewijs: [RBAC](../../wies/core/roles.py),
[permission definitions](../../wies/core/permission_engine.py),
[login required en allowed domains](../../config/settings/base.py)

## 5.12 Classificatie van informatie

**De informatie in alle informatiesystemen is door middel van een expliciete
risicoafweging geclassificeerd, zodat duidelijk is welke bescherming nodig
is.** — Voldoet

Wies verwerkt geen gerubriceerde informatie (geen Dep-V/Stg). Bevat
persoonsgegevens (namen, e-mail, plaatsingsgegevens) die worden vermeld in de
privacyverklaring. Deze gegevensset is besproken met de CISO.

Bewijs: [privacyverklaring](../privacy.md)

## 5.14 Informatieoverdracht

**Voor de beveiliging van elektronische (e-mail)berichten gelden de vastgestelde
open standaarden tegen phishing en afluisteren op de 'pas toe of leg uit'-lijst
van het Forum Standaardisatie. Voor beveiliging van websiteverkeer gelden de
open standaarden tegen afluisteren op de 'pas toe of leg uit'-lijst van het
Forum Standaardisatie.** — n.v.t.

Wies verstuurt geen mails.

**Voor veilige berichtenuitwisseling met basisregistraties wordt, conform de
'pas toe of leg uit'-lijst van het Forum Standaardisatie, gebruik gemaakt van de
actuele versie van Digikoppeling.** — n.v.t.

Geen berichtenuitwisseling.

**Maak bij openbaar webverkeer van gevoelige gegevens gebruik van ten minste
publiek vertrouwde Organization Validated-certificaten. Maak bij intern
webverkeer voor gevoelige gegevens gebruik van ten minste publieke vertrouwde
OV-certificaten of private PKIo-certificaten. Hogere eisen aan certificaten
kunnen voortvloeien uit een risicoanalyse, aansluitvoorwaarden of
wetgeving.** — Deels

Wel encryptie via Let's Encrypt. OV-certificaten lijken wel nodig. We gaan deze
aanvragen. Actie: Robbert U.

Bewijs: `lets_encrypt.png`

**Om zekerheid te bieden over de integriteit van het elektronische bericht,
wordt voor elektronische handtekeningen gebruik gemaakt van de AdES Baseline
Profile standaard.** — n.v.t.

Geen berichtenuitwisseling.

## 5.15 Toegangsbeveiliging

**Alleen geauthentiseerde apparatuur kan toegang krijgen tot een vertrouwde
zone.** — Voldoet

Netwerktoegang wordt afgedwongen door SSO-Rijk en de hosting-omgeving. Wies
dwingt OIDC-authenticatie af via Keycloak.

Bewijs: [login required](../../config/settings/base.py),
[authenticatie-backend](../../wies/rijksauth/auth_backend.py),
[authenticatie over OIDC](../../wies/rijksauth/views.py)

**Gebruikers met eigen of ongeauthentiseerde apparatuur (Bring Your Own Device)
krijgen alleen toegang tot een onvertrouwde zone.** — n.v.t.

## 5.16 Identiteitsbeheer

**Er is een sluitende formele registratie- en afmeldprocedure voor het beheren
van gebruikersidentificaties.** — Voldoet

`create_user()` service en `delete_user` endpoint met Event-logging. Unieke
email als identifier. Alleen beheerders mogen gebruikers aanmaken/verwijderen.
Netwerktoegang wordt afgedwongen door SSO-Rijk en de hosting-omgeving.

Bewijs: [user create service](../../wies/core/services/users.py),
[user delete endpoint](../../wies/core/views/users.py),
[unieke email](../../wies/rijksauth/models.py),
[RBAC](../../wies/core/roles.py),
[permission definitions](../../wies/core/permission_engine.py)

**Het gebruiken van groepsaccounts is niet toegestaan, tenzij dit wordt
gemotiveerd en vastgelegd door de proceseigenaar.** — Voldoet

## 5.17 Authenticatie-informatie

**Bij het aanloggen op een vertrouwde zone:**
**(a) is het gebruik van tweefactor-authenticatie altijd verplicht;**
**(b) is de minimale wachtwoordlengte 12 posities en wordt het wachtwoord
minimaal halfjaarlijks vernieuwd als geen tweefactor-authenticatie mogelijk is
(zie ook 8.5.1);**
**(c) mogen wachtwoorden niet worden hergebruikt;**
**(d) zijn de tekens van een wachtwoord zo willekeurig mogelijk gekozen dat
individuele tekens of combinaties van tekens geen voorspellende waarde hebben
voor de rest van het wachtwoord;**
**(e) is het aantal inlogpogingen maximaal 5;**
**(f) is de tijdsduur vastgelegd dat een account wordt geblokkeerd na
overschrijding van het aantal keer foutief inloggen;**
**(g) wordt in het bewustwordingsprogramma en de gedragsregels ingegaan op het
belang van het hebben van goede wachtwoorden.**
**Vanuit een vertrouwde zone mag op basis van een risicoafweging afgeweken
worden van bovenstaande regels.** — n.v.t., SSO

**De eisen aan wachtwoorden moeten geautomatiseerd worden afgedwongen.** —
n.v.t., SSO

**Van initiële wachtwoorden en wachtwoorden die gereset zijn, wordt automatisch
afgedwongen dat deze bij het eerste gebruik worden gewijzigd.** — n.v.t., SSO

## 5.18 Toegangsrechten

**Er is uitsluitend toegang verleend tot informatiesystemen na autorisatie door
een bevoegde functionaris.** — Voldoet

Gebruikers worden aangemaakt door Beheerders (permission: `change_user`).
Roltoewijzing via groepen. Staff-toegang beperkt tot `STAFF_EMAILS` whitelist.

Bewijs: [RBAC](../../wies/core/roles.py),
[permission definitions](../../wies/core/permission_engine.py)

### 5.18.1

**Alle uitgegeven toegangsrechten worden minimaal eenmaal per jaar
beoordeeld.** — Voldoet

Gebruikerslijst zichtbaar voor Beheerders in de interface.

Bewijs: `gebruikers_lijst.png`

**Ongeautoriseerde afwijkingen op of ongeautoriseerde aanpassingen aan
uitgegeven toegangsrechten worden beschouwd als beveiligingsgebeurtenis en als
zodanig vastgelegd en afgehandeld.** — Voldoet

Event-model logt user create/update/delete. AuthEvent logt login
success/failure. Groepswijzigingen (rolveranderingen) worden gelogd als
onderdeel van User.Update. Beveiligingsgebeurtenissen worden bijgehouden in
GitHub security advisories.

Bewijs: [Event-model](../../wies/core/models.py),
[AuthEvent-model](../../wies/rijksauth/models.py),
[user update](../../wies/core/services/users.py),
[security advisories](https://github.com/RijksICTGilde/wies/security/advisories)

**Er is een actueel mandaatregister of er zijn functieprofielen waaruit blijkt
welke personen bevoegdheden hebben voor het verlenen van
toegangsrechten.** — Voldoet

Rollen zijn gedefinieerd in [`roles.py`](../../wies/core/roles.py) en zichtbaar
in de GitHub-repo. Zichtbaar wie beheerder is in de gebruikerslijst op
https://wies.rijksorganisatieodi.nl/beheer/gebruikers/.

Bewijs: [RBAC](../../wies/core/roles.py),
[permission definitions](../../wies/core/permission_engine.py),
[controle speciale rollen](20261014_speciale_rollen.md)

**Alle uitgegeven toegangsrechten worden minimaal eenmaal per halfjaar
beoordeeld.** — Voldoet

Zie 5.18.1.

## 5.24 Incidentbeheer

**Een Coordinated Vulnerability Disclosure (CVD)-procedure is gepubliceerd en
ingericht, inclusief de opvolging. Voorheen werd Coordinated Vulnerability
Disclosure (CVD) responsible disclosure genoemd.** — Voldoet

`/.well-known/security.txt` redirect naar NCSC. Standaard CVD-kanaal voor
rijksoverheid.

Bewijs: [redirect naar NCSC](../../config/urls.py)

**Informatie afkomstig uit de Coordinated Vulnerability Disclosure
(CVD)-procedure is onderdeel van de incidentrapportage.** — n.v.t.

**Informatiebeveiligingsincidenten die hebben geleid tot een vermoedelijk of
mogelijk opzettelijke inbreuk op de beschikbaarheid, vertrouwelijkheid of
integriteit van informatieverwerkende systemen, behoren zo snel mogelijk
(binnen 72 uur) al dan niet geautomatiseerd te worden gemeld aan het NCSC
(alleen voor rijksoverheidsorganisaties) of de sectorale CERT.** — n.v.t.

## 5.33 Bewaartermijnen

**De proceseigenaar heeft per soort informatie inzichtelijk gemaakt wat de
bewaartermijn is.** — Deels, onderhanden

Geen retentiebeleid geïmplementeerd. Event-tabel groeit onbeperkt. Geen
automatische cleanup. Daarnaast nog geen beleid over uit dienst treding en
historische opdrachten.

- TODO: retentiebeleid implementeren / opstellen
- TODO: delete user → annoteren `deleted_at`? (#419)

## 5.34 Naleving privacy

**Organisaties controleren regelmatig de naleving van de privacyregels en
informatieverwerking en -procedures binnen hun verantwoordelijkheidsgebied aan
de hand van de desbetreffende beleidsregels, normen en andere eisen betreffende
beveiliging.** — n.v.t.

## 6.08 Melden van incidenten

**Incidenten worden zo snel mogelijk, maar in ieder geval binnen 24 uur na
bekendwording, intern gemeld.** — Deels, onderhanden

Aan wie moet dit worden gemeld? Aan de CISO?

## 8.02 Speciale bevoegdheden

**De uitgegeven speciale bevoegdheden worden minimaal ieder kwartaal
beoordeeld.** — Voldoet

Drie rollen met duidelijke permissies. Rollen zichtbaar in UI. Staff-toegang via
`STAFF_EMAILS` env var. Env var zichtbaar in ZAD.

Bewijs: [controle speciale rollen](20261014_speciale_rollen.md)

## 8.03 Beperking toegang tot informatie

**Er zijn maatregelen genomen die het fysiek en/of logisch isoleren van
informatie met specifiek belang waarborgen.** — Voldoet

Permission engine dwingt veld-niveau toegang af. Row-level checks via
`has_permission()`.

Bewijs: [RBAC](../../wies/core/roles.py),
[permission definitions](../../wies/core/permission_engine.py)

**Gebruikers kunnen alleen die informatie met specifiek belang inzien en
verwerken die ze nodig hebben voor de uitoefening van hun taak.** — Voldoet

Er is een beperkte dataset gemaakt die alle ingelogde gebruikers mogen zien. Wel
is de bewerking beperkt per rol. Alle mutaties worden gelogd.

Bewijs: [dataset in de privacyverklaring](../privacy.md),
[RBAC](../../wies/core/roles.py),
[permission definitions](../../wies/core/permission_engine.py)

## 8.05 Veilige authenticatie

**Als vanuit een onvertrouwde zone toegang wordt verleend naar een vertrouwde
zone, gebeurt dit alleen op basis van minimaal tweefactor-authenticatie.** —
Voldoet

SSO-Rijk/Keycloak dwingt MFA af.

## 8.07 Bescherming tegen malware

**Het downloaden van bestanden is beheerst en beperkt op basis van risico en
need-of-use.** — Voldoet

Op dit moment niet mogelijk om te downloaden.

**Gebruikers zijn voorgelicht over de risico's ten aanzien van surfgedrag en
het klikken op onbekende links.** — n.v.t.

**De gebruikte antimalwaresoftware en bijbehorende herstelsoftware is actueel
en wordt ondersteund door periodieke updates.** — n.v.t.

**De malwarescan wordt uitgevoerd op:**
**(a) alle omgevingen, bijvoorbeeld op mailservers, (desktop)computers en bij de
toegangsverlening tot het netwerk van de organisatie;**
**(b) alle gedownloade content voorafgaand aan executie of opslag;**
**(c) alle bestanden die via netwerken of via elke vorm van opslagmedium zijn
ontvangen, vóór gebruik of opslag in de eigen omgeving.** — n.v.t.

## 8.08 Beheer van technische kwetsbaarheden

**Als de kans op misbruik en de verwachte schade beide hoog zijn (bijvoorbeeld
met de NCSC-Inschalingsmatrix beveiligingsadviezen of
leveranciersbeveiligingsadviezen), worden passende mitigerende maatregelen zo
snel mogelijk, maar uiterlijk binnen een week getroffen.** — Voldoet

TODO: waarom voldoen we hieraan?

**Op basis van een expliciete risicoafweging wordt bepaald op welke wijze
mitigerende maatregelen getroffen worden.** — Voldoet

Dependabot signaleert kwetsbaarheden. Geen formeel risicoafwegingsproces
gedocumenteerd. Proces in GitHub Security Advisory aanhouden.

- TODO: risicoafwegingsproces maken
- TODO: melding Dependabot in Mattermost

**In de tussentijd of als installatie binnen een week niet mogelijk is, worden
op basis van een expliciete risicoafweging mitigerende maatregelen
getroffen.** — Voldoet

TODO: toevoegen aan `security.md`

**Informatiesystemen worden bij voorkeur jaarlijks gecontroleerd op technische
naleving van beveiligingsnormen en risico's ten aanzien van de feitelijke
veiligheid. Dit kan bijvoorbeeld door (geautomatiseerde)
kwetsbaarheidsanalyses, penetratietesten of red-teamingstesten.** — Voldoet

Beveiligingsaudits of penetratietest wordt gepland.

**Internetfacing-systemen hebben een verplichte (bij voorkeur geautomatiseerde)
penetratietest bij iedere nieuwe release of major update. Als daar bevindingen
met een hoog risico uitkomen, mag het systeem niet in productie.** — Voldoet

Test pipeline bevat security tests, daarnaast draait er een automatische
security check of PR's vulnerabilities introduceren en waarschuwt Dependabot
voor vulnerabilities bij dependencies.

Bewijs: [access control tests](../../wies/core/tests/test_access_control.py),
[permission tests](../../wies/core/tests/),
[role tests](../../wies/core/tests/test_role_matrix.py),
`security_scan_dependencies.png`, `security_scanning_config.png`

## 8.13 Back-up van informatie

**Er is een back-up beleid waarin de eisen voor het bewaren en beschermen zijn
gedefinieerd en vastgesteld. Er moet speciale aandacht zijn voor het beschermen
van de back-up tegen ransomware-aanvallen.** — Voldoet

Backups via ZAD. Back-upperiode vermeld in het beheerdocument.

TODO Robbert U: uitzoeken welke maatregelen er moeten worden genomen tegen
ransomware.

Bewijs: [beheerdocument](../beheer.md)

**Op basis van een expliciete risicoafweging is bepaald wat het maximaal
toegestane dataverlies is en wat de maximale hersteltijd is na een
incident.** — Voldoet

Zie punt hieronder.

**In het back-upbeleid staan minimaal de volgende eisen:**
**(a) Dataverlies bedraagt maximaal 28 uur.**
**(b) Hersteltijd in geval van incidenten is maximaal 16 werkuren (2 dagen van
8 uur) in 85% van de gevallen.** — Voldoet

TODO: toevoegen in securityproces

**Het back-upproces voorziet in opslag van de back-up op een locatie, waarbij
een incident op de ene locatie niet kan leiden tot schade op de andere.** —
Voldoet

**Zorg dat ten minste één back-up niet online benaderbaar is en beschermd wordt
tegen veranderingen.** — Voldoet

**De herstelprocedure wordt minimaal jaarlijks getest of na een grote wijziging,
om de goede werking te waarborgen als deze in noodgevallen uitgevoerd moet
worden.** — Voldoet

Bewijs: `periodieke_beheertaken.png`

## 8.15 Logging

**Een logregel bevat minimaal:**
**(a) de gebeurtenis;**
**(b) de benodigde informatie die nodig is om het incident met hoge mate van
zekerheid te herleiden tot een natuurlijk persoon;**
**(c) het gebruikte apparaat;**
**(d) het resultaat van de handeling;**
**(e) een datum en tijdstip van de gebeurtenis.** — Voldoet

Bewijs: [Event-model](../../wies/core/models.py)

**Een logregel bevat in geen geval gegevens die tot het doorbreken van de
beveiliging kunnen leiden.** — Voldoet

Event-tabel slaat geen wachtwoorden, tokens of sessiegegevens op. AuthEvent logt
alleen email + success/failure.

Bewijs: [Event-model](../../wies/core/models.py),
[AuthEvent-model](../../wies/rijksauth/models.py)

**Er is een overzicht van logbestanden die worden gegenereerd.** — Voldoet,
onderhanden

Twee audit-tabellen (Event, AuthEvent) in PostgreSQL. Console logging op
INFO-niveau.

TODO: toevoegen aan beheerdocument

**Ten behoeve van de loganalyse is op basis van een expliciete risicoafweging de
bewaarperiode van de logging bepaald. Binnen deze periode is de beschikbaarheid
van de loginformatie gewaarborgd.** — Deels, onderhanden

TODO: bewaarperiode bepalen en vastleggen

**Oneigenlijk wijzigen, verwijderen of pogingen daartoe van loggegevens worden
zo snel mogelijk gemeld als beveiligingsincident via de procedure voor
informatiebeveiligingsincidenten conform control 5.24.** — Voldoet

Logging wijzigen via de applicatie is niet mogelijk. Wordt gemeld als het
bekend is.

TODO: hoe moet dit gemeld worden?

**Minimaal halfjaarlijks wordt door een onafhankelijke functionaris (ten
opzichte van de uitvoering) getoetst op het ongewijzigd bestaan van logbestanden
gedurende de bewaartermijn.** — Voldoet

Bewijs: `periodieke_beheertaken.png`

## 8.21 Beveiliging netwerkdiensten

**In koppelpunten met externe of onvertrouwde zones zijn maatregelen getroffen
om mogelijke aanvallen die de beschikbaarheid van de informatievoorziening
negatief beïnvloeden (bijvoorbeeld DDoS-aanvallen, Distributed Denial of
Service attacks) te signaleren en hierop te reageren.** — Onderhanden

TODO Robbert U: uitvragen bij ODC Noord

## 8.24 Gebruik van cryptografie

**In het cryptografiebeleid zijn minimaal de volgende onderwerpen uitgewerkt:**
**(a) Wanneer cryptografie ingezet wordt.**
**(b) Wie verantwoordelijk is voor de implementatie.**
**(c) Wie verantwoordelijk is voor het sleutelbeheer.**
**(d) Welke normen als basis dienen voor cryptografie en de wijze waarop de
normen van het Forum Standaardisatie worden toegepast.**
**(e) De wijze waarop het beschermingsniveau vastgesteld wordt.**
**(f) Bij communicatie tussen organisaties wordt het beleid onderling
vastgesteld.** — Deels, onderhanden

TODO: moet worden opgenomen in securitydocument

**Cryptografische toepassingen voldoen aan passende standaarden van het Forum
Standaardisatie.** — Voldoet

**De sterkte van de cryptografie wordt waar mogelijk gebaseerd op de actuele
adviezen van het NCSC.** — Voldoet

**In geval van PKIoverheid-certificaten hanteer de PKIoverheid-eisen ten
aanzien van het sleutelbeheer. In overige situaties hanteer de norm ISO 11770-1
voor het beheer van cryptografische sleutels.** — Voldoet

**Er zijn (contractuele) afspraken over reservecertificaten van een alternatieve
leverancier als uit risicoafweging blijkt dat deze noodzakelijk zijn.** — n.v.t.

## Security by design

**De gangbare principes rondom 'security by design' zijn uitgangspunt voor de
ontwikkeling van software en systemen.** — Voldoet

- **Least privilege & secure defaults:** authenticatie verloopt uitsluitend via
  SSO-Rijk (OIDC/Keycloak); de applicatie kent zelf geen wachtwoorden en geen
  groepsaccounts. Autorisatie is rolgebaseerd (Beheerder, Consultant, BDM) en
  wordt per view en queryset afgedwongen.
- **Defense in depth:** Django's ingebouwde bescherming tegen CSRF, XSS (Jinja2
  auto-escaping) en SQL-injectie (ORM) wordt actief gebruikt; ruwe SQL wordt
  vermeden.
- **Reduce attack surface:** geen externe runtime-afhankelijkheden in de
  browser: JavaScript (htmx) is gevendored in plaats van via een CDN geladen,
  zodat de Content Security Policy geen externe bronnen hoeft toe te staan.

Bewijs: [RBAC](../../wies/core/roles.py),
[permission definitions](../../wies/core/permission_engine.py),
[CSP-policy](../../wies/core/middleware.py)

## 8.29 Beveiligingstesten

**Voor acceptatietesten van systemen worden gestructureerde testmethodieken
gebruikt. De testen worden bij voorkeur geautomatiseerd uitgevoerd.** — Voldoet

Django TestCase-framework met `just test`. CI-pipeline via GitHub Actions.
Pre-commit hooks.

Bewijs: [testworkflow](../../.github/workflows/test.yml)

**Van de resultaten van de testen wordt verslag gemaakt.** — Voldoet

CI-pipeline genereert testresultaten. Eventueel testresultaten opnemen in
release packages: onderzoekend.

## 8.31 Scheiding van ontwikkel-, test- en productieomgevingen

**Cryptografische toepassingen voldoen aan passende standaarden van het Forum
Standaardisatie.** — dubbel, zie 8.24

**In de productieomgeving wordt niet getest. Alleen met voorafgaande goedkeuring
door de proceseigenaar en schriftelijke vastlegging hiervan, kan hiervan worden
afgeweken.** — Voldoet

Bewijs: `separate_deployments.png`

**Wijzigingen in de productieomgeving worden altijd getest voordat zij in
productie gebracht worden. Alleen met voorafgaande goedkeuring door de
proceseigenaar en schriftelijke vastlegging hiervan, kan hiervan worden
afgeweken.** — Voldoet

GitHub PR-workflow met review (4-ogenprincipe). Test pipeline checkt of wordt
voldaan aan alle eisen. Als tests niet slagen kan de branch niet naar main
worden gemerged.

Bewijs: `github_ruleset.png`

**In de procedure voor wijzigingenbeheer is minimaal aandacht besteed aan:**
**(a) het administreren van wijzigingen;**
**(b) risicoafweging van mogelijke gevolgen van de wijzigingen;**
**(c) goedkeuringsprocedure voor wijzigingen.** — Voldoet

Git + GitHub PR-workflow. CI checks (tests, linting). Django migrations voor
databasewijzigingen. PR-review als goedkeuringsprocedure.

Bewijs: `pr_approval.png`, [testworkflow](../../.github/workflows/test.yml)

**Wijzigingsbeheer vindt plaats op basis van een algemeen geaccepteerd
beheerraamwerk.** — Voldoet

Git-based workflow met GitHub als beheerplatform. Dependabot voor dependency
updates.
