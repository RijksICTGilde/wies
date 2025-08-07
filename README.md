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
