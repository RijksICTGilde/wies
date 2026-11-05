<!--
  Source of truth for this handbook page, also shown in Wies at /handboek/.
  After editing, regenerate the in-product pages:
      uv run python manage.py generate_docs_html
-->

# Data, privacy en beveiliging

Wies verwerkt persoonsgegevens van collega's. Daar gaan we zuinig mee om: we bewaren weinig, tonen nog minder, en laten onszelf regelmatig controleren.

## Gegevens

| Gegeven                                                                       | Waar het vandaan komt                 | Wie het ziet                                                                                |
| ----------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------- |
| Naam en zakelijk e-mailadres                                                  | Gebruikersbeheer in Wies              | Alle gebruikers                                                                             |
| Inlog-id (OIDC-subject)                                                       | SSO Rijk, bij de eerste keer inloggen | Niemand in de app; alleen voor het inloggen                                                 |
| Labels en merk (bv. expertise)                                                | De collega zelf of gebruikersbeheer   | Alle gebruikers                                                                             |
| Lopende plaatsingen en opdrachten                                             | Wies zelf en OTYS                     | Alle gebruikers                                                                             |
| Afgelopen en toekomstige plaatsingen                                          | Wies zelf en OTYS                     | De collega zelf en business managers                                                        |
| Contracturen per periode, en daarmee de datum uit dienst                      | Gebruikersbeheer                      | Business managers en gebruikersbeheerders                                                   |
| Uren per week op een rol                                                      | Business managers                     | Business managers; bij een open aanvraag iedereen                                           |
| Opdrachtgevers (overheidsorganisaties)                                        | organisaties.overheid.nl              | Alle gebruikers                                                                             |
| Audit-log: wie wat wijzigde, inlogpogingen, rolwijzigingen, IP-adres, browser | Automatisch                           | Niemand in de app; alleen voor incidentonderzoek                                            |
| Foutmeldingen: de fout met stacktrace, pagina en gebruiker                    | Automatisch, bij een fout in de app   | Applicatiebeheerders; het teamkanaal op Mattermost krijgt alleen het soort fout en een link |

## Privacy

Voor privacy, beveiligingsbeleid en regelgeving werken we samen met Patrick Keizer, CISO en privacy officer van ODI, die ons adviseert over beleid en de AVG.

- De grondslag is gerechtvaardigd belang (AVG artikel 6, lid 1, sub f). Een pre-scan DPIA liet zien dat een volledige DPIA niet nodig is; we werken de pre-scan bij als nieuwe functies daarom vragen.
- Collega's zien van elkaar alleen lopende opdrachten. Wat voorbij is of nog komt, ziet alleen de collega zelf en een business manager.
- De audit-log staat nooit in de app. Ook het e-mailadres in een logregel wordt nergens getoond.
- Geen cookies of andere middelen om gedrag te volgen.
- Alle gegevens blijven in Nederland, in het Overheidsdatacenter Noord (ODC-Noord). We maken dagelijks een back-up en bewaren er maximaal zeven.
- Opdrachten die uit OTYS komen, controleren business managers op vertrouwelijke informatie in de omschrijving, zodat die niet via Wies voor iedereen leesbaar wordt. Opdrachten die ze zelf invoeren, schrijven ze in het besef dat alle collega's ze kunnen lezen.
- Wies hoeft niet gearchiveerd te worden als website: het is een applicatie achter een inlog. Dat is afgestemd met de CIO van BZK.
- Je rechten als gebruiker staan in de [privacyverklaring](../privacy.md).

## Bewaartermijnen

Hoe lang we wat bewaren, stemmen we af met de privacy officer en de business managers. Ons voorstel:

| Gegeven                      | Voorstel                                                                                                                                                                                                                     |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Naam en zakelijk e-mailadres | Verwijderen bij uitdiensttreding; het profiel blijft daarna nog 3 maanden zichtbaar voor business managers, gelijk aan de termijn in de Active Directory van SSC-ICT                                                         |
| Plaatsingen                  | Niet verwijderen maar anonimiseren: de koppeling tussen persoon en opdracht wordt losgeknipt, zodat te zien blijft welke opdrachten voor welke opdrachtgevers zijn gedaan, zonder dat dat naar een persoon herleidbaar is    |
| Audit-log                    | Niet anonimiseren of verwijderen bij uitdiensttreding, want dan verdwijnen de sporen die je bij een incident nodig hebt; bewaren voor een termijn van 12 tot 24 maanden, op basis van een risicoafweging zoals de BIO vraagt |

Anonimiseren heeft een tweede voordeel boven direct verwijderen: een vergissing is terug te draaien.

## Hosting

