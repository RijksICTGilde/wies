# Toegankelijkheidsonderzoek

Onderbouwing bij toegankelijkheidsverklaring **29132**.

## Het rapport

[`rapport-wcag22-2026-08.md`](rapport-wcag22-2026-08.md) — WCAG 2.2 niveau A en
AA, uitgevoerd op `main` @ `d072cf3b`, 19 augustus 2026.

**Uitkomst: 31 van de 55 succescriteria voldoen.** Twee afwijkingen, beide niveau
A:

| Succescriterium        | Bevinding                                       | Waar                              |
| ---------------------- | ----------------------------------------------- | --------------------------------- |
| 1.3.1 Info en relaties | Koppenstructuur slaat een niveau over (H1 → H3) | `parts/filter_sidebar.html:42,81` |
| 2.4.3 Focus volgorde   | Focus valt terug op `<body>` na een htmx-swap   | Issue #600                        |

Veertien succescriteria konden niet worden vastgesteld: daarvoor is toetsing met
een schermlezer nodig.

> **Dit rapport is geen vervanging van een formeel onderzoek.** Het is uitgevoerd
> door het eigen team, zonder hulpsoftware en zonder gebruikers. Voor status A of
> B van de verklaring is een onafhankelijk WCAG-EM-onderzoek vereist.

## De metingen herhalen

De scripts in [`scripts/`](scripts/) meten wat in het rapport staat. Ze draaien
tegen een lokaal draaiende instantie.

```bash
just up                                    # app op http://localhost:8080

pip install playwright && playwright install chromium
curl -sL https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js -o scripts/axe.min.js

cd scripts && python3 scan.py              # axe-core over 11 pagina's
```

| Script         | Meet                                                            |
| -------------- | --------------------------------------------------------------- |
| `scan.py`      | axe-core over de elf pagina's uit de steekproef                 |
| `contrast2.py` | 1.4.3 contrast, inclusief shadow DOM, met canvas-kleurconversie |
| `manual.py`    | koppenstructuur, taal, paginatitel, reflow, tabvolgorde         |
| `names.py`     | toegankelijke namen via de accessibility tree                   |
| `focus.py`     | 2.4.1 skiplink en 2.4.7 focuszichtbaarheid                      |
| `extra.py`     | doelgrootte, tekstafstand, weergavestand, linkteksten           |
| `extra2.py`    | niet-tekstueel contrast, toetsenbordval, live regions           |
| `wcag22.py`    | de nieuwe 2.2-criteria: 2.4.11, 3.2.6, 3.3.7, 3.3.8             |
| `parsen.py`    | dubbele ID's (4.1.1, vervallen in 2.2)                          |

## Waarom er eigen scripts zijn

Wies bestaat voor ongeveer 78% uit elementen binnen een shadow root (2.310 van de
2.948). Standaard toetsingsgereedschap kijkt daar niet in. Dat is aangetoond door
een contrastfout van 1,9:1 te injecteren: in het gewone document vond axe-core
hem, in een shadow root niet.

"0 overtredingen" van axe-core dekt hier dus maar een vijfde van de interface. De
scripts hierboven doorlopen shadow roots wel, of gebruiken de accessibility tree
van de browser.

## Waarschuwing bij eigen metingen

Vijf metingen leverden tijdens dit onderzoek een plausibel ogende maar onjuiste
uitkomst op:

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

1. De twee bevindingen oplossen (1.3.1 is een kleine wijziging in één bestand)
2. Issue #600 bijwerken — het skiplink-deel is achterhaald, die bestaat wel
3. Schermlezertest voor de veertien openstaande criteria
4. Onafhankelijk WCAG-EM-onderzoek voor de verklaring
