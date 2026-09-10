# Toegankelijkheidsonderzoek

Onderbouwing bij toegankelijkheidsverklaring **29132**.

## Het rapport

[`rapport-wcag22-2026-08.md`](rapport-wcag22-2026-08.md) — WCAG 2.2 niveau A en
AA, versie 1.1. Volledig onderzoek op `main` @ `d072cf3b`, 19 augustus 2026;
hertest op `main` @ `f4595a8`, 9 september 2026. Opbouw A tot en met D zoals
DigiToegankelijk die voorschrijft.

**Uitkomst na de hertest: 32 van de 55 succescriteria voldoen.** Eén afwijking,
niveau A:

| Succescriterium        | Bevinding                                       | Waar                              |
| ---------------------- | ----------------------------------------------- | --------------------------------- |
| 1.3.1 Info en relaties | Koppenstructuur slaat een niveau over (H1 → H3) | `parts/filter_sidebar.html:42,81` |

Bevinding 2 (2.4.3, focus na een htmx-swap) is opgelost in PR #638 en bij de
hertest bevestigd in Chromium, Edge en Firefox.

Veertien succescriteria konden niet worden vastgesteld: daarvoor is toetsing met
een schermlezer nodig. [`toetsronde.html`](toetsronde.html) loopt die veertien af,
met per criterium de stappen en invulvelden per schermlezer-combinatie. Open je
het bestand lokaal, dan bewaart het alleen in je eigen browser; de gepubliceerde
versie als Claude-artifact heeft gedeelde opslag.

> **Dit rapport is nog niet volledig.** Het is uitgevoerd door het eigen team,
> zonder hulpsoftware en zonder gebruikers. Voor status A of B van de verklaring
> moeten alle 55 criteria beoordeeld zijn; onafhankelijkheid eist DigiToegankelijk
> niet, wel dat het rapport zegt wie het deed.

## De metingen herhalen

De scripts in [`scripts/`](scripts/) meten wat in het rapport staat. Ze draaien
tegen een lokaal draaiende instantie.

```bash
just up                                    # app op http://localhost:8080

pip install playwright && playwright install chromium
curl -sL https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js -o scripts/axe.min.js

cd scripts && python3 scan.py              # axe-core over 11 pagina's
```

| Script                 | Meet                                                                                               |
| ---------------------- | -------------------------------------------------------------------------------------------------- |
| `scan.py`              | axe-core over de elf pagina's uit de steekproef                                                    |
| `contrast2.py`         | 1.4.3 contrast, inclusief shadow DOM, met canvas-kleurconversie                                    |
| `manual.py`            | koppenstructuur, taal, paginatitel, reflow, tabvolgorde                                            |
| `names.py`             | toegankelijke namen via de accessibility tree                                                      |
| `focus.py`             | 2.4.1 skiplink en 2.4.7 focuszichtbaarheid                                                         |
| `focus_swap.py`        | 2.4.3 focus na een htmx-swap (bevinding 2) — vereist een sessie                                    |
| `extra.py`             | doelgrootte, tekstafstand, weergavestand, linkteksten                                              |
| `extra2.py`            | niet-tekstueel contrast, toetsenbordval, live regions                                              |
| `wcag22.py`            | de nieuwe 2.2-criteria: 2.4.11, 3.2.6, 3.3.7, 3.3.8                                                |
| `parsen.py`            | dubbele ID's (4.1.1, vervallen in 2.2)                                                             |
| `hertest_browsers.py`  | hertest: koppen, tabvolgorde, JS-fouten in Chromium, Edge en Firefox — vereist een sessie          |
| `hertest_focusring.py` | hertest: focusring als pixelverschil (niet bruikbaar in Firefox, zie rapport) — vereist een sessie |
| `hertest_swap.py`      | hertest: focus na een htmx-swap in drie browsers — vereist een sessie                              |

`focus_swap.py` is de uitzondering: de panelen zitten achter OIDC, dus het heeft
een sessie nodig. Maak er een aan en geef de sleutel mee:

```bash
docker compose run --rm django python manage.py shell -c "
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
u = get_user_model().objects.filter(is_active=True).first()
s = SessionStore()
s['_auth_user_id'] = str(u.pk)
s['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
s['_auth_user_hash'] = u.get_session_auth_hash()
s.create()
print(s.session_key)
"

python3 focus_swap.py <sessionid>
```

## Waarom er eigen scripts zijn

Wies bestaat voor ongeveer 78% uit elementen binnen een shadow root (2.310 van de
2.948). Standaard toetsingsgereedschap kijkt daar niet in. Dat is aangetoond door
een contrastfout van 1,9:1 te injecteren: in het gewone document vond axe-core
hem, in een shadow root niet.

"0 overtredingen" van axe-core dekt hier dus maar een vijfde van de interface. De
scripts hierboven doorlopen shadow roots wel, of gebruiken de accessibility tree
van de browser.

## Waarschuwing bij eigen metingen

Negen metingen leverden tijdens dit onderzoek een plausibel ogende maar onjuiste
uitkomst op; de volledige lijst staat in het rapport onder beperking 6. De eerste
vijf:

| Onjuist                        | Werkelijk      | Oorzaak                                         |
| ------------------------------ | -------------- | ----------------------------------------------- |
| 910 contrastfouten             | 0              | `oklch()` als RGB gelezen                       |
| 8/10 tabstops zonder focusring | alle zichtbaar | ring zit in de shadow root                      |
| 192 elementen zonder naam      | 0              | naam komt uit geslotte inhoud                   |
| sheet sluit focus niet in      | sluit wel in   | detectie kruiste de shadow-grens niet           |
| 16 tabstops met bedekte focus  | geen           | `elementFromPoint` gaf het omhullende component |

Toets elke uitkomst met een tweede methode, visueel, of via de accessibility tree
voordat je hem opschrijft.

## Vervolg

1. Bevinding 1 oplossen (een kleine wijziging in één bestand)
2. Issue #600 sluiten; bevinding 2 is opgelost
3. De toetsronde met schermlezer doen voor de veertien openstaande criteria
4. Het rapport openbaar publiceren als onderbouwing van de verklaring
