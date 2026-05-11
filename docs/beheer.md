# Beheerplan Wies

Status: concept

E-mail: [wies-odi@rijksoverheid.nl](mailto:wies-odi@rijksoverheid.nl)
Mattermost: [https://digilab.overheid.nl/chat/odi/channels/wies](https://digilab.overheid.nl/chat/odi/channels/wies)
Code: [https://github.com/RijksICTGilde/wies](https://github.com/RijksICTGilde/wies)

## 1\. Doel & scope

Wies is een interne webapplicatie voor medewerkers bij ODI om inzicht te krijgen in wie waar zit en aan welke opdrachten wordt gewerkt, ter bevordering van kennisdeling. Dit beheerplan beschrijft hoe Wies stabiel, veilig en efficiënt wordt beheerd.

## 2\. Rollen & verantwoordelijkheden

| Rol                   | Naam / team                                        | Verantwoordelijkheden                                |
| :-------------------- | :------------------------------------------------- | :--------------------------------------------------- |
| Adviseur              | Robbert Bos                                        | Prioriteiten, productrichting, stakeholderafstemming |
| Product Owner         | Matthijs Beekman                                   | Prioriteiten, productrichting, stakeholderafstemming |
| Technisch beheerder   | Robbert Uittenbroek Matthijs Beekman               | Hosting, deployment, updates, monitoring             |
| Functioneel beheerder | Robbert Uittenbroek Ruben Rouwhof Matthijs Beekman | Gebruikersbeheer, feedback, testen                   |
| Ontwikkelteam         | Robbert Uittenbroek Ruben Rouwhof Matthijs Beekman | Ontwikkeling, bugfixes, releases                     |
| Security/Privacy      | CISO & CPO ODIEiric Vellinga                       | Beleid, AVG compliance, advisering                   |

## 3\. Hosting & infrastructuur

- Locatie: ODC-Noord, overheidsdatacenter.
- Platform: tenant in bestaand ODCN Kubernetes omgeving, beheerd door ODCN
- Omgevingen: aparte test- en productieomgevingen, volledig geïsoleerd van elkaar
- Back-ups: van specifieke data opgeslagen in Wies wordt dagelijks een back-up gemaakt.
- Monitoring & logging: logging reeds aanwezig; monitoring wordt geïntroduceerd.
- Beschikbaarheid: tijdens kantooruren is niet beschikbaar zijn toegestaan voor de maximale duur van 5 werkdagen per incident; buiten kantooruren is beschikbaarheid niet gegarandeerd.

## 4\. Beveiliging & continuïteit

- Authenticatie: Rijks SSO, alleen expliciet toegevoegde ODI-gebruikers; beheerd via speciale rol (“Beheerder”). Elke wijziging aan de gebruikerslijst wordt gelogd en kan later geïnspecteerd worden.
- Onboarding/offboarding: voor elk merk binnen ODI wordt er 1 beheerder aangesteld. Deze beheerder kan bij indiensttreding/uitdiensttreding gebruikers toevoegen/verwijderen.
- Data & privacy: er wordt een zeer beperkte set gegevens opgeslagen per persoon, waarbij slechts de huidige opdrachten zichtbaar zijn voor collega’s. Een Pre-scan DPIA heeft aangetoond dat er geen DPIA nodig is.
- Updates: per sprint en daarnaast direct na beveiligingspatches.
- Testen: automatische tests voor bestaande en nieuwe functionaliteiten.
- Afhankelijkheid van specifieke personen: minimaal 2 ontwikkelaars die onafhankelijk zorg kunnen dragen voor de applicatie
- Code wijzigingen worden door een andere ontwikkelaar bekeken voordat deze goedgekeurd worden (4-ogen principe).
- Incident respons: binnen één werkdag; proces wordt nader uitgewerkt.

## 5\. Operationeel beheer & rapportage

- Incidenttracking: GitHub Issues.
- Gebruikersfeedback: GitHub Issues.
- Communicatie: “wies” kanaal op Mattermost voor meldingen en updates. Daarnaast bereikbaar op [wies-odi@rijksoverheid.nl](mailto:wies-odi@rijksoverheid.nl).
- Statusrapportage: elke 4 maanden aan stakeholders: stabiliteit, gebruik en verbeterpunten
- KPI’s: aantal incidenten, aantal inlogacties totaal, aantal inlogacties afgelopen 90d, aantal gebruikers die een keer hebben ingelogd

## 6\. Verbetercyclus & continuïteit

- 4-maandelijkse reviews voor stabiliteit, performance en feedback.
- Backlog voor technische en functionele verbeteringen.
- Alle code en data zijn overdraagbaar; documentatie houden we actueel.
- Pre-scan DPIA en eventueel DPIA worden tussendoor, afhankelijk van hetgeen wordt ontwikkeld, geactualiseerd.
