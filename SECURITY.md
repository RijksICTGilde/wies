<!--
  Source of truth for the security policy, also shown in Wies at /beveiliging/.
  After editing this file, regenerate the in-product page:
      uv run python manage.py generate_docs_html
-->

# Beveiligingsbeleid

Wies is een intern hulpmiddel van ODI, onderdeel van de Rijksoverheid. Voor Wies gelden de
regels van de [Baseline Informatiebeveiliging Overheid (BIO2)](https://www.bio-overheid.nl/),
de beveiligingsnorm voor de hele overheid.

## Een kwetsbaarheid melden

Zie je iets in Wies dat niet veilig lijkt? Bijvoorbeeld gegevens die je niet zou mogen zien,
of een manier om iets te doen dat niet mag? Dat noemen we een kwetsbaarheid. Meld het bij ons:

- Stuur een e-mail naar [wies-odi@rijksoverheid.nl](mailto:wies-odi@rijksoverheid.nl).
- Heb je een GitHub-account? Dan kun je het ook
  [vertrouwelijk melden op GitHub](https://github.com/RijksICTGilde/wies/security/advisories/new)
  (Engelstalig). Alleen het Wies-team ziet die melding.
- Krijg je geen reactie van ons? Meld het dan bij het
  [Nationaal Cyber Security Centrum (NCSC)](https://www.ncsc.nl/contact/kwetsbaarheid-melden).

Twijfel je? Meld het toch. Liever een loos alarm dan een gemiste kwetsbaarheid.
Deel wat je gevonden hebt niet met anderen voordat we hebben gereageerd.

## Wat je van ons mag verwachten

- Je krijgt altijd een reactie op je melding.
- Is de kans op misbruik groot en de mogelijke schade ook? Dan nemen we zo snel mogelijk
  maatregelen, uiterlijk binnen een week. Dat is de termijn uit BIO2 (maatregel 8.08).
- We laten je weten wat we met je melding doen.

## Hoe we Wies beveiligen

- **Toegang** — Je logt alleen in via SSO Rijk, de centrale inlogdienst van de Rijksoverheid.
  Wies bewaart geen wachtwoorden en heeft geen gedeelde accounts.
- **Software van anderen** — Wies gebruikt onderdelen die anderen hebben gemaakt. Elke week
  controleren we automatisch of daar een nieuwe, veiligere versie van is.
- **Automatische controles** — Bij elke wijziging en elke week controleren we de code en de
  omgeving waarin Wies draait op bekende kwetsbaarheden. Ernstige bevindingen pakken we op.
- **Wachtwoorden en sleutels** — Die horen niet in de code. GitHub controleert dat automatisch
  en houdt ze tegen.
- **Wijzigingen** — Elke wijziging wordt eerst nagekeken en automatisch getest voordat die in
  Wies komt. We testen in aparte testomgevingen, nooit in de Wies die je gebruikt.
- **Geen code van buiten** — Wies laadt alle code van de eigen server, niets van andere websites.

## Voor ontwikkelaars

De technische invulling van de maatregelen hierboven:

- Inloggen via SSO-Rijk met OIDC; geen lokale wachtwoorden, geen groepsaccounts.
- Dependabot bewaakt wekelijks de Python-, npm- en GitHub Actions-dependencies
  ([`.github/dependabot.yml`](.github/dependabot.yml)).
- Trivy scant bij iedere pull request, bij iedere push naar `main` en dagelijks de broncode
  (dependencies, geheimen, configuratie) en de container-image (OS-pakketten). Bevindingen met
  ernst hoog of kritiek waarvoor een fix beschikbaar is, komen in de Security-tab van de
  repository ([`.github/workflows/security-scan.yml`](.github/workflows/security-scan.yml)).
- GitHub secret scanning met push protection staat aan op de repository.
- Iedere wijziging gaat via een pull request en draait automatisch de testsuite
  ([`.github/workflows/test.yml`](.github/workflows/test.yml)).
- JavaScript is gevendored, niet via een CDN; de CSP staat geen externe bronnen toe.
