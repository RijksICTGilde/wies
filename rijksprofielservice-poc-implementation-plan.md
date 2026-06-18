# Wies integreren met de Rijksprofielservice

Praktische handleiding voor een Wies-developer die de Rijksprofielservice wil aansluiten als bron voor profielgegevens. Stap-voor-stap, met code-voorbeelden tegen de lokale PoC-setup.

## Architectuur op één scherm

```
Browser
   │
   ▼
Wies (localhost:8080)                Rijksprofielservice (localhost:8000)
   │                                  │
   │  1. user wil teamlijst zien      │
   ├─────────────────────────────────▶│  /oauth/authorize?client_id=wies&redirect_uri=...&state=...
   │                                  │  → toont consent-scherm
   │  2. user geeft toestemming       │
   │◀─────────────────────────────────┤  /callback?consent=granted&state=...&subject_id=<UUID>
   │                                  │
   │  3. M2M token aanvragen          │
   │            ┌─────────────────────┴─────────┐
   │            │  Keycloak (localhost:8081)    │
   │            │  POST /realms/profielservice/ │
   │            │       /openid-connect/token   │
   │            └─────────────────────┬─────────┘
   │                                  │
   │  4. batch-API call met Bearer    │
   ├─────────────────────────────────▶│  POST /api/v1/profiles/batch
   │  ◀──────────────────────────────│  { "profiles": { "<UUID>": {...} } }
   │                                  │
```

## Lokale poorten

| Service                        | Host-poort | Doel                                                |
| ------------------------------ | ---------- | --------------------------------------------------- |
| Wies (Django)                  | `8080`     | Standaard Wies.                                     |
| Rijksprofielservice (Django)   | `8000`     | Bewust uit de weg van Wies.                         |
| Postgres (rijksprofielservice) | `5433`     | Naast standaard 5432 (Wies).                        |
| Keycloak                       | `8081`     | M2M tokens + admin console (`/admin`, admin/admin). |

Beide repo's kunnen tegelijk draaien zonder conflicten.

## Stap 1 — Keycloak client registreren

De Rijksprofielservice valideert M2M-tokens tegen de `profielservice` realm in onze lokale Keycloak. Wies heeft daar een eigen client nodig.

Twee opties:

**Optie A — handmatig via admin console:**

1. Open <http://localhost:8081/admin> (admin/admin).
2. Realm `profielservice` → Clients → Create client.
3. Settings: Client type=OpenID Connect, Client ID=`wies`.
4. Capability config:
   - Client authentication: **on** (confidential)
   - Authorization: off
   - Standard flow: **off**
   - Direct access grants: **off**
   - Implicit flow: **off**
   - Service accounts roles: **on**
5. Login settings: alles leeg laten.
6. Save → Credentials tab → kopieer Client secret.

**Optie B — realm-import aanvullen:**
Voeg een client-entry toe aan [`keycloak/realms/profielservice-realm.json`](../keycloak/realms/profielservice-realm.json) (zelfde shape als `mock-wies`) en herstart Keycloak: `docker compose down -v keycloak && docker compose up keycloak`.

## Stap 2 — Application registreren bij rijksprofielservice

Naast Keycloak moet de profielservice de app **goedkeuren**. Dit is een extra beveiligingslaag bovenop Keycloak-registratie.

1. Open <http://localhost:8000/admin> (admin/admin uit `.env`).
2. Core → Applications → Add application.
3. Vul in:
   - **Naam**: `Wies`
   - **Client id**: `wies` (moet exact matchen met Keycloak client_id en JWT `azp` claim)
   - **Beschrijving**: bv. `Bemiddelingsplatform voor opdrachten en collega's.`
   - **Requested fields**: kies de profielvelden die Wies wil opvragen, bv. `["naam","email","telefoon","functie","avatar"]`
   - **Redirect uris**: `["http://localhost:8080/profielservice/callback/"]` (of welke callback-URL Wies ook gebruikt)
   - **Is approved**: ✓
4. Save.

## Stap 3 — OAuth-style consent flow

De profielservice gebruikt een eigen "OAuth-style" redirect-flow (geen echte code/token exchange — die komt later). Wies stuurt de gebruiker naar de profielservice, krijgt een redirect terug met grant/deny.

### Wies-kant: redirect naar profielservice

```python
# wies/views.py — voorbeeld
import secrets
from urllib.parse import urlencode
from django.shortcuts import redirect

PROFIELSERVICE_AUTHORIZE_URL = "http://localhost:8000/oauth/authorize"
PROFIELSERVICE_CLIENT_ID = "wies"
CALLBACK_URL = "http://localhost:8080/profielservice/callback/"

def vraag_profiel_toestemming(request):
    state = secrets.token_urlsafe(16)
    request.session["profielservice_state"] = state
    params = {
        "client_id": PROFIELSERVICE_CLIENT_ID,
        "redirect_uri": CALLBACK_URL,
        "state": state,
        # optioneel: requested_fields=naam,email om subset op te vragen
    }
    return redirect(f"{PROFIELSERVICE_AUTHORIZE_URL}?{urlencode(params)}")
```

