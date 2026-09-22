# Plan: ODI Knowledge Base — SSO-gated portal + article reader inside Wies

## Context

ODI wants a **private knowledge base / start portal**: full-page articles authored as
Markdown in a **private git repo**, built to static HTML by **Hugo in GitHub Actions**,
readable only by ODI staff via SSO. Wies (at `wies.rijksorganisatieodi.nl`) already solves
ODI SSO auth and deploys to the ZAD platform, so the KB is built **as an app inside the Wies
codebase** to reuse auth, the user list, and the deploy pipeline.

**Iteration 1 ships at `wies.rijksorganisatieodi.nl/start/`** (a path under Wies), _not_ the
`start.rijksorganisatieodi.nl` subdomain. The subdomain is the eventual home (it's a hub /
front door, and a hub shouldn't visibly live inside one of the tools it links to), but
standing it up needs DNS + TLS + ingress that "may take a while." Gating the first release on
that would ship nothing. A path is **same-origin as Wies**, so it needs _zero_ new auth,
cookie, host-routing, or Keycloak work — it unblocks iteration 1 entirely. Promotion to the
subdomain later is a **config-only, lossless** change (see "Future: promote to subdomain"):
the app code is identical, only the mount point and infra items differ, and a 301 keeps every
`/start/` bookmark alive.

The full decision analysis (every architectural fork, both sides, the deciding factor)
lives in `ODI-KB-ARCHITECTURE-COMPARISON.md` at the repo root. This plan is the chosen
design only.

**Decisions taken (this session):**

- **App inside Wies** (`wies/kb/`), not a separate service — one DB, one `User` model,
  `rijksauth` imported directly, `wies.core`'s `no_access` reused. **No shared-DB
  machinery, no new image** (ships in the existing `web`/`worker` images).
- **MinIO bucket** holds the built HTML (replica-safe; Wies may scale to >1 `web`
  replica, which rules out a `ReadWriteOnce` volume; free object versioning aids rollback).
- **Stream-through serving**: `boto3.get_object()` → `StreamingHttpResponse`. No nginx,
  no volume, no `X-Accel-Redirect` (that offloads _local_ files and needs a proxy Wies
  doesn't have). Presigned-URL redirect is the future escape hatch if worker-occupancy
  ever bites — not built now.
- **Publish = pull, not push**: Hugo CI attaches the built site as a **GitHub release
  artifact** (CI gets no credentials to ODI infra). A **role-gated manual button** (e.g.
  Beheerder) enqueues a background job on the existing **`db_worker`** that downloads the
  artifact, unpacks it, uploads objects to a **new MinIO prefix, then flips a pointer**
  (atomic publish). Designed so a future GitHub webhook can trigger the same job — build
  the button now, webhook later, no rework.
- **Portal + reader, mounted at a path**: it's a hub (curated portal pages that link out to
  the KB, Wies, and other tools — real Django views) _plus_ the article catch-all underneath.
  Iteration 1 mounts the whole thing at `wies.rijksorganisatieodi.nl/start/` via a single
  `include()` in `config/urls.py`.
- **Auth is free (same origin)**: because `/start/` is the same host as Wies, it inherits
  Wies's existing session cookie, Keycloak client + redirect URI, `ALLOWED_HOSTS`, and CSRF
  config **with no changes**. No host routing, no `SESSION_COOKIE_DOMAIN`, no new Keycloak
  client, no domain-wide-cookie risk — all of that is deferred with the subdomain. The
  existing `LoginRequiredMiddleware` gates `/start/` automatically.
- **Keep promotion cheap**: write the app's URLs **relative** (mounted under one `include()`,
  no hardcoded `/start/` inside the app) and build all links via `reverse()` /
  `build_absolute_uri` (never hardcode host or prefix). That makes the eventual subdomain move
  a one-line mount change + a 301, not a prefix hunt. See "Future: promote to subdomain".

## Approach

### 1. The `wies/kb/` app

