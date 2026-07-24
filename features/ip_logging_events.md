# Adding device/IP context to event log (BIO compliance)

## Context

BIO requires that each log entry contains "het gebruikte apparaat" (the
device used). The current `Event` and `AuthEvent` models capture user,
action, timestamp and free-form `context`, but no device identifier
(see [wies/core/models.py:252-276](wies/core/models.py#L252-L276) and
[wies/rijksauth/models.py:34-41](wies/rijksauth/models.py#L34-L41)).

Two well-known articles raise spoofing concerns for `X-Forwarded-For`
on Heroku/Flask and an older Django CVE. The objection only applies
when the app sits behind an _untrusted_ edge that lets clients inject
the header. **Wies does not have this exposure:** production runs in
the ODCN Kubernetes tenant behind a government-managed
ingress/load-balancer ([docs/beheer.md:27-29](docs/beheer.md#L27-L29);
production already trusts `HTTP_X_FORWARDED_PROTO` via
`SECURE_PROXY_SSL_HEADER` at
[config/settings/production.py:17](config/settings/production.py#L17)).
So IP from `X-Forwarded-For` is trustworthy here _provided_ we read
the right position — the rightmost entry the trusted proxy added, not
the leftmost client-supplied value.

**Caveat on IP-as-device:** IP identifies a network endpoint, not a
device. On corporate NAT many devices share one IP. The realistic
best-effort to honour BIO (c) in a web app is **IP + User-Agent
together**, documented as such.

## Approach

### Phase 0: Debug endpoint to determine `TRUSTED_PROXY_HOPS`

Before wiring IP logging in, ship a small staff-only page that reveals
what request metadata the pod actually receives. We use its output to
pick the correct hop count, then remove the endpoint.

- New view `debug_request_meta` in [wies/core/views.py](wies/core/views.py),
  decorated with the existing `@staff_required` at
  [wies/core/views.py:486](wies/core/views.py#L486) (already used for
  `staff_dashboard` — same gate).
- URL: `/beheer/debug/request-meta/` (Dutch-consistent, under the
  admin area).
- Template renders (plain `<pre>` inside the RVO layout is fine):
  - `REMOTE_ADDR`
  - `HTTP_X_FORWARDED_FOR` (raw, unsplit)
  - `HTTP_X_FORWARDED_FOR` split by `,` and stripped, indexed
    (`[0] = ...`, `[1] = ...`, `[-1] = ...`) — makes the "which entry
    is me" question a one-glance answer
  - `HTTP_X_FORWARDED_PROTO`, `HTTP_X_FORWARDED_HOST`,
    `HTTP_X_REAL_IP` (some ingresses set this instead)
  - `HTTP_USER_AGENT`
  - Server time
- **How to interpret:** open the page from your own laptop, note your
  public IP (e.g. `curl ifconfig.me` beforehand). Find your public IP
  in the split list. If it's at index `-1`, hops = 1. If at `-2`,
  hops = 2. If it's at `[0]` and there are more entries after it, the
  entries after `[0]` are the proxies you trust (count them).
- Ship, deploy to production, hit the page, decide, set
  `TRUSTED_PROXY_HOPS`, then **remove the endpoint** in a follow-up
  PR (or gate it behind `DEBUG` if we want to keep it for future
  incidents — decide when we remove it).
- Security notes for the debug page: (a) `@staff_required` — same gate
  as the existing staff dashboard, no new trust surface; (b) it only
  echoes headers of the _current_ request (the staff member's own),
  not other users' data, so it isn't a cross-user leak even if the
  gate ever slipped; (c) do not log the page's output to files or the
  changelog — staff should read it in the browser and discard.

### Phase 1: Wire IP + User-Agent into event logging

1. **Add a `get_client_ip(request)` helper** in
   `wies/core/utils/request_meta.py` (new file). Behaviour:
   - If `settings.TRUSTED_PROXY_HOPS > 0`: parse
     `request.META["HTTP_X_FORWARDED_FOR"]`, split on `,`, strip, take
     the entry at `-TRUSTED_PROXY_HOPS` (rightmost-minus-N). Fall back
     to `REMOTE_ADDR` if the header is missing or shorter than
     expected.
   - If `TRUSTED_PROXY_HOPS == 0` (local/dev/test): return
     `request.META["REMOTE_ADDR"]`.
   - Also export `get_user_agent(request)` returning
     `request.META.get("HTTP_USER_AGENT", "")[:512]`.

2. **Configure trusted hop count.**
   - `config/settings/base.py`: `TRUSTED_PROXY_HOPS = 0` (safe default
     for dev/test — `REMOTE_ADDR` only, no header trust).
   - `config/settings/production.py`: read from env
     `TRUSTED_PROXY_HOPS = int(os.environ["TRUSTED_PROXY_HOPS"])`
     (fail-fast: production must set it explicitly, no silent
     default). The right value depends on how many proxies ODCN puts
     in front of the pod — must be confirmed with ODCN before
     deployment (see "Open question" below). Until confirmed, do not
     set the env var; the code can ship and the feature simply won't
     log IP in production yet.

3. **Extend `create_event`** at
   [wies/core/services/events.py:12](wies/core/services/events.py#L12)
   to accept an optional `request` kwarg. When supplied, attach
   `ip` and `user_agent` keys to `context` (do not add new columns —
   `context` is already a JSONField, see
   [wies/core/models.py:262](wies/core/models.py#L262)). This keeps
   the schema migration-free.

4. **Pass `request` from the 11 view-based call sites** (all listed
   below have `request` in scope). The 4 sync-driven sites in
   `wies/core/services/organizations.py` legitimately have no
   request — leave them alone; their `source="sync"` already explains
   the absence, which is BIO-acceptable for system events.

   View-based sites to update:
   - [wies/core/services/users.py:95, 143](wies/core/services/users.py#L95)
   - [wies/core/services/placements.py:179](wies/core/services/placements.py#L179)
     (CSV import — has request)
   - [wies/core/views.py:578, 1586, 2135, 2379, 2766, 2801, 2837](wies/core/views.py#L578)

5. **AuthEvent.** Mirror the same `ip` + `user_agent` keys into the
   `context` JSONField at the two call sites:
   - [wies/rijksauth/auth_backend.py:25](wies/rijksauth/auth_backend.py#L25) (login fail)
   - [wies/rijksauth/views.py:55](wies/rijksauth/views.py#L55) (login success)

6. **UI exposure.** Do NOT show IP or User-Agent in the user-facing
   event list. Same rationale as `user_email` (kept out of UI for
   GDPR, see comment at
   [wies/core/models.py:256](wies/core/models.py#L256)). Available
   via Django admin / DB query for security incident response only.

7. **Document in `docs/beheer.md` §4 (Beveiliging).** One paragraph:
   what is logged (event, actor, timestamp, IP, User-Agent, result),
   that IP is read from the ODCN-managed proxy and therefore not
   client-spoofable, and the explicit caveat that "device" is
   approximated by IP + User-Agent because the web context offers no
   stronger identifier.

8. **Changelog.** Add a bullet to `CHANGES.md` under `## unreleased`
   referring to the PR (per project convention).

## Critical files

- `wies/core/views.py` — add `debug_request_meta` view (Phase 0, temporary)
- `wies/core/urls.py` — register the debug URL (Phase 0, temporary)
- `wies/core/jinja2/debug_request_meta.html` — new template (Phase 0, temporary)
- `wies/core/utils/request_meta.py` (new)
- `wies/core/services/events.py` — add `request` kwarg
- `wies/rijksauth/auth_backend.py`, `wies/rijksauth/views.py` — pass IP/UA into `AuthEvent.context`
- `wies/core/views.py`, `wies/core/services/users.py`, `wies/core/services/placements.py` — pass `request=request`
- `config/settings/base.py` + `config/settings/production.py` — `TRUSTED_PROXY_HOPS`
- `docs/beheer.md` — BIO logging paragraph
- `CHANGES.md`

## Verification

- Unit test for `get_client_ip`:
  - `TRUSTED_PROXY_HOPS=0` returns `REMOTE_ADDR` even when
    `X-Forwarded-For` is set (proves spoofing isn't honoured in dev).
  - `TRUSTED_PROXY_HOPS=1` with `X-Forwarded-For: 1.1.1.1, 2.2.2.2`
    returns `2.2.2.2` (rightmost-trusted), NOT `1.1.1.1`
    (client-supplied).
  - Missing header falls back to `REMOTE_ADDR`.
- Integration test: log in via `self.client.force_login(...)`,
  trigger one create + one update, assert the resulting `Event.context`
  contains `ip` and `user_agent`.
- Manual: hit the deployed test environment, perform an edit, verify
  in the DB that `context["ip"]` matches the developer's egress IP and
  not an internal cluster IP (sanity check the hop count).
- `just test` green before merge.

## Determining `TRUSTED_PROXY_HOPS`

Answered empirically via the Phase 0 debug endpoint rather than by
asking ODCN. Procedure:

1. Deploy Phase 0.
2. From your laptop, run `curl ifconfig.me` — record your public IP.
3. Open `/beheer/debug/request-meta/` in your browser (must be logged
   in as staff).
4. Find your public IP in the split `X-Forwarded-For` list.
5. `TRUSTED_PROXY_HOPS` = (number of entries after your IP) + 1.
   Equivalently: the index-from-the-right of your IP. If your IP is
   at `[-2]`, set `TRUSTED_PROXY_HOPS=2`.
6. Set the env var in production, redeploy, verify the next event's
   `context["ip"]` matches your public IP.
7. Remove (or `DEBUG`-gate) the debug endpoint in a follow-up PR.

Wrong value has real consequences: too low and we trust a
client-supplied entry (the spoofing risk the blog posts warn about);
too high and we log an internal cluster IP instead of the real
client. Until step 6, the env var stays unset → production behaves as
today (no IP logged; feature effectively dark-shipped).
