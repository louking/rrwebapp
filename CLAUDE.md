# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**scoretility** (repo: `rrwebapp`) is a Flask-based web application for managing race results and series standings for running clubs. It is multi-club enabled, supporting separate membership, races, divisions, series, results, and standings per club.

## Architecture

### Tech Stack
- **Backend**: Python 3.12, Flask 3.0.3 with SQLAlchemy 2.x ORM
- **Database**: MySQL 8.0.40 (SQLite in-memory for testing)
- **Task Queue**: Celery 5.4 with RabbitMQ for async results processing
- **Frontend**: Server-rendered Jinja2 with DataTables, Flask-Assets for JS/CSS bundling
- **Auth**: Flask-Security-Too with Flask-Principal for role-based access control

### Application Structure

The main package lives in [app/src/rrwebapp/](app/src/rrwebapp/):

- **[`__init__.py`](app/src/rrwebapp/__init__.py)** — `create_app()` factory: initializes Flask extensions, registers blueprints, sets up Jinja loaders for `loutilities` templates
- **[`model.py`](app/src/rrwebapp/model.py)** — All SQLAlchemy ORM models: `Club`, `Runner`, `Race`, `RaceResult`, `ManagedResult`, `Series`, `RaceSeries`, `Divisions`, `User`, `Role`, etc.
- **[`settings.py`](app/src/rrwebapp/settings.py)** — Config classes: `Config` (base), `Testing` (SQLite in-memory), `Development`/`Production` (MySQL via `/run/secrets/appdb-password`)
- **[`crudapi.py`](app/src/rrwebapp/crudapi.py)** — `CrudApi` class wrapping `loutilities.tables.DbCrudApi` for DataTables CRUD; most admin views extend this
- **[`accesscontrol.py`](app/src/rrwebapp/accesscontrol.py)** — Flask-Principal permissions: `UpdateClubDataPermission`, `ViewClubDataPermission` scoped to `session['club_id']`
- **[`tasks.py`](app/src/rrwebapp/tasks.py)** — Celery tasks for async race results import/processing
- **[`celery.py`](app/src/rrwebapp/celery.py)** — Celery app configuration

### Blueprints

- **`admin`** (`/admin` prefix) — [app/src/rrwebapp/views/admin/](app/src/rrwebapp/views/admin/): club, member, race, results, resultsanalysis, standings, agegrade, location, services, uploads, userrole, debug
- **`frontend`** (no prefix) — [app/src/rrwebapp/views/frontend/](app/src/rrwebapp/views/frontend/): index, userviews, sysinfo

### External Results Import Modules

Race results can be imported from multiple sources:
- [`raceresults.py`](app/src/rrwebapp/raceresults.py) — local file parsing (Excel/CSV/TXT)
- [`athlinksresults.py`](app/src/rrwebapp/athlinksresults.py) — Athlinks API
- [`ultrasignupresults.py`](app/src/rrwebapp/ultrasignupresults.py) — Ultrasignup
- [`runningaheadresults.py`](app/src/rrwebapp/runningaheadresults.py) — RunningAHEAD

### Key Dependencies

- **`loutilities`** (sibling repo at `../loutilities/loutilities`) — provides `DbCrudApi` (DataTables CRUD base class), Flask helpers, age grade calculations, `timeu` utilities, and JS/CSS table assets; templates are loaded via `PackageLoader('loutilities', 'tables-assets/templates')`
- **`runtilities`** — race result parsing utilities

## Development

### Running Locally

Development uses Docker Compose. The `.env` file controls all configuration:

```bash
# Start all services (db, rabbitmq, app, web, celery, crond, phpmyadmin)
docker compose up

# The .env COMPOSE_FILE already includes docker-compose.dev.yml which mounts
# ./app/src as /app in the container for live reload
```

The dev compose file mounts `./app/src` into the container so code changes take effect without rebuilding. The app runs on port `APP_PORT=8004` (configurable in `.env`).

### Docker Debug Variants

```bash
# Debug the app container
docker compose -f docker-compose.yml -f docker-compose.debug.yml up app

# Debug celery worker
docker compose -f docker-compose.yml -f docker-compose.debug-celery.yml up celery
```

### Database Migrations

Migrations use Alembic via Flask-Migrate. The `dbupgrade_and_run.sh` script in the container runs `flask db upgrade` automatically on startup.

To create a new migration after changing models:
```bash
docker compose exec app flask db migrate -m "description"
docker compose exec app flask db upgrade
```

### Configuration

App configuration is read from `/config/rrwebapp.cfg` (mounted into container from `./config/`). Secrets (database password, RabbitMQ password) are mounted as Docker secrets at `/run/secrets/`.

Environment variables prefixed with `FLASK_` are automatically loaded into `app.config` (without the prefix) via `app.config.from_prefixed_env(prefix='FLASK')`.

Results analysis debugging is controlled via `.env`:
- `RESULTS_ANALYSIS_DEBUG` — all services
- `RESULTS_ANALYSIS_DEBUG_RA` — RunningAHEAD only
- `RESULTS_ANALYSIS_DEBUG_ATHLINKS` — Athlinks only
- `RESULTS_ANALYSIS_DEBUG_ULTRASIGNUP` — Ultrasignup only

### Deployment

Uses Fabric for remote deployment:
```bash
fab -H <target-host> deploy prod
fab -H <target-host> deploy sandbox
fab -H <target-host> deploy --branchname=<branch> prod
```

Fabric pulls `docker-compose.yml` from GitHub and runs `docker compose pull && docker compose up -d` on the target host.

## Key Patterns

### Session State

`session['club_id']` and `session['year']` are used pervasively throughout views and models. The `getclubid` and `getyear` lambdas in `model.py` are convenience accessors for forms.

### CRUD Views

Most admin views extend `DbCrudApi` from `loutilities`. Views define column mappings, form fields, and permissions; the base class handles DataTables server-side processing, Editor integration, create/read/update/delete operations, and JSON responses.

### Celery Tasks

Two Celery queues exist:
- Default queue (`celery` service) — regular tasks, concurrency 1
- `longtask` queue (`celerylongtask` service) — long-running results imports, concurrency 1

Tasks are defined in [`tasks.py`](app/src/rrwebapp/tasks.py) and dispatched from results views.

### Access Control

Permissions are checked with Flask-Principal `Permission` objects. The club ID from `session['club_id']` scopes all data access — every query filters by club ID. Roles are `admin`, `viewer`, and `owner`.
