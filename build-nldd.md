# Beoordeling: NLDD als gedistribueerde bundel — werkt dit voor Wies?

## Context

De maker van het NLDD design system overweegt het bundelen zelf te doen en een
kant-en-klare bundel te distribueren, zodat consumenten (zoals Wies) niet meer
zelf hoeven te builden. Zijn advies na meten: lever de bundel als **ESM met
code-splitting + een autoloader (MutationObserver, à la Shoelace)**, minified
als standaard, met een exports-entry, CSS/fonts zoals ze er al zijn, en een
unpkg/jsdelivr-veld. Voor Wies zou `scripts/build-nldd.mjs` + esbuild kunnen
vervallen; het build-script wordt een `cp -R` van ~30 chunks en `<script src>`
wordt `<script type="module" src>`.

De vraag: werkt dit inderdaad voor ons?

## Korte antwoord

**Ja op de kern, maar niet zonder één blokkerende aanpassing.** Het bundelwerk
hoort inderdaad bij het design system. De ESM + code-splitting + autoloader-opzet
past goed bij Wies — _mits_ Wies's static-pipeline (WhiteNoise
`ManifestStaticFilesStorage`) de code-split chunks niet stukmaakt. Dat is het
enige echte risico en het is oplosbaar.

**Wies gaat in de nabije toekomst rich text editing gebruiken.** Dat versterkt
zijn code-splitting-argument juist: de CodeMirror/editor-stack hangt dan niet meer
aan één zelden-bezochte error-pagina, maar aan een centrale feature op reguliere
pagina's. "Editors lui laden maar wél beschikbaar" is precies waar de autoloader
voor bedoeld is. De autoloader/code-splitting-aanpak is daarmee de betere keuze
voor Wies (een simpele core+full bundel zou ook kunnen, maar geeft minder fijne
controle over wanneer de editor laadt).

## Wat de huidige situatie is (feitelijk, uit de code)

- **Build:** `scripts/build-nldd.mjs` bundelt `@nldd/design-system`
  (`^0.8.77`) met esbuild naar één **IIFE** `ndd.bundle.js` (unminified) +
  gecombineerde `ndd.styles.css`, in `wies/core/static/vendor/nldd/`. Deps:
  alleen `esbuild` (`package.json` devDependencies).
- **Laden:** `wies/core/jinja2/base.html:24` —
  `<script defer src="{{ nldd_asset('ndd.bundle.js') }}">`. `nldd_asset`
  (`config/jinja2.py:154`) cache-bust op de NLDD-versie uit `VERSION.txt`.
- **Editor-componenten (nu):** `nldd-code-viewer` komt voor op **precies één**
  template: `wies/core/jinja2/parts/error_detail_body.html:54` (staff
  error-detail). Nog geen `code-editor`/`text-editor` in de codebase.
- **Editor-componenten (binnenkort):** Wies gaat **rich text editing** gebruiken.
  Die editor-component leunt op dezelfde CodeMirror-familie en komt op reguliere
  pagina's te staan — geen randgeval meer, maar een centrale feature. Waar precies
  (direct bij page-load vs. achter een klik/modal) is nog niet vastgelegd.
- **CSP (blokkerend voor de aanpak):** `wies/core/middleware.py` zet
  `script-src 'self'; connect-src 'self'`, streng, met een test
  (`test_response_headers.py`) die faalt bij versoepeling. Alle JS extern, geen
  inline scripts.
- **Prod static:** `config/settings/production.py:38` —
  `CompressedManifestStaticFilesStorage` (WhiteNoise): hasht filenames en
  rewrite referenties **alleen** in CSS `url()` en via het manifest.

## De drie punten die er voor Wies toe doen

### 1. WhiteNoise ManifestStaticFilesStorage vs. code-split chunks — BLOKKEREND, oplosbaar

Wies serveert static in productie via `CompressedManifestStaticFilesStorage`.
Die hasht bestandsnamen (`ndd.bundle.abc123.js`) en herschrijft verwijzingen —
maar **niet** de relatieve `import "./chunk-XYZ.js"` specifiers _binnenin_ JS.
Een ESM-entry die met relatieve paden naar ~30 chunks verwijst, breekt dus:
de entry krijgt een hash, de chunks krijgen andere hashes, en de imports in de
entry wijzen naar niet-bestaande paden → 404 → dode componenten. Dit is dezelfde
klasse probleem die de `no-store`-comment in `middleware.py` al beschrijft voor
HTML.

**Opties (aflopend in voorkeur):**

