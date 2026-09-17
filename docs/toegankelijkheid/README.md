# Toegankelijkheidsonderzoek

Onderbouwing bij toegankelijkheidsverklaring **29132**.

## Het rapport

[`rapport-wcag22-2026-08.md`](rapport-wcag22-2026-08.md) — WCAG 2.2 niveau A en
AA, versie 2.0. Onderzoek van 19 augustus tot en met 17 september 2026 op
`main` (laatste stand @ `58bb0f0`): geautomatiseerd, instrumenteel in drie
browsers en met de schermlezer VoiceOver. Opbouw A tot en met D zoals
DigiToegankelijk die voorschrijft.

**Uitkomst: alle 55 succescriteria beoordeeld, 41 voldoen.** Zes afwijkingen,
in vijf bevindingen:

| #   | Succescriterium                       | Bevinding                                                        |
| --- | ------------------------------------- | ---------------------------------------------------------------- |
| 1   | 1.3.1 Info en relaties (A)            | Koppenstructuur slaat een niveau over (H1 → H3)                  |
| 2   | 1.3.5 Inputdoel identificeren (AA)    | Naamvelden op Mijn profiel zonder `autocomplete`                 |
| 3   | 3.2.2 Bij input (A)                   | Focus springt naar het begin van de pagina na een filterwissel   |
| 4   | 3.3.1 en 3.3.3 Fouten (A, AA)         | Foutmelding wordt niet bij het veld voorgelezen (shadow-grens)   |
| 5   | 4.1.3 Statusberichten (AA)            | Aantal resultaten en bevestigingen worden niet aangekondigd      |

Het herstel van alle vijf is voorbereid in branch `a11y-screenreader-fixes` en
met VoiceOver gemeten; het staat nog niet op `main`. Na samenvoegen en één
meting op `main` zijn er geen afwijkingen meer: 47 voldoen, 8 niet van toepassing.

De schermlezertoets is gedaan met [`toetsronde.html`](toetsronde.html): per
criterium de stappen, de toetsen en invulvelden per schermlezer-combinatie.
VoiceOver + Chrome op macOS bepaalt het oordeel; Safari en NVDA staan als
optionele kolommen klaar. Open je het bestand lokaal, dan bewaart het alleen in
je eigen browser; de gepubliceerde versie als Claude-artifact heeft gedeelde
opslag, waarin de uitkomsten van 17 september staan.

> **Wat dit rapport wel en niet is.** Uitgevoerd door het eigen team, met één
> schermlezer en zonder gebruikers. Alle 55 criteria zijn beoordeeld, dus het kan
> de verklaring onderbouwen: status B nu, status A zodra het herstel op `main`
> staat en daar is gemeten. Onafhankelijkheid eist DigiToegankelijk niet, wel dat
> het rapport zegt wie het deed.

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
| `hertest_browsers.py`  | koppen, tabvolgorde, JS-fouten in Chromium, Edge en Firefox — vereist een sessie          |
| `hertest_focusring.py` | focusring als pixelverschil (niet bruikbaar in Firefox, zie rapport) — vereist een sessie |
| `hertest_swap.py`      | focus na een htmx-swap in drie browsers — vereist een sessie                              |

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

1. Branch `a11y-screenreader-fixes` samenvoegen en op `main` opnieuw meten
2. De toetsronde herhalen met NVDA op Windows (optionele kolommen)
3. Twee punten melden bij NLDD: `aria-describedby` over de shadow-grens en "1 of 1" in de weergavekeuze
4. Issue #600 sluiten; skiplink en focus na een swap zijn in orde
5. Het rapport openbaar publiceren als onderbouwing van de verklaring, status B
