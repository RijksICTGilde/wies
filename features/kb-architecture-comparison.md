# ODI Knowledge Base — Architectural Decision Comparison

A private, SSO-gated knowledge base: articles authored as Markdown in a **private
git repo**, built to static HTML by **Hugo in GitHub Actions**, readable only by ODI
staff. The build pipeline is fixed; this document works through the _serving and access_
architecture — every fork we considered, both sides, and why the chosen option won.

Wies is the relevant prior art: it already solves ODI SSO auth via a clean, reusable
Django app (`rijksauth`), deploys to the **ZAD** managed container platform (image →
private registry → ZAD runs it), runs a **`db_worker`** background-task process, and has
a **MinIO** bucket and persistent-volume storage available. Wies's repo is **open source**;
the article content is **not**.

---

## Decision 1 — Separate service vs. app inside Wies

**The question:** is the KB its own Django project/repo/deployment, or another Django app
inside the existing Wies codebase?

|                              | Separate service                                                  | App inside Wies (`wies/kb/`)                                  |
| ---------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------- |
| Reuse `rijksauth`            | Copy it in                                                        | Import it directly                                            |
| User list / `auth_user`      | **Shared DB** → migration guard, drift guard, co-upgrade coupling | One DB, one model, one migration owner — **nothing to guard** |
| `no_access` view + templates | Reimplement (they live in `wies.core`, not `rijksauth`)           | Reuse as-is                                                   |
| Release cadence              | Independent                                                       | Coupled to Wies                                               |
| Blast radius                 | Isolated process                                                  | A KB bug is a Wies-deployment bug                             |

**Parts considered:** the auth reuse story, the cost of sharing one Postgres between two
independently-migrating Django apps, and how independent the KB's releases/failures need
to be.

**Why app-inside-Wies wins:** the _only_ advantage of a separate service is independence
— independent deploys and an isolated blast radius. For an internal, ODI-sized tool, that
independence was judged **not worth its price**. And the price is steep: two Django apps on
one `auth_user` table forces a migration-ownership guard, a schema-drift guard, and a
permanent "KB must upgrade when Wies changes `rijksauth.User`" coupling that _no packaging
trick removes_ (sharing a table inherently couples the schema; only _not_ sharing it would
sever that). Collapsing to one app deletes that entire category of problem: one database,
one `User` definition, `rijksauth` imported not copied, and the existing `no_access`
view/templates reused. **The separate-service plan was ~80% shared-DB machinery that the
app-in-Wies approach simply never incurs.**

**What we accept:** a KB serving bug runs in the Wies process, and the KB ships on Wies's
cadence. Mitigated by keeping the KB app dependency-light. Reversible later if ODI ever
needs the KB to outlive Wies — but not free to reverse, so it's a deliberate today-choice.

---

## Decision 2 — Where the built HTML lives at runtime

**The question:** the compiled article HTML is sensitive (must never be public) and the
Wies repo is open source. Where does it physically live so the running app can serve it?

Three candidates: **baked into a container image**, a **persistent volume**, or an
**object store (MinIO)**.

|                                 | Baked into image                      | Persistent volume                         | MinIO bucket                |
| ------------------------------- | ------------------------------------- | ----------------------------------------- | --------------------------- |
| Publish = redeploy?             | **Yes** — rebuild + redeploy per edit | No                                        | No                          |
| New dependency                  | none                                  | none (`FileResponse`)                     | `boto3`                     |
| Multi-replica safe?             | yes                                   | ⚠️ `ReadWriteOnce` mounts to one pod only | ✅ native                   |
| Independent versioning/rollback | no                                    | manual                                    | ✅ free (object versioning) |
| Fits open-source repo           | yes (private registry)                | yes                                       | yes                         |

**Parts considered:** how often articles change (edit cadence), whether Wies runs one or
many `web` replicas, whether content should version/roll back independently of Wies deploys,
and what new dependencies/infra each option drags in.

**Why MinIO wins — two eliminations then a decider:**