- New Django app `wies/kb/` in the existing project. `rijksauth` is already installed and
  wired; the KB reuses it and `wies.core`'s `no_access` view + `no_access.html` +
  `login_error.html`. No auth code is written or copied.
- **Portal views**: server-rendered landing/portal page(s) using the same NLDD components
  as the rest of Wies (curated links to articles, to Wies, etc.).
- **Article catch-all view** (the one genuinely new serving path), gated by the existing
  `LoginRequiredMiddleware`:
  - Take the request path, **sanitize** it (reject `..`, absolute paths — no escaping the
    KB prefix in the bucket).
  - Resolve to a MinIO object key, applying Hugo's **pretty-URL** rule: a trailing-slash
    path → `<path>index.html`; redirect `/x` → `/x/` for consistency.
  - `s3.get_object(Bucket=..., Key=...)`; on missing key → `Http404`.
  - Return `StreamingHttpResponse(body.iter_chunks(), content_type=obj["ContentType"])`.
  - Serves **assets too** (CSS/JS/images are private objects under their own keys) — which
    is exactly why serving goes through this view, never WhiteNoise (WhiteNoise runs before
    auth and is public).
- **URL ordering**: explicit portal routes first; the article catch-all is the **last**
  pattern so it only claims paths the portal didn't.

### 2. Mounting + settings (iteration 1: a path, no new host)

Same `web` image, same ZAD component, **same host** — so this section is nearly empty, which
is the whole point of shipping a path first.

- **Mount**: one line in `config/urls.py` — `path("start/", include("wies.kb.urls"))`.
  Portal routes first, article catch-all last (see §1).
