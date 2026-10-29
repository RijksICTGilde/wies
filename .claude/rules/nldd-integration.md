# NLDD in een server-gerenderde app

De componenten van `@nldd/design-system` zijn Lit web components met een
shadow root. Wies rendert HTML op de server en swapt fragmenten in met htmx.
Op die grens gaat het mis op manieren die de officiële NLDD-skills
(plugin `nldd-design-system`) niet dekken: die laten server-side rendering
over aan de algemene web-componentenpraktijk.

Drie valkuilen, met dezelfde oorzaak: **een swap trapt de levenscyclus van een
component niet af zoals een paginalading dat doet.**

## 1. `href` én `hx-get` op hetzelfde element

Componenten die intern een `<a>` renderen (`nldd-list-item`, `nldd-card`,
`nldd-menu-item`) laten die anchor winnen: de browser navigeert weg en gooit
de htmx-respons weg. Kies er één, of onderschep de default click.

`wies/core/static/js/hx_link_guard.js` doet dat laatste voor elementen die beide dragen.

## 2. POST vanuit een component in een shadow root

Uitloggen en verwijderen horen POST te zijn, maar een menu-item in een shadow
root kun je niet in een `<form>` wikkelen. Doe de POST vanuit JS met het
CSRF-token uit de markup — zie `wies/core/static/js/menu_nav.js`.

## 3. Formuliervalidatie koppelt zichzelf niet

De foutweergave is een `nldd-validation-list` met `nldd-validation-item`s in
de `nldd-form-field`; een item zonder regel is pas zichtbaar als het veld
`invalid` heeft en het item-id in `unmet` noemt. Django-widgets die we zelf
renderen zetten die attributen niet, dus de melding blijft onzichtbaar, ook
voor een screenreader. Elke custom widget rendert ze expliciet mee
(`wire_field_errors`). Een widget dat geen invoerveld is (de opdrachtgever-
kiezer) geeft de lijst een `for` naar zijn knop. Elk `<form>` draagt
`novalidate`: sinds 0.8.88 melden de velden `required` aan de browser, die de
inzending dan zonder tekst tegenhoudt; in Wies oordeelt de server.

## `show()` mag direct

Een `show()` vóór de eerste render zet het component in de wachtrij; wachten op
`updateComplete` is niet nodig. Een script dat vóór de bundel laadt
(`extra_head` in `base.html`) wacht wel op `customElements.whenDefined()`:
daar bestaat `show()` nog niet.

## Eigen CSS op een `nldd-*` element

Mag, maar alleen met een comment erboven die uitlegt **waarom het component
het zelf niet kan** (render-timing, swap-grens, shadow-DOM). Lukt die zin
niet, dan is het smaak-styling en hoort de regel weg. Stuur bij voorkeur via
attributen, slots en `--components-*`-tokens.

Zo is `wies/core/static/css/app.css` opgezet: de regels die een `nldd-*`
element targeten staan onder een comment dat hun bestaan verantwoordt.

## Namen niet raden

Een onbekende icoonnaam rendert **stil niets**; een onbekende `appearance` of
`variant` valt terug op de default, net als een attribuut dat een upgrade
hernoemde (`variant` → `appearance` op `nldd-button`). Dat geldt ook voor de
private `--_`-variabelen: 0.9.0 gaf ze een componentprefix
(`--_background-color` → `--_card-background-color`). De naam die logisch
klinkt is vaak net niet de echte (`edit` → `pencil`, `lock` → `lock-closed`,
`tertiary` → `neutral-transparent`, `warning-subtle` → `critical-tinted`).

Zoek op met de `nldd-design`-skill (`reference.md`), of in de broncode van
`NederlandseDigitaleDienst/design-system` (`src/components/<groep>/<naam>/`).
Niet gissen in de geminificeerde bundle.

## CSS-tokens: test in dark mode

Een niet-bestaand token is geldige CSS en valt terug op de fallback in
`var(--token, #fff)`. In de lichte modus ziet dat er goed uit; het breekt pas
in dark mode. Controleer elke stylingwijziging in beide modi.
