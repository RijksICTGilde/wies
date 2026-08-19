# Bezetting-pagina onder "Business management"

> Tijdelijk PR-beschrijving-bestand. Wordt vóór het mergen verwijderd.

## Wat & waarom

Business managers (BDM's) hebben een overzicht nodig van **wie werk nodig heeft**:
wie zit op de bank en wie is volledig ingezet, en welke inzet loopt binnenkort af.
Hiervoor is een nieuwe **"Business management"**-sectie toegevoegd met een
**"Bezetting"**-tijdlijn.

**Scope:** deze PR implementeert alleen de Bezetting-pagina zelf. Uren per
opdracht en contracturen per collega zitten hier bewust **niet** in; die komen in
een aparte, latere PR. Daarom is bezetting nu binair (op de bank / volledig
ingezet) zonder tussenstaat.

Belangrijke ontwerpkeuzes en de onderbouwing daarvan:

- **Geen datamodel-wijzigingen.** De app registreert geen uren per week, dus
  bezetting is binair: een collega is **"op de bank"** (geen actieve plaatsing
  vandaag) of **"volledig ingezet"** (≥1 actieve plaatsing). Bewust géén
  tussenstaat ("deels vrij"), omdat we die data niet hebben en niet in deze stap
  willen introduceren.
- **Alleen zichtbaar voor Business Development Managers.** De hele sectie zit
  achter een role-gate op de bestaande BDM-groep. Er is bewust geen nieuwe rol
  aangemaakt; de BDM-groep is de bestaande rol die deze taak past.
- **Alleen consultants in de lijst.** De tijdlijn toont alleen collega's die de
  rol **Consultant** hebben (de gekoppelde gebruiker zit in de groep
  "Consultant"). Collega's zonder gekoppelde gebruiker vallen dus buiten de
  lijst. **Let op:** dit is de eerste keer dat functionele logica gekoppeld wordt
  aan de groep "Consultant" — tot nu toe had die groep geen effect (lege
  permissieset). Zorg er dus voor dat consultants ook echt in die groep zitten.
- **Tijdlijn (Gantt-stijl)** over een horizon van 3 maanden terug tot 1 jaar
  vooruit, gesorteerd op urgentie: eerst wie op de bank zit, dan wie volledig is
  ingezet, met de opdrachten die het eerst aflopen bovenaan. Een rij is helemaal
  klikbaar en opent hetzelfde collega-panel als "Wie zit waar?".
- **Filteren op merk en op label-categorieën.** De filters hergebruiken de
  facet-/filterlogica van "Wie zit waar?" (OR binnen een categorie, AND tussen
  categorieën). Er worden alleen merken/labels aangeboden die daadwerkelijk aan
  een collega zijn toegekend, zodat de filters niet vervuilen met ongebruikte
  waarden.

### Waarom "alle label-categorieën" filterbaar zijn

Het filter werkt bewust op **alle** label-categorieën (niet een vaste set). De
directe aanleiding: binnen het RIG moet een **subverdeling** gemaakt kunnen
worden. Door na de release een nieuwe label-categorie **"Subgroep"** aan te maken
met de labels **"IT Gilde"** en **"Data en AI Gilde"** en collega's aan de juiste
subgroep toe te kennen, verschijnt die subverdeling automatisch als filter op de
Bezetting-pagina.

## UI-details

- De filters zitten in een **filtersheet** die links openschuift — hetzelfde
  patroon als de "Gebruikers"-lijst. Een "Filters"-knop opent de sheet; per facet
  (merk en elke label-categorie) staat een lijst met aanvinkbare opties met een
  telling ernaast, plus een "Meer…"-sheet als er meer dan drie opties zijn.
- Aanvinken filtert **direct** (htmx): de tijdlijn en de samenvattingskaarten
  herladen ter plekke, de sheet blijft open en de tellingen volgen mee. Actieve
  filters verschijnen als chips boven de tijdlijn, met "Wis alle filters".
- Er is bewust **geen "Rol"-filter**: iedereen op deze pagina is consultant.
- CSP-veilig: geen inline JS. De gedeelde filterlogica zit in
  `static/js/filter_interactions.js`; `static/js/user_filter.js` opent de sheet.

## Post-release acties

> Deze acties zijn ook geannoteerd in `CHANGES.md` met `(post-release actions)`.

- [ ] **Maak in productie de label-categorie "Subgroep" aan**, met de labels
      **"IT Gilde"** en **"Data en AI Gilde"**.
- [ ] **Ken de betreffende collega's toe** aan de juiste subgroep.

Pas daarna verschijnt de "Subgroep"-filter op de Bezetting-pagina (er worden
alleen categorieën/labels getoond die aan minstens één collega zijn toegekend).