- **A. Vendor-dir buiten de manifest houden.** Laat de NLDD-chunks met hun eigen
  (door de leverancier ge-hashte) namen staan en sla ze over in
  `ManifestStaticFilesStorage`. Cache-busting doet dan `nldd_asset(...)?v=<versie>`
  op alleen de entry (bestaat al). Vereist een subclass die
  `vendor/nldd/**` overslaat, of de vendor-dir buiten `collectstatic` serveren.
- **B. Autoloader-only, geen statische code-split imports.** Als de entry zélf
  geen relatieve imports bevat maar de autoloader chunks op naam ophaalt op basis
  van de tag, kan het manifest-probleem verschuiven naar "kan de autoloader het
  juiste pad vinden". Hangt af van hoe de leverancier de chunk-URLs afleidt
  (import.meta.url vs. een base-path config). **Vraag de leverancier expliciet
  hoe chunk-URLs worden opgelost** — dit bepaalt of A nodig is.

Zonder dit opgelost is de migratie niet productie-veilig. Het is geen
show-stopper, wel een vereiste.

### 2. `type="module"` + CSP — geen probleem

`script-src 'self'` staat `<script type="module" src="/static/...">` toe, en de
relatieve chunk-imports vallen ook onder `'self'` (zelfde origin). De autoloader
haalt chunks op met dynamische `import()` → ook `'self'`. `connect-src 'self'`
raakt dit niet (module-imports vallen onder `script-src`, niet `connect-src`).
**Mits alles same-origin uit `/static/` komt** (dus géén unpkg/jsdelivr in
productie — dat veld is voor anderen, niet voor ons) is CSP geen blokker. Wel
toevoegen: een test die borgt dat de vendor-dir compleet mee-gedeployd wordt.

### 3. Code-splitting is voor Wies nu wél de moeite waard

Zijn 154 KB-vs-1998 KB-meting leunt op het lui houden van CodeMirror. Zolang Wies
CodeMirror alleen op de error-pagina had, was die winst grotendeels theoretisch.
Maar **met rich text editing op reguliere pagina's telt het verschil wél**: zonder
code-splitting sleept elke paginaweergave de editor-stack mee. De autoloader die de
editor pas ophaalt wanneer een `nldd-*`-editor-tag verschijnt, is hier precies de
juiste oplossing. Een core+full bundel zou ook kunnen, maar geeft grovere controle
(je moet zelf per pagina de juiste bundel kiezen) dan de autoloader. **Aanbeveling:
neem de autoloader/code-splitting-variant** — mits punt 1 opgelost is.

## Overige punten uit zijn lijst — akkoord

- **npm-tarball +2 MB, ook voor wie zelf bundelt:** voor Wies niet relevant zodra
  we `build-nldd.mjs` + esbuild schrappen; we consumeren dan alleen de dist-dir.
- **FOUC-guard dekt lui geladen componenten niet:** klopt en raakt Wies concreet
  zodra rich text editing er is. Een editor die **direct bij page-load zichtbaar**
  is (bijv. een bewerk-pagina) wil je statisch in de entry, anders flitst het veld
  even leeg voor de chunk binnen is — de 200ms-FOUC-guard uit `fouc.css` dekt dat
  niet. Een editor die pas **na een klik** (modal/sheet/inline-edit) verschijnt,
  mag lui geladen worden; de kleine vertraging valt dan samen met het openen.
  **Waar de rich-text-editor komt is nog niet vastgelegd** → veilige default: de
  editor-chunk statisch in de entry, en pas naar lui-laden schakelen zodra het
  gebruikspatroon vaststaat. `nldd-code-viewer` (error-pagina) mag sowieso lui.
- **Relatieve chunk-paden → hele vendor-dir mee:** exact punt 1 hierboven.
- **SRI:** niet nodig voor v1 (same-origin, geen CDN). Akkoord.
- **exports-entry, CSS/fonts as-is, minified default:** akkoord.
- **Wies-specifieke CSS-logica verdwijnt niet gratis:** `build-nldd.mjs` doet nu
  meer dan bundelen — het inlinet `@import`s en herschrijft `url()`-font-refs naar
  `assets/` (regels 92–139), en concateneert 5 losse CSS-bestanden tot
  `ndd.styles.css`. Als de leverancier één klaar-om-te-linken CSS levert vervalt
  dit; levert hij losse bestanden, dan blijft een klein rewrite-stapje nodig.
  **Vraag: levert de dist één gebundelde CSS of losse bestanden?**
