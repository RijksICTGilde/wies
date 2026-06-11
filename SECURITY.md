# Beveiligingsbeleid

Wies is een interne applicatie van de Rijksoverheid en valt onder de
[Baseline Informatiebeveiliging Overheid (BIO2)](https://www.bio-overheid.nl/).

## Een kwetsbaarheid melden

Heb je een (vermoedelijke) kwetsbaarheid of een ander beveiligingsprobleem
gevonden in Wies?

- Meld het vertrouwelijk via GitHub:
  [Report a vulnerability](https://github.com/RijksICTGilde/wies/security/advisories/new)
  (private vulnerability reporting — alleen het team ziet je melding).
- Of mail het team: [wies-odi@rijksoverheid.nl](mailto:wies-odi@rijksoverheid.nl)
- Of meld het via [Coordinated Vulnerability Disclosure van het NCSC](https://www.ncsc.nl/contact/kwetsbaarheid-melden)
  als je het team niet kunt bereiken.

Meld ook vermoedens, liever een loos alarm dan een gemiste kwetsbaarheid.
Maak een bevinding niet openbaar voordat het team heeft kunnen reageren.

## Wat je van ons mag verwachten

- Je krijgt een reactie van het team op iedere melding.
- Kwetsbaarheden waarbij de kans op misbruik en de verwachte schade beide hoog
  zijn, mitigeren we zo snel mogelijk en uiterlijk binnen één week (BIO2 8.08).
- We houden je op de hoogte van de afhandeling van je melding.

## Hoe we beveiliging geregeld hebben

- **Toegang** — inloggen kan uitsluitend via SSO-Rijk (OIDC); de applicatie kent
  geen wachtwoorden en geen groepsaccounts.
- **Dependencies** — Dependabot bewaakt wekelijks de Python-, npm- en GitHub
  Actions-dependencies ([`.github/dependabot.yml`](.github/dependabot.yml)).
- **Geheimen** — GitHub secret scanning met push protection blokkeert het pushen
  van credentials naar deze repository.
- **Wijzigingen** — iedere wijziging gaat via een pull request en draait
  automatisch de testsuite ([`.github/workflows/test.yml`](.github/workflows/test.yml));
  getest wordt op lokale en previewomgevingen, nooit in productie.
- **Geen externe runtime-afhankelijkheden** — JavaScript is gevendored in plaats
  van via een CDN geladen, zodat de CSP geen externe bronnen hoeft toe te staan.

De volledige BIO-verantwoording (per control en maatregel) is intern belegd bij
ODI en wordt hier niet herhaald.

## Versies

Alleen de laatst uitgerolde versie (`main` → productie) wordt ondersteund met
beveiligingsfixes.