- **Settings**: **none required.** `/start/` inherits Wies's session cookie, Keycloak client,
  redirect URI, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` unchanged because it's the same
  origin. No `SESSION_COOKIE_DOMAIN`, no host routing, no new Keycloak client. (The whole
  cookie/host/Keycloak surface is deferred to the subdomain promotion — see the Future
  section.)
- **DNS / TLS / ingress**: **none** — it's the existing Wies host.

### 3. MinIO storage + `boto3`

- Add `boto3` dependency (Wies has none today). Configure an S3 client against the MinIO
  endpoint.
- New ZAD secrets: MinIO endpoint + access/secret keys.
- Bucket layout supporting **atomic publish**: upload each release under a versioned prefix
  (e.g. `sites/<release-tag>/…`), then flip a small **current-pointer** object (or a
  settings/DB value) the catch-all view reads to resolve the active prefix. Readers never
  see a half-written site; rollback = point back at a previous prefix (object versioning
  also available).

### 4. Publish job (pull-via-button, webhook-ready)

- A background job on the existing `db_worker`, implemented with the `TaskCommand` base
  (`wies/core/management/task.py`): download the latest **GitHub release artifact** from
  the private content repo (GitHub read token, new ZAD secret) → unpack → upload objects to
  a new MinIO prefix → flip the current-pointer.
- **Trigger**: a **role-gated button** in the KB portal (gate via `wies/core/roles.py`,
  e.g. Beheerder) that enqueues the job; status shown via HTMX polling/swap (Wies pattern).
- **Webhook-ready**: factor the job so a future GitHub "release published" webhook can
  enqueue the _same_ job with no rework (still a pull — CI never gets infra credentials).

## Critical files

- **New**: `wies/kb/` — app (portal views, article catch-all view, urls), the
  `db_worker` publish task (subclass `wies/core/management/task.py`'s `TaskCommand`), MinIO
  client helper, templates for portal pages.
- **Edit**: `config/urls.py` (`path("start/", include("wies.kb.urls"))`), `config/settings/*`
  (MinIO + GitHub-token settings only — **no auth/cookie/host changes in iteration 1**),
  `pyproject.toml` (`boto3`).
- **Reuse (no change)**: `wies/rijksauth/*`, `wies.core`'s `no_access` view + templates,
  `wies/core/roles.py` (button gate).
- **Outside this repo**: the private Hugo content repo's GitHub Actions gains a step that
  attaches the built site as a release artifact.

## Verification

1. **Auth gate**: request `/start/onboarding/` while logged out → redirect to login; logged
   into Wies → served directly (same session, no extra round-trip — it's the same origin).
2. **Non-ODI user**: no `auth_user` row → `AuthBackend` denies → `geen-toegang/`.
3. **Serving**: seed the bucket; `/start/onboarding/` streams `onboarding/index.html`;
   a referenced asset (`/start/css/…`) streams with correct content-type; unknown path → 404.
4. **Path traversal**: `../`-style keys are rejected → 404, never escape the KB prefix.
5. **Portal vs. catch-all**: `/start/` renders the portal view (not a MinIO lookup);
   article paths fall through to the catch-all; no shadowing either way.
6. **Publish**: click the button as a Beheerder → `db_worker` pulls the release artifact,
   uploads to a new prefix, flips the pointer; readers see the new content; a mid-publish
   request never sees a half-written site. Non-privileged users don't see the button.
7. **Relative-URL discipline**: grep the app for hardcoded `/start/` and absolute hosts —
   there should be none (all via `include()` + `reverse()`), so promotion stays a one-liner.
8. **Tests** in `wies/kb/tests/`: catch-all (authed 200, unauthed redirect, traversal 404,
   pretty-URL resolution), portal view, publish task (mock MinIO + GitHub), button role
   gate. Run with `DJANGO_SETTINGS_MODULE=config.settings.test`.

## Open items (platform team) — iteration 1 only

- MinIO endpoint reachable from ZAD `web`/`worker`; keys as ZAD secrets.
- GitHub read token scope for the private content repo's release artifacts, from ZAD.
- Reconfirm `web` replica count (MinIO is safe either way; this drove the storage choice).

(Notably, iteration 1 needs **no DNS/TLS/ingress/Keycloak** change — that's the point of the
path-first approach.)

## Future: promote to `start.rijksorganisatieodi.nl` subdomain

When the subdomain infra is available, promote the (unchanged) app to its own host. This is
config + one redirect, no app rewrite — provided the relative-URL discipline (§1) held:

- **Platform**: DNS + TLS for `start.` (trivial with a `*.rijksorganisatieodi.nl` wildcard
  cert; else a request), ZAD ingress routing `start.` → the existing `web` component, and the
  ingress **must forward the real `Host` header** (not rewrite to an internal name) —
  `rijksauth` derives the OIDC redirect URI from the request host.
- **Django**: host-based routing (`start.` → KB urlconf, `wies.` → Wies), `ALLOWED_HOSTS` +=
  `start.`, `CSRF_TRUSTED_ORIGINS` += `https://start.rijksorganisatieodi.nl`.
- **Cookies**: keep them **host-scoped** — do NOT set `SESSION_COOKIE_DOMAIN` to
  `.rijksorganisatieodi.nl`. We don't govern every subdomain, so a domain-wide cookie would
  leak the session to hosts we don't control. Cross-host SSO comes from **Keycloak** instead:
  a user with a Keycloak session hitting `start.` does one silent OIDC round-trip and is
  logged in with no password prompt.
- **Keycloak**: add `https://start.rijksorganisatieodi.nl/auth/` to the **existing shared
  client's** allowed redirect URIs — no new client (the redirect URI is derived from the
  request host by the same code).
- **Migration glue**: mount the app at `/` on `start.`, and add a **301 from
  `wies.../start/…` → `start./…`** so every iteration-1 bookmark and shared link survives.

## Deferred (a "later" concern, not now)

- **nginx / reverse proxy** in front of Wies — justified on Wies's _own_ merits (static
  serving, TLS termination, proxy hardening), not the KB. If added, the KB could adopt
  presigned-URL redirects for large-file efficiency; neither is needed at current scale.
- **Webhook auto-publish** — the pull job is built webhook-ready; wiring the GitHub webhook
  is a follow-up once the manual button is proven.