- **`VERSION.txt` / cache-busting:** `get_nldd_version()`
  (`wies/core/services/version.py`) leest `VERSION.txt` dat het build-script nu
  schrijft, en `test_nldd_asset.py` test dit. Een `cp -R`-variant moet dus nog
  steeds een versiestring afleiden (uit `node_modules/@nldd/design-system/package.json`).

## Waar het pakket vandaan komt: `.npmrc` en de `@minbzk`-scope

De `.npmrc` in de repo-root scopet `@minbzk` naar GitHub Packages
(`@minbzk:registry=https://npm.pkg.github.com`, auth via `${GITHUB_TOKEN}`), maar
is **nu inactief**: `package-lock.json` lost alle 96 packages — inclusief
`@nldd/design-system@0.8.77` — op van `https://registry.npmjs.org`. Er wordt op
dit moment geen enkel `@minbzk`-pakket gebruikt, dus `npm install` heeft de
`GITHUB_TOKEN` niet nodig.

De file staat er vooruitlopend: als NLDD naar een private `@minbzk` GitHub-scope
verhuist (in plaats van publiek `@nldd` op npm), is de registry-config al klaar.
**Let op:** op dat moment wordt `GITHUB_TOKEN` wél vereist bij `npm install` —
zowel lokaal als in de Docker-build (`Dockerfile`, regels 73–79). Dat is een extra
migratie-afhankelijkheid bovenop de bundel-distributie zelf.

## Concreet voor de Wies-migratie (als de leverancier levert)

1. `scripts/build-nldd.mjs` + `esbuild` devDependency verwijderen;
   `package.json` houdt alleen `@nldd/design-system` als dependency.
2. `just build-nldd` wordt een `cp -R node_modules/@nldd/design-system/dist/<esm-dir>`
   → `wies/core/static/vendor/nldd/`, plus het schrijven van `VERSION.txt` (uit
   `package.json`) en — indien de leverancier losse CSS levert — het behouden van
   het CSS-inline/rewrite-stapje. In de `Dockerfile` (regels 73–79) worden `npm
install` + `npm run build-nldd` dan een simpele install + copy; het purgen van
   node/npm daarna kan blijven.
3. `base.html:24`: `<script defer src=...>` → `<script type="module" src=...>`.
   (`defer` is impliciet bij modules; expliciet mag blijven.)
4. **Punt 1 oplossen:** vendor-dir uit `ManifestStaticFilesStorage` houden (subclass
   of aparte WhiteNoise-root), zodat de chunk-imports intact blijven. `nldd_asset`
   blijft de entry cache-busten via `?v=<versie>`.
5. **Editor-strategie vastleggen:** zodra bekend is waar de rich-text-editor komt,
   beslissen of de editor-chunk statisch in de entry gaat (direct-in-beeld) of lui
   via de autoloader (achter een klik). Veilige start: statisch, later versoepelen.
   `nldd-code-viewer` (error-pagina) mag lui.
6. `CHANGES.md`-entry onder `## unreleased`.

## Verificatie

- **Lokaal:** `just build-nldd` (nieuwe cp-variant) → `just up` → controleer dat
  `nldd-*` componenten renderen op de hoofdpagina's en dat `nldd-code-viewer` op
  de error-detail-pagina de traceback highlight.
- **Productie-pad (de echte test):** `docker build --target web` +
  `collectstatic` draaien, dan controleren dat de ge-hashte entry de chunk-imports
  nog kan resolven (geen 404's in de netwerk-tab). Dit vangt het manifest-probleem
  uit punt 1.
- **CSP:** `test_response_headers.py` moet groen blijven; voeg een check toe dat de
  vendor-chunks onder `/static/` (same-origin) laden.
- **Regressie:** `just test` (django + js).

## Wat aan de leverancier terug te vragen

1. **Hoe worden chunk-URLs opgelost** — relatieve imports in de entry, of een
   configureerbaar base-path / `import.meta.url`? (Bepaalt of WhiteNoise-optie A
   nodig is.)
2. **Autoloader-variant beschikbaar?** Wies wil de rich-text-editor lui kunnen
   laden (verschijnt op reguliere pagina's, maar niet elke pagina). De
   autoloader/code-splitting-variant is daarom onze voorkeur boven één all-in-één
   IIFE.
3. **Levert de dist één gebundelde CSS of losse bestanden?** Bepaalt of Wies's
   CSS-inline/font-rewrite-stapje kan vervallen of moet blijven.
