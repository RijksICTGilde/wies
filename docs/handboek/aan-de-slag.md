<!--
  Source of truth for this handbook page, also shown in Wies at /handboek/.
  After editing, regenerate the in-product pages:
      uv run python manage.py generate_docs_html
-->

# Aan de slag

Nieuw in het team, of gewoon benieuwd hoe Wies onder de motorkap werkt? Dan zit je hier goed. Lees de drie techniekpagina's op volgorde: elke pagina bouwt voort op de vorige.

- Deze pagina, **Aan de slag**: wat Wies is en hoe je het lokaal draait.
- [De code](de-code.md): hoe de code in elkaar zit.
- [Samenwerken](samenwerken.md) bevat de spelregels: testen, valkuilen en hoe we werken.
- Sluit af met de [oefenopdrachten](samenwerken.md#oefenopdrachten): doe ze echt; alleen lezen blijft niet hangen.

Na afloop kun je zelf een bewerkbaar veld toevoegen, een modelwijziging met migratie doorvoeren en een PR openen die in één keer door de review komt.

Klopt er iets niet meer? De code is de bron van waarheid. Pas dit handboek aan in dezelfde PR als de code.

## Wies in het kort

Wies laat zien welke collega op welke opdracht zit, in welke rol en wanneer. Het is een interne tool van ODI (Rijksorganisatie voor Ontwikkeling, Digitalisering en Innovatie): collega's zoeken elkaar op, business managers beheren hun opdrachten en de bezetting, en gebruikersbeheerders beheren accounts en labels.

Een deel van de opdrachten wordt in Wies zelf aangemaakt (`source="wies"`). Een ander deel komt via een synchronisatie uit OTYS, het systeem van de business managers voor het matchen consultants aan opdrachten(`wies/core/services/otys.py`, `sync.py`). Geïmporteerde opdrachten zijn in Wies alleen-lezen, ook voor business managers.

Wies kent vier rollen: Consultant, Business Manager, Gebruikersbeheerder en Applicatiebeheerder. Wat elke rol mag, staat in [Rollen en rechten](de-code.md#rollen-en-rechten).

### Begrippen

De code is Engels, de app Nederlands, en de vertaling is niet altijd letterlijk.

| In de app                        | In de code                                   | Wat het is                                                                                         |
| -------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| opdracht                         | `Assignment`                                 | De klus voor een opdrachtgever, met een periode en een business manager (`owner`)                  |
| rol                              | `Service`                                    | Het werk dat een opdracht nodig heeft, met uren per week en status `CONCEPT`, `OPEN` of `GESLOTEN` |
| aanvraag                         | `Service` met status `OPEN` zonder plaatsing | Een rol waar nog niemand op staat                                                                  |
| plaatsing (in een team: teamlid) | `Placement`                                  | Een collega op een rol                                                                             |
| collega                          | `Colleague`                                  | De persoon; kan gekoppeld zijn aan een `User`                                                      |
| gebruiker                        | `rijksauth.User`                             | Het account, inlog via e-mail en OIDC; alleen zo genoemd onder Beheer                              |
| opdrachtgever                    | `OrganizationUnit`                           | Een overheidsorganisatie, in een boomstructuur (`parent`)                                          |
| merk                             | `Suborganization`                            | De suborganisatie waaronder een collega werkt                                                      |
| label in een categorie           | `Label`, `LabelCategory`                     | Kenmerken op een collega, zoals Expertise                                                          |
| contractperiode                  | `ContractPeriod`                             | Uren per week van een collega over een periode                                                     |

De ruggengraat van het domein is één keten: **opdracht → rol → plaatsing → collega**. Bijna elk scherm is een andere blik op die keten.

## Wies op je eigen laptop

Alles draait in Docker, dus op je laptop heb je alleen wat gereedschap nodig. Na deze stappen draait Wies op http://localhost:8080, gevuld met nepdata.

**Installeer eerst:** [Docker](https://www.docker.com/), [just](https://github.com/casey/just), [uv](https://docs.astral.sh/uv/), [pre-commit](https://pre-commit.com/) en Node.js 22 of hoger (alleen voor de JavaScript-tests).

1. Clone de repo en draai `just setup`. Dat installeert de Python-pakketten, maakt `.env` aan uit `.env.local.example`, bouwt de containers, migreert de database en laadt een kleine set dummydata (`load_dummy_data --profile base`, werkt offline).
2. Open `.env` en zet jezelf erin: `INITIAL_USER_FIRSTNAME`, `INITIAL_USER_LASTNAME`, `INITIAL_USER_EMAIL` en je e-mailadres in `STAFF_EMAILS`.
3. Geen Keycloak-gegevens of geen VPN? Zet `SKIP_OIDC=true`. Dan logt de `AutoLoginMiddleware` je automatisch in, zonder SSO.
4. Draai `just setup` opnieuw zodat je eerste gebruiker wordt aangemaakt, en start daarna met `just up`.
5. Installeer de git-hooks met `just pre-commit-install`.

Wil je de app voelen met realistische aantallen? `just load-full-data` synchroniseert de echte organisatiestructuur en genereert een grote dataset. Daar heb je netwerk voor nodig.

### Handige commando's

| Commando                    | Wat het doet                                                                  |
| --------------------------- | ----------------------------------------------------------------------------- |
| `just up` / `just down`     | Containers starten en stoppen (postgres, minio, django, db_worker)            |
| `just test`                 | Alle tests: Django (pytest in Docker) en JavaScript (`node --test`)           |
| `just test django`          | Alleen de Django-tests                                                        |
| `just manage <cmd>`         | Elk `manage.py`-commando in de container, bv. `just manage makemigrations`    |
| `just lint` / `just format` | Ruff controleren / automatisch repareren en formatteren                       |
| `just pre-commit`           | Alle pre-commit-hooks over de hele repo                                       |
| `just vendor`               | NLDD en htmx uit `package-lock.json` naar `wies/core/static/vendor/` kopiëren |

### Wat er allemaal draait

| Service     | Poort                      | Rol                                                                                                     |
| ----------- | -------------------------- | ------------------------------------------------------------------------------------------------------- |
| `django`    | 8080                       | De app zelf, met je checkout als volume gemount: wijzigingen zijn direct live                           |
| `postgres`  | 5432                       | De database                                                                                             |
| `minio`     | 9000 (API), 9001 (console) | S3-compatibele objectopslag voor lokaal ontwikkelen; in productie levert ZAD de objectopslag            |
| `db_worker` | geen                       | Achtergrondtaken (organisatiesync, startpagina publiceren); leest de tabel Task en gebruikt .env.worker |