Wies draait in het Overheidsdatacenter Noord (ODC-Noord), op [ZAD](https://zad.rijksapp.nl/introductie): Zelfservice Applicatie Deployment, een deploymentplatform op Kubernetes dat het Digi Gilde zelf ontwikkelt. Ook ZAD is open source: [RIG-Cluster op GitHub](https://github.com/RijksICTGilde/RIG-Cluster).

- Uitrol gaat via GitOps met ArgoCD: wat in Git staat, wordt uitgerold.
- Ontwikkelaars beheren deployments, back-ups en testomgevingen per branch zelf, via een portaal en een API.
- Geheimen zoals wachtwoorden en sleutels staan versleuteld in Git, met SOPS en AGE.
- Per project levert ZAD een eigen PostgreSQL-database (CloudNativePG) en Keycloak, dat de inlog doorgeeft aan SSO Rijk.
- Bestanden, zoals de startpagina, staan in S3-compatibele objectopslag van ZAD. Op productie is dat nog MinIO. ZAD vervangt MinIO door SeaweedFS, omdat MinIO niet meer wordt onderhouden; voor Wies verandert daarbij niets, want de app ziet dezelfde `OBJECT_STORE_*`-instellingen en dezelfde S3-koppeling.
- Er zijn gescheiden omgevingen voor test en productie, met TLS op alle verkeer van buiten.

## Inloggen

Collega's loggen in met hun rijksaccount via SSO Rijk, de inlogdienst voor rijksmedewerkers. Wies praat niet rechtstreeks met SSO Rijk: Keycloak zit ertussen als makelaar en is aan SSO Rijk gekoppeld. Wies spreekt met Keycloak via OpenID Connect (OIDC). Hoe SSO Rijk en Keycloak samenwerken, staat in het [Digi Handboek](https://digihandboek.rijks.app/kennis/sso-rijk-keycloak/).

1. Je klikt op inloggen. Wies stuurt je door naar Keycloak, en Keycloak naar SSO Rijk.
2. Je logt in met je rijksaccount. SSO Rijk geeft via Keycloak onder meer je naam en e-mailadres terug.
3. Wies zoekt je account op. Bij de eerste keer koppelt Wies je vaste inlog-id (het OIDC-subject) aan het account dat een gebruikersbeheerder voor jouw e-mailadres heeft klaargezet. Daarna herkent Wies je aan dat inlog-id.
4. Heeft niemand een account voor je klaargezet, of is je e-mailadres niet bevestigd door SSO Rijk? Dan kom je niet binnen.

Een account dat al aan een inlog-id hangt, wordt nooit aan een ander inlog-id gekoppeld, ook niet bij hetzelfde e-mailadres. Zo kan niemand een account overnemen met een nagemaakt e-mailadres. Accounts aanmaken kan alleen voor e-mailadressen op een toegestaan domein (standaard `@rijksoverheid.nl` en `@minbzk.nl`, in te stellen met `ALLOWED_EMAIL_DOMAINS`). De code zit in `wies/rijksauth/`.

## Beveiliging

- Wies volgt de [Baseline Informatiebeveiliging Overheid (BIO2)](https://www.bio-overheid.nl/). Controles, zoals wie speciale rollen heeft op productie, leggen we vast in [docs/bio](../bio/).
- Binnenkort laten we Wies testen met een penetratietest. De nadruk ligt op:
  1. Autorisatie: kan iemand objecten of pagina's zien of wijzigen waar die geen recht op heeft?
  2. Privacy van plaatsingen: zijn afgelopen en toekomstige plaatsingen echt afgeschermd?
  3. Authenticatie: is de keten SSO Rijk, Keycloak, Wies als geheel veilig?
  4. Lekken van persoonsgegevens via foutmeldingen of logging.
  5. Het ZAD-platform: de API, de geheimen, de GitOps-uitrol en de scheiding tussen omgevingen.
- Inloggen gaat alleen via SSO Rijk. Wies bewaart geen wachtwoorden en heeft geen gedeelde accounts.
- Accounts zijn alleen op uitnodiging: een gebruikersbeheerder zet je e-mailadres klaar, en pas dan kun je inloggen.
- Rechten worden per object en per veld gecontroleerd, niet alleen per pagina (zie [Rollen en rechten](de-code.md#rollen-en-rechten)).
- Elke wijziging wordt door een tweede ontwikkelaar nagekeken (vier-ogenprincipe) en automatisch getest.
- Afhankelijkheden en de container worden bij elke wijziging en dagelijks gescand op bekende kwetsbaarheden (Trivy); Dependabot stelt updates voor.
- Wies laadt geen code van andere websites; de Content-Security-Policy staat het niet toe.
- Een kwetsbaarheid melden kan via ons [beveiligingsbeleid](../../SECURITY.md).

## Toegankelijkheid

- Wies is onderzocht volgens WCAG 2.2, niveau AA, en heeft status A: voldoet volledig. De verklaring staat in het [register van toegankelijkheidsverklaringen](https://www.toegankelijkheidsverklaring.nl/register/29132).
- We draaien regelmatig loep, het toegankelijkheidsonderzoek van NLDD, over de hele app.
- Bij wijzigingen aan de interface toetsen we met het toetsenbord, een schermlezer en een automatische scan (axe), in licht en donker thema.
