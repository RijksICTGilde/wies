# NLDD in een server-gerenderde app

De componenten van `@nldd/design-system` zijn Lit web components met een
shadow root. Wies rendert HTML op de server en swapt fragmenten in met htmx.
Op die grens gaat het mis op manieren die de officiële `nldd`-skill niet
dekt: die is geschreven voor client-side apps en zet server-side rendering
expliciet buiten scope.

Vier valkuilen, met dezelfde oorzaak: **een swap trapt de levenscyclus van een
component niet af zoals een paginalading dat doet.**

## 1. `show()` faalt stil na een swap

Op een sheet, modal of dialog die net is ingeswapt doet `show()` niets: Lit
heeft de shadow-`<dialog>` nog niet gerenderd. Er komt geen foutmelding — het
venster gaat gewoon niet open.

Wacht op `updateComplete`:

```js
await el.updateComplete;
el.show();
```

Zie `wies/core/static/js/dialog.js`, dat sheets met `data-auto-show` na een swap opent.

## 2. `href` én `hx-get` op hetzelfde element

Componenten die intern een `<a>` renderen (`nldd-list-item`, `nldd-card`,
`nldd-menu-item`) laten die anchor winnen: de browser navigeert weg en gooit
de htmx-respons weg. Kies er één, of onderschep de default click.

`wies/core/static/js/hx_link_guard.js` doet dat laatste voor elementen die beide dragen.

## 3. POST vanuit een component in een shadow root

Uitloggen en verwijderen horen POST te zijn, maar een menu-item in een shadow
root kun je niet in een `<form>` wikkelen. Doe de POST vanuit JS met het
CSRF-token uit de markup — zie `wies/core/static/js/menu_nav.js`.

## 4. Formuliervalidatie koppelt zichzelf niet

De foutweergave werkt op `invalid` + `error-message="<id>"`. Django-widgets
die we zelf renderen zetten die attributen niet, dus de melding krijgt hoogte
0 en is onzichtbaar — ook voor een screenreader. Elke custom widget rendert ze
expliciet mee.

## Eigen CSS op een `nldd-*` element

Mag, maar alleen met een comment erboven die uitlegt **waarom het component
het zelf niet kan** (render-timing, swap-grens, shadow-DOM). Lukt die zin
niet, dan is het smaak-styling en hoort de regel weg. Stuur bij voorkeur via
attributen, slots en `--components-*`-tokens.

Zo is `wies/core/static/css/app.css` opgezet: de regels die een `nldd-*`
element targeten staan onder een comment dat hun bestaan verantwoordt.

## Namen niet raden

Een onbekende icoonnaam rendert **stil niets**; een onbekende `variant` valt
terug op de default. De naam die logisch klinkt is vaak net niet de echte
(`edit` → `pencil`, `lock` → `lock-closed`, `tertiary` →
`neutral-transparent`, `warning-subtle` → `critical-tinted`).

Zoek op in `skills/nldd/reference.md` van de `nldd`-skill, of in de broncode
van `MinBZK/storybook` (`src/components/<groep>/<naam>/`). Niet gissen in de
geminificeerde bundle.

## CSS-tokens: test in dark mode

Een niet-bestaand token is geldige CSS en valt terug op de fallback in
`var(--token, #fff)`. In de lichte modus ziet dat er goed uit; het breekt pas
in dark mode. Controleer elke stylingwijziging in beide modi.