1. **Baked-into-image is eliminated by edit cadence.** Articles change frequently, and
   baking them into the image means _every article edit is an image rebuild + ZAD redeploy_.
   That's backwards for a knowledge base, whose whole purpose is frequent content edits.
   (It was also the "third build target" the team wanted to avoid.)

2. **The choice narrows to volume vs. bucket, and replicas decide it.** In the _pull_ model
   (Decision 4), Wies itself is the writer — so the old objection to volumes ("CI can't
   write to them") disappears, and a single-replica volume would actually be _simpler_
   (no dependency, trivial `FileResponse`, atomic swap via directory rename). **But Wies
   runs, or may scale to, multiple `web` replicas.** A standard `ReadWriteOnce` block
   volume mounts to only one pod; a second replica can't read the articles. Escaping that
   needs `ReadWriteMany` (NFS-like) storage — a bigger, flakier platform ask. **MinIO is
   replica-agnostic by construction:** every pod talks to the same bucket. The moment
   more-than-one-replica is on the table, the volume's simplicity advantage evaporates and
   MinIO is the safer floor.

**Reinforcing (not deciding) factor:** MinIO gives object versioning for free, so a bad
article set can be rolled back without touching Wies — a "nice to have" the team flagged.

---

## Decision 3 — How bytes reach the reader (serving mechanism)

**The question:** a logged-in user requests an article; the app must (a) authorize and
(b) deliver the file. How is (b) done?

Three mechanisms surfaced across the discussion: **`X-Accel-Redirect` (nginx offload)**,
**presigned-URL redirect**, and **stream-through** (`boto3` → `StreamingHttpResponse`).

|                            | `X-Accel-Redirect`                                                         | Presigned redirect                                                                   | Stream-through (chosen)                   |
| -------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------- |
| Applies to MinIO?          | **No** — offloads _local files_ to nginx; can't hand off a remote S3 fetch | Yes                                                                                  | Yes                                       |
| Needs nginx in front?      | Yes (Wies has none today — pure gunicorn)                                  | No                                                                                   | No                                        |
| Bytes touch Django worker? | No                                                                         | No (bucket→browser direct)                                                           | Yes                                       |
| Trust boundary             | strong                                                                     | **weaker** — signed URL is a leakable bearer token; bucket must be browser-reachable | **strong** — user only ever talks to Wies |
| Complexity                 | proxy config + `internal` location                                         | URL signing + browser-reachable bucket                                               | ~15 lines, native Django                  |

**Parts considered:** whether nginx exists in front of Wies (it doesn't — the `web` target
runs gunicorn directly), whether the storage is local or remote, worker-occupancy cost, and
the security/trust boundary of each delivery path.

**Why stream-through wins:** two of the three options don't even fit the MinIO decision.
`X-Accel-Redirect` is a _local-file_ offload — it cannot delegate "fetch this object from a
remote bucket" to nginx, and Wies has no nginx anyway. The presigned redirect _works_ but
weakens the trust boundary (the signed URL is a bearer token, leakable via history/referrer
for its TTL, and requires the bucket to be reachable from users' browsers). **Stream-through
is native, simple, and airtight:** `boto3.get_object()` returns a `StreamingBody`, fed to
Django's `StreamingHttpResponse` via `iter_chunks` — the user only ever talks to Wies, memory
stays flat regardless of file size, and there's no proxy or signing to manage.

**What we accept:** the bytes pass through a gunicorn worker (Django is the proxy in the
middle), occupying a worker for the download's duration. **Irrelevant at this scale** —
HTML articles are kilobytes and the audience is internal. Streaming (not buffering) keeps
memory flat. If it ever mattered, the escape hatch is the **presigned-URL redirect** (not
nginx) — noted as a future lever, not built now.

---

## Decision 4 — How MinIO gets the built HTML (publish flow)

**The question:** Hugo builds the HTML in GitHub Actions. How does it end up in MinIO?

**Push vs. pull**, and if pull, triggered how.

|                             | Push (CI → MinIO)                    | Pull (Wies fetches) — chosen                                                  |
| --------------------------- | ------------------------------------ | ----------------------------------------------------------------------------- |
| Who holds infra credentials | **CI** needs MinIO write keys        | CI holds none; Wies holds a GitHub read token + MinIO keys                    |
| Trust boundary              | CI can write to your runtime storage | **CI never touches your infra** — it only publishes a GitHub release artifact |
| Publish is                  | automatic on merge                   | a deliberate, audited action                                                  |
| Moving parts                | fewer                                | a fetch/unpack/upload job                                                     |

**Parts considered:** who should hold credentials to production storage, whether publishing
should be an automatic or deliberate act, where CI can leave the artifact for Wies to reach,
and who actually publishes articles (a group separate from Wies admins).

**Why pull wins:** the team explicitly did **not** want CI pushing into their
infrastructure. Pull inverts the trust boundary so **CI holds zero credentials to runtime
storage** — Hugo CI just attaches the built site as a **GitHub release artifact** (something
it already has rights to), and Wies pulls it on demand. Publishing becomes a deliberate,
auditable action rather than an automatic side effect of merge — a good fit for a
governance-sensitive context.

**Sub-decision — pull source:** _GitHub release artifact_ over _Wies builds Hugo itself_.
Making Wies `git pull` the content repo and run Hugo server-side would put a build toolchain
and repo credentials inside the web app — heavier and worse-isolated. The release artifact
keeps Wies's job to "download a tarball, unpack, upload," nothing more.

**Sub-decision — trigger:** _manual button now, webhook-ready later_. Because article
editors are a **separate group** from Wies admins, a purely manual button risks an
editor→admin handoff on every publish. The resolution: **build the sync as a background job
now, exposed via a role-gated manual button**, but design the job so a future GitHub
"release published" **webhook can trigger the same job** with no rework — still a pull (no
CI credentials), just auto-triggered. Ship the simple thing; don't foreclose automation.

**Implementation reuse:** the sync runs as a background job on Wies's existing **`db_worker`**
via the `TaskCommand` base (`wies/core/management/task.py`) — download release tarball →
unpack → upload objects to MinIO under a **new prefix**, then **flip a pointer** so readers
never see a half-written site (atomic publish). Gated by an existing role in
`wies/core/roles.py` (e.g. Beheerder).

---

## Decision 5 — How it's reached (URL / host) and when

**The question:** the KB is meant to be a **hub / front door** (it links out to the KB, Wies,
and other ODI tools). What URL do people visit, and does it need its own host?

Candidates: a **path under Wies** (`wies.rijksorganisatieodi.nl/start/`), a **separate
subdomain** (`start.rijksorganisatieodi.nl`), or a **redirect** trick to fake one from the
other.

|                               | Path under Wies                   | Subdomain `start.`                        | `start.` → redirects to path            |
| ----------------------------- | --------------------------------- | ----------------------------------------- | --------------------------------------- |
| Setup now                     | ~1 line (`include`)               | DNS + TLS + ingress + host routing + CSRF | DNS + TLS + ingress (host must resolve) |
| Auth / cookie / Keycloak work | **none** (same origin)            | host-scoped cookies, redirect-URI add     | none saved — still same-origin app      |
| Front-door framing            | ❌ reads as a Wies sub-feature    | ✅ true front door                        | ❌ flips to `wies/…` on landing         |
| Migration cost later          | promote losslessly (config + 301) | already there                             | pointless middle ground                 |

**Parts considered:** whether this is the org's front door or reference material Wies users
read; whether it will link out to many tools (a hub); whether a redirect can avoid subdomain
setup; who governs the domain's subdomains (cookie-scope safety); and how soon the subdomain
infra can actually be provisioned.

**Why the positioning answer is "subdomain," but the _sequencing_ answer is "path first":**

- **Positioning:** it's a hub that links out to Wies and other tools, so it _cannot_
  canonically live at `wies.../start/` — a hub can't be a sub-path of one of the tools it
  points at (that inverts the hierarchy). So `start.` is the eventual right home.
- **The redirect trick doesn't help:** a redirect can't avoid the subdomain's cost, because
  the host you redirect to/from must _resolve first_ — and standing up a host **is** the
  DNS + TLS + ingress work. Redirects move URLs around after both hosts exist; they don't
  conjure a host into being. Ruled out.
- **Sequencing wins on availability:** the subdomain needs platform infra that "may take a
  while." A **path is same-origin as Wies**, so it needs _zero_ new auth/cookie/host/Keycloak
  work and ships immediately. Crucially, **promotion is lossless**: the app code is identical
  (URLs kept relative, links via `reverse()`), so moving to `start.` later is config + a
  **301** from `/start/…`, no rewrite and no broken bookmarks. So iteration 1 ships at
  `wies.../start/`; the subdomain is a documented future promotion.

**Two corrections this decision forced (both making the design _simpler/safer_):**

1. **Cookies stay host-scoped — never a domain-wide `.rijksorganisatieodi.nl` cookie.** We do
   not govern every subdomain under that domain, so a domain-wide session cookie would be sent
   to hosts we don't control → session-hijack risk. Cross-host SSO instead comes from
   **Keycloak** (a user with a Keycloak session hitting `start.` does one silent OIDC
   round-trip, no password prompt). The shared identity lives at the IdP, not in a broadcast
   cookie. (Moot for the path — same origin — but decisive for the subdomain.)
2. **No new Keycloak client is needed.** `rijksauth`'s `login()` derives the redirect URI from
   the _request host_ (`request.build_absolute_uri(reverse_lazy("auth"))` in
   `wies/rijksauth/views.py`), so the one shared ZAD Keycloak client serves both hosts — the
   only change is **adding `start./auth/` to that client's allowed redirect-URI list**. (I
   initially claimed a separate client was required; the code proved otherwise.) This depends
   on the ingress forwarding the real `Host` header — the single integration risk to verify.

---

## Decisions that were near-automatic (recorded for completeness)

**Reuse `rijksauth` vs. build auth fresh.** No contest — `rijksauth` is a clean, reusable
OIDC app with no imports from `wies.core`, and its "user must pre-exist in the DB" model
_is_ the ODI allow-list. Building auth again would re-solve a solved problem and risk
diverging from Wies's SSO behavior.

**Serve through the app (auth-gated) vs. a public CDN/bucket.** The entire requirement is
"not public," so the static output can never be served by an unauthenticated CDN or by
WhiteNoise (which in Wies runs _before_ auth middleware and is public by design). Everything
must pass the KB view behind `LoginRequiredMiddleware`. This was a constraint, not really a
choice.

---

## The resulting architecture (one line per layer)

- **App:** `wies/kb/` inside Wies — imports `rijksauth`, reuses `wies.core`'s `no_access`,
  gated by `LoginRequiredMiddleware`.
- **URL:** iteration 1 at `wies.rijksorganisatieodi.nl/start/` (a path); promote to the
  `start.rijksorganisatieodi.nl` subdomain later (config + 301, lossless).
- **Storage:** MinIO bucket (replica-safe, free versioning).
- **Serving:** `boto3.get_object()` → `StreamingHttpResponse` — no nginx, no volume, no
  `X-Accel-Redirect`.
- **Publish:** Hugo CI → GitHub release artifact → role-gated button → `db_worker` job pulls,
  unpacks, uploads to a new MinIO prefix, flips a pointer. Webhook-triggerable later.
- **New dependency:** `boto3`. **New ZAD secrets:** MinIO endpoint + keys, GitHub read token
  for the private content repo.

## Open items to confirm with the platform team

- MinIO endpoint reachable from ZAD components; credentials provisioned as ZAD secrets.
- GitHub read token scope for the private content repo (release-artifact download) from ZAD.
- Exact `web` replica count / scaling intent (reconfirms Decision 2, though MinIO is safe
  either way).
- _(Deferred to subdomain promotion — not iteration 1)_ DNS + TLS + ingress for `start.`;
  ingress must forward the real `Host` header; add `start./auth/` to the shared Keycloak
  client's redirect-URI list; keep cookies host-scoped.
