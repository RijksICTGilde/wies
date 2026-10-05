# Toegankelijkheidsonderzoek

Het WCAG-onderzoeksrapport van Wies. De `.html` wordt uitgeserveerd op
`/toegankelijkheid/onderzoek/`, zonder dat je hoeft in te loggen: de
toegankelijkheidsverklaring in het DigiToegankelijk-register
([29132](https://www.toegankelijkheidsverklaring.nl/register/29132)) linkt
rechtstreeks naar die URL, en de checklist van het register wijst "een link naar
een pagina achter een inlogscherm" af.

De `.md` ernaast is de bron waaruit de `.html` is gemaakt; hij staat erbij zodat
een volgend onderzoek niet opnieuw hoeft te beginnen.

## Een nieuw onderzoek publiceren

1. Zet het nieuwe rapport hiernaast als `onderzoek-wcag22-<datum>.html` (en de
   markdown ernaast).
2. Wijs `CURRENT_AUDIT_REPORT` in `wies/core/views.py` naar het nieuwe bestand.
3. Laat het oude bestand staan. De URL verandert niet, dus de link in het
   register blijft werken.

De URL mag niet verplaatsen: hij staat in een openbaar register en wordt door
toezichthouders gecontroleerd.