### Wies-kant: callback verwerken

Na grant of deny redirect de profielservice terug naar `redirect_uri`:

- **Grant**: `?consent=granted&state=<jouw-state>&subject_id=<UUID>`
- **Deny**: `?consent=denied&state=<jouw-state>` (geen `subject_id`)

```python
# wies/views.py — voorbeeld
def profielservice_callback(request):
    state_uit_request = request.GET.get("state", "")
    state_uit_session = request.session.pop("profielservice_state", None)
    if not state_uit_session or state_uit_session != state_uit_request:
        return HttpResponseBadRequest("State-mismatch")

    if request.GET.get("consent") != "granted":
        # User heeft geweigerd; toon fallback.
        return render(request, "wies/profiel_geweigerd.html")

    subject_id = request.GET.get("subject_id", "")
    # subject_id is de UUID waarmee je het profiel kunt opvragen.
    # Sla 'm op aan de Wies-user zodat je dit later opnieuw kunt gebruiken.
    request.user.rijksprofielservice_sub = subject_id
    request.user.save(update_fields=["rijksprofielservice_sub"])

    return redirect("wies:dashboard")
```

## Stap 4 — M2M token ophalen bij Keycloak

Eenmalig (of bij elke API-call, of gecached) haalt Wies een client-credentials token op.

```python
# wies/profielservice_client.py — voorbeeld
import time
import httpx

KEYCLOAK_TOKEN_URL = "http://localhost:8081/realms/profielservice/protocol/openid-connect/token"
PROFIELSERVICE_CLIENT_ID = "wies"
PROFIELSERVICE_CLIENT_SECRET = "..."  # uit Keycloak Credentials tab

_token_cache = {"token": None, "expires_at": 0}

def get_m2m_token() -> str:
    """Haal client-credentials token bij Keycloak. Cache TTL respecteert exp."""
    if _token_cache["expires_at"] > time.time() + 30:
        return _token_cache["token"]
    response = httpx.post(
        KEYCLOAK_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": PROFIELSERVICE_CLIENT_ID,
            "client_secret": PROFIELSERVICE_CLIENT_SECRET,
        },
        timeout=5,
    )
    response.raise_for_status()
    data = response.json()
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"]
    return data["access_token"]
```

## Stap 5 — Batch-API aanroepen

```python
# wies/profielservice_client.py — voorbeeld vervolg
PROFIELEN_BATCH_URL = "http://localhost:8000/api/v1/profiles/batch"

def haal_profielen(subject_ids: list[str]) -> dict:
    """Haal meerdere profielen in één call. Response shape:
       {"profiles": {"<UUID>": {...velden...} | null}}
       null betekent: user bestaat niet OF geen consent voor deze app.
    """
    response = httpx.post(
        PROFIELEN_BATCH_URL,
        json={"subject_ids": subject_ids},
        headers={"Authorization": f"Bearer {get_m2m_token()}"},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()["profiles"]
```

Voorbeeld response:

```json
{
  "profiles": {
    "01d256f8-f354-46b7-a18f-2ad919bbf9cd": {
      "naam": "Matthijs Beekman",
      "email": "matthijs.beekman@rijksoverheid.nl",
      "telefoon": "06-1234",
      "functie": "Beleidsmedewerker",
      "avatar_url": "http://localhost:8000/avatars/6.jpg"
    },
    "00000000-0000-0000-0000-000000000099": null
  }
}
```

Velden in de response zijn de doorsnijding van `Application.requested_fields` ∩ user-consent. `null` betekent geen consent of onbekend subject.

## Stap 6 — Caching aan Wies-kant

De profielservice rate-limit of cached zelf nog niet. Wies kan een korte in-memory cache (5 min TTL) gebruiken om het aantal API-calls te beperken. Zie [`integratie-patronen.md`](integratie-patronen.md) voor HTMX lazy loading en batch-patronen.

## Foutgevallen

| Status | Betekenis                                                                                         | Wat te doen                                                                             |
| ------ | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 400    | Onbekende client_id, ongeldige redirect_uri, of ongeldige requested_fields bij `/oauth/authorize` | Check Application-registratie en redirect_uri whitelist.                                |
| 401    | Token ontbreekt, ongeldig, verlopen, verkeerde issuer, of signature mismatch op batch-API         | Vernieuw token; check `iss`-claim matcht `http://localhost:8081/realms/profielservice`. |
| 403    | App niet goedgekeurd (`is_approved=false`) bij `/oauth/authorize` of batch-API                    | Vraag admin om goedkeuring.                                                             |
| 404    | Onbekend subject_id bij `/api/v1/profiles/<id>`                                                   | User bestaat niet.                                                                      |

## Testen zonder Keycloak

Voor snelle dev-loops zonder echte Keycloak-token kun je de PoC-bypass gebruiken:

