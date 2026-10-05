# Toegankelijkheidsonderzoek

Het WCAG-onderzoeksrapport van Wies. De markdown hiernaast is de bron; de HTML
die eruit is gemaakt staat in `wies/core/static/toegankelijkheid/` en wordt als
gewoon statisch bestand uitgeserveerd.

Je leest het rapport op `/toegankelijkheid/onderzoek/`, zonder in te loggen: de
toegankelijkheidsverklaring in het DigiToegankelijk-register
([29132](https://www.toegankelijkheidsverklaring.nl/register/29132)) linkt
rechtstreeks naar die URL, en de checklist van het register wijst "een link naar
een pagina achter een inlogscherm" af.

Die URL is een view die doorstuurt naar het statische bestand. Dat tussenstapje
is nodig omdat productie de bestandsnaam van een statisch bestand van een hash
voorziet: zonder de view zou elke nieuwe versie van het rapport op een andere
URL landen en de link in het register breken.

## Een nieuw onderzoek publiceren

1. Zet de nieuwe markdown hiernaast als `onderzoek-wcag22-<datum>.md`.
2. Zet de HTML ernaast in `wies/core/static/toegankelijkheid/` onder dezelfde
   naam.
3. Wijs `CURRENT_AUDIT_REPORT` in `wies/core/views.py` naar het nieuwe bestand.
4. Laat het oude bestand staan. De URL verandert niet, dus de link in het
   register blijft werken.

De URL mag niet verplaatsen: hij staat in een openbaar register en wordt door
toezichthouders gecontroleerd.
