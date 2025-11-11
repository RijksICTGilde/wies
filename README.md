# wies (prototype)
Interne tool voor overzicht wie, waar, wat, wanneer

## Prerequisites
- docker
- just
- uv
- npm

## Setup

Setting up the system. Can also be used to clean up current state.
- installs dependencies
- sets up database from scratch, including source data
- creates example .env file if non-existent (make sure to add OIDC credentials yourself)

```
just setup
```

## Start

Starts up current system
- Applies hanging data migration if available

```
just up
```

### Other commands

django manage.py command

```
just manage [...]
```

### Special URLs
The following URLs are not linked through the UI
- /admin/
- /admin/db/: for dropping db and loading dummy data

### Release
- everything in main
- change "unreleased" in CHANGES to date + commit & push
- tag with date using "yyyy-mm-dd": e.g. `git tag -a 2025-08-18 -m "2025-08-18"`
- push tag: `git push --tags`
- (CI produces image)

### Testing
Run all tests
```
just manage test wies
```