```sh
# Op de rijksprofielservice-kant: zorg dat PROFIELSERVICE_JWT_ALLOW_TEST_KEY=true in .env
docker compose run --rm django python manage.py mint_test_token --app wies
# → print een RS256 JWT met kid=test-kid, geldig 1 uur.
```

Deze token wordt geaccepteerd door de batch-API mits `PROFIELSERVICE_JWT_ALLOW_TEST_KEY=true`. Niet inschakelen in productie.

## Verschillen met productie (toekomst)

Dit is een **PoC-flow**. Voor productie staat op de roadmap (zie hoofd-`README.md` PoC2):

- Echte OAuth Authorization Code grant met code/token exchange (in plaats van eigen redirect).
- `redirect_uri` validatie verhuist naar Keycloak.
- HTTP caching headers (`ETag`, `Cache-Control`, `Vary: Authorization`).
- Productie-grade JWT-validatie is in PoC1 al af (JWKS-cache + signature + iss-check).

## Implementatie-aantekeningen bij Wies (geleerd tijdens uitrol)

Een paar valkuilen die je tijdens de Wies-PoC-implementatie tegenkomt:

### Subject_id is geen UUID

De handleiding hierboven suggereert UUIDs (bv. `01d256f8-...`), maar de PoC-profielservice stuurt willekeurige strings (`demo-sub-foobar`). Sla `subject_id` op als `CharField`, niet `UUIDField`, anders crasht de save in stilte.

### Session-cookie clash op localhost

Wies en Rijksprofielservice zijn allebei Django-apps die op `localhost` draaien (verschillende poorten). Browsers delen cookies tussen poorten op dezelfde host, dus de default `sessionid`-cookie van de ene app overschrijft die van de andere — Wies' user wordt zo "uitgelogd" zodra de profielservice op `localhost:8000` een sessie aanmaakt.

Geef Wies een unieke cookie-naam in [config/settings/base.py](../../wies/config/settings/base.py):

```python
SESSION_COOKIE_NAME = "wies_sessionid"
CSRF_COOKIE_NAME = "wies_csrftoken"
```

### Container ↔ host networking (twee URLs nodig)

Wies draait in een Docker-container. De rijksprofielservice en Keycloak draaien op de host. Wies praat op twee manieren met de profielservice:

- **Browser-redirect** (consent-scherm): de URL moet door de browser bereikbaar zijn → `http://localhost:8000`.
- **Back-channel API-call** (batch + Keycloak-token): de URL moet vanuit de container bereikbaar zijn → `http://host.docker.internal:8000` resp. `:8081` op macOS/Windows. Op Linux moet je `extra_hosts: ["host.docker.internal:host-gateway"]` toevoegen aan `docker-compose.yml`.

Daarom twee aparte settings:

```python
RIJKSPROFIELSERVICE_BROWSER_URL = "http://localhost:8000"        # browser-redirect
RIJKSPROFIELSERVICE_API_URL     = "http://host.docker.internal:8000"  # back-channel
RIJKSPROFIELSERVICE_TOKEN_URL   = "http://host.docker.internal:8081/realms/profielservice/protocol/openid-connect/token"
```

### ALLOWED_HOSTS-mismatch bij Host-header override

Als je via `host.docker.internal:8000` requests doet, krijgt de profielservice die hostnaam in de `Host`-header. Staat hij niet in `ALLOWED_HOSTS`, dan antwoordt Django met een HTML 400-DEBUG-pagina — een verraderlijke fout omdat `response.text` dan met `<!DOCTYPE html>` begint in plaats van een nette JSON-error.

Oplossing voor de PoC: override de Host-header expliciet zodat de TCP-connectie naar `host.docker.internal` gaat maar de profielservice `localhost` ziet:

```python
RIJKSPROFIELSERVICE_API_HOST_HEADER = "localhost:8000"
# ...
headers = {"Authorization": f"Bearer {token}"}
if settings.RIJKSPROFIELSERVICE_API_HOST_HEADER:
    headers["Host"] = settings.RIJKSPROFIELSERVICE_API_HOST_HEADER
```

Productiefix: zorg dat de profielservice `host.docker.internal` (of beter: de echte hostname) in `ALLOWED_HOSTS` heeft.

### .env variabelen voor Wies

Minimale set in `.env`:

```
RIJKSPROFIELSERVICE_CLIENT_SECRET=<uit Keycloak Credentials tab>
RIJKSPROFIELSERVICE_API_URL=http://host.docker.internal:8000
RIJKSPROFIELSERVICE_TOKEN_URL=http://host.docker.internal:8081/realms/profielservice/protocol/openid-connect/token
RIJKSPROFIELSERVICE_API_HOST_HEADER=localhost:8000
```

(`RIJKSPROFIELSERVICE_BROWSER_URL` en `RIJKSPROFIELSERVICE_CLIENT_ID` houden hun default.)

Vergeet niet: `env_file` wordt alleen geladen bij container-start, niet door autoreload. Na een `.env`-wijziging dus `just down && just up`.
