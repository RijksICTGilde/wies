# ODI Start Page — testing end to end

What's needed to exercise the start page (`/odi-startpagina/`) at each level, from "just the code"
to "the full publish flow against real infrastructure".

## Serving side — fully testable now

After the local MinIO dev loop landed, no external dependencies are needed to
test **reading/serving** articles:

```
just setup   # brings up MinIO, seeds a dummy site (startpage_seed_dummy)
just up
```

Then log in and browse:

- `/odi-startpagina/` — the site homepage (dummy root `index.html`, streamed from MinIO)
- `/odi-startpagina/kennisbank/` — a dummy article index (streamed as `text/html`)
- `/odi-startpagina/css/app.css` — a dummy asset (served as `text/css`)

Re-seed at any time with `docker compose run --rm django python manage.py startpage_seed_dummy`. Inspect the bucket in the MinIO console
at `http://localhost:9001` (`minioadmin` / `minioadmin`): bucket `wies`,
objects under `startpage/`. There is one live copy of the site; seeding or
publishing replaces it.

Verified behaviour (real Django + real MinIO): logged-out request → redirect to
`/inloggen/`; homepage (root) → 200 `text/html`; article → 200 `text/html` with
`Cache-Control: private, no-store`; asset → 200 `text/css` with an `ETag` and
`Cache-Control: private, no-cache`, and 304 on a reload; a pretty URL without a
trailing slash → 302 to its `/`-suffixed form; unknown path → 404; any method
other than GET → 405.

Automated coverage: `just test django` runs `wies/startpage/tests/` (catch-all auth
gate, homepage + article serving, pretty-URL resolution, traversal rejection,
publish service with mocked GitHub + MinIO, staff gate).

## Publish side — needs a token

The publish button (staff-only) enqueues the `startpage_publish` background job, which
pulls the **latest GitHub release artifact** from the content repo, unpacks it,
and replaces the site under `startpage/` with it: new files are uploaded (HTML
last), then objects the release no longer contains are deleted. There is no
versioning in the bucket; to roll back, publish a new release upstream.

The archive is not trusted blindly: at most 200 MB to download, 10,000 entries
and 500 MB unpacked, and only known web file types are published (see
`PUBLISHABLE_SUFFIXES` in `wies/startpage/publish.py`). Dotfiles and other types
are skipped; the task result reports how many, the worker log names them.

The content repo is `DigiGilde/odi-startpagina`, private. Its CI attaches the
built site as a `.tar.gz` release artifact on every merge to `main`.

- **A GitHub read token** able to download the repo's release artifacts. The
  repo is private, so this is required: without it the download 401s.
  - Local: set `STARTPAGE_CONTENT_GITHUB_TOKEN` in `.env.worker` (see
    `.env.worker.example`). The repo defaults to `DigiGilde/odi-startpagina`;
    set `STARTPAGE_CONTENT_GITHUB_REPO` there only to override it.
  - A fine-grained token with `Contents: read` on that one repo is enough.
    Resource owner must be DigiGilde, and an org owner approves it.
  - Production: provision the token as a ZAD secret on the `worker` component.
    `STARTPAGE_CONTENT_GITHUB_REPO` only needs setting to override the default.

Verified end-to-end on 6 October 2026: the button fetched release `build-2` and
published 339 objects to MinIO, and `/odi-startpagina/` served the site with its
assets.

Without the token configured, the button enqueues the job but `startpage_publish` fails
its config check with a clear message. The local loop uses `startpage_seed_dummy` as a
stand-in: it exercises the identical upload path, so the only piece
not tested against reality is the GitHub download + unpack step — which is covered
by mocked tests in `wies/startpage/tests/test_publish.py`.

**Summary:** serving is fully testable today; the full publish flow becomes
testable once the token is configured.

## Production checklist (platform team)

- Attach a MinIO Object Storage service to both the ZAD `frontend` and `worker`
  components. ZAD injects `OBJECT_STORE_HOST`, `OBJECT_STORE_PORT`,
  `OBJECT_STORE_USER`, `OBJECT_STORE_PASSWORD`, `OBJECT_STORE_BUCKET_NAME` and
  `OBJECT_STORE_REGION`; the app reads those directly (no remap). The endpoint URL
  is composed from host+port — set `OBJECT_STORE_SCHEME=https` if the endpoint is
  TLS (default `http`). The web reads the site, the worker reads + writes/publishes,
  so both components need the service.
- GitHub read token for the private content repo's release artifacts, as a ZAD
  secret on the `worker` component (`STARTPAGE_CONTENT_GITHUB_TOKEN`; only needed once the
  repo is private).
