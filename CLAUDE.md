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

### Testing

`pytest` (config in [`pytest.ini`](pytest.ini), tests in [`test/`](test/)). Run from the repo root: `pytest`.

**`test/conftest.py`'s `app`/`dbapp` fixtures deliberately do NOT call `rrwebapp.create_app()`** — they build a bare `Flask('rrwebapp')` with just `db.init_app(app)`, no blueprints/extensions registered. This is required, not a style choice: `create_app()` unconditionally registers the `admin` blueprint (`__init__.py` → `views/admin/__init__.py` → `from . import member` → `tasks.py` → `celery.py`), and [`celery.py`](app/src/rrwebapp/celery.py) reads `/config/<APP_NAME>.cfg` and two Docker-secrets files (`/run/secrets/appdb-password`, `/run/secrets/rabbitmq-app-password`) **unconditionally at module import time** — paths that only exist inside the container. There's currently no way to import anything under `rrwebapp.views.admin` (which is where most view-function code lives, including `results.py`) outside Docker without hitting this. `contracts`/`members` never hit it because neither uses Celery at all — this is rrwebapp-specific. Fixing it properly would mean deferring `celery.py`'s config read into a function instead of module level; not done here since it's a change to production task-dispatch code, out of scope for adding a test harness.

**Practical implications for writing new tests:**
- A bare `Flask` + `db.init_app()` is enough for model-level tests and for testing free functions that don't need the full app. Prefer putting DB-credential/config-reading helpers in a plain top-level module (not inside `views/admin/`) specifically so they stay importable/testable without tripping the `celery.py` chain.
- Anything that genuinely needs the full app (routing, Flask-Security, blueprint-registered views) can't be tested this way yet — that needs the `celery.py` fix above first.

`APP_NAME`/`APP_VER` must also be set *before* `rrwebapp` is imported at all, regardless of the above — [`__init__.py:35`](app/src/rrwebapp/__init__.py#L35) reads `environ['APP_NAME']` at module import time, and [`version.py:3`](app/src/rrwebapp/version.py#L3) reads `environ['APP_VER']` the same way. Both are normally supplied by Docker Compose's `.env`; `conftest.py` sets defaults via `os.environ.setdefault(...)` as its first lines, before any `rrwebapp` import. Get the ordering wrong and every test errors at collection, not just the ones touching those modules.

Separately, `settings.Testing` was also given `APP_LOUTILITY`, `EXCEPTION_EMAIL`, and the three `SECURITY_EMAIL_SUBJECT_*` keys it was missing (see [`settings.py`](app/src/rrwebapp/settings.py)) — in real deployments these come from `config/<app>.cfg`'s `[app]` section, which `Testing` doesn't load, but `create_app()` reads them unconditionally during `setlogging()`/security-email setup regardless of `DEBUG`/`TESTING`. Not currently exercised by the test suite (since it avoids `create_app()`, per above) but left in place since it's a real, correct gap-fix — needed the moment anything does call `create_app(Testing)`, e.g. once the `celery.py` fix above lands.

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

### Static JS Assets

JS assets are **not** served from the repo's `app/src/rrwebapp/static/js/` directory. That path is shadowed by a Docker volume mount defined in `docker-compose.yml`:

```yaml
- ${JS_COMMON_HOST}:/app/${APP_NAME}/static/js:ro
```

`JS_COMMON_HOST` is set in `.env`:
```
JS_COMMON_HOST="C:\Users\lking\Documents\Lou's Software\operational\js-common"
```

This shared `js-common` directory contains all versioned JS bundles (jQuery, DataTables, yadcf, etc.) used across multiple apps. Editing files under `static/js/` in the repo has no effect on the running container — changes must be placed in `js-common`.

The yadcf development repo lives at `C:\Users\lking\Documents\Lou's Software\projects\yadcf\yadcf\`. After editing yadcf there, the built file must be copied into `js-common` under the appropriate versioned directory (e.g., `js/yadcf-<version>/`) for it to be picked up by the app.

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

### Custom DataTables Buttons

Custom buttons on `CrudApi` views follow a two-file JS pattern:

- **[`static/beforedatatables.js`](app/src/rrwebapp/static/beforedatatables.js)** — define button handler functions/variables that must exist before DataTables initialises. A button's `action` key in Python is a string expression that loutilities' `datatables.js` `eval()`s at init time; the result must be a function `(e, dt, node, config)`. The convention is a top-level `var foo_button = function(url) { return function(e, dt, node, config) {...}; }` so the eval'd call `foo_button("<url>")` returns the handler.

- **[`static/afterdatatables.js`](app/src/rrwebapp/static/afterdatatables.js)** — per-path `afterdatatables()` hook (guarded by `location.pathname.includes(...)`) for post-init work such as disabling buttons until a row is selected and initialising `SaEditor` instances.

Custom read-only API endpoints on the `admin` blueprint use `flask.views.MethodView` with the `@apimethod` decorator from `loutilities.tables`. The view must implement `permission()` (returns bool) and `rollback()`, then `get()`/`post()` methods decorated with `@apimethod`.

### Age Grade Models

Three related models in [`model.py`](app/src/rrwebapp/model.py) (`AgeGradeTable` → `AgeGradeCategory` → `AgeGradeFactor`). Distance is stored as `dist_mm = int(dist_km * 1_000_000)` (i.e. millimetres). `AgeGradeCategory.oc_secs` holds the open-class (world record) performance in seconds for that distance.

### RaceResult Duplicate Prevention

`RaceResult` declares `UniqueConstraint('runnerid', 'runnername', 'raceid', 'seriesid', 'club_id')`, but the tabulate flow (`AjaxTabulateResults` in [`results.py`](app/src/rrwebapp/views/admin/results.py)) never sets `runnername`, so it's always `NULL`. SQL unique constraints treat `NULL` as distinct from `NULL`, so this constraint does **not** actually prevent duplicate `RaceResult` rows. The real defense is preventing duplicate tabulate requests client-side: the shared `ajax_update_db_noform()` helper in [`RaceResults.js`](app/src/rrwebapp/static/RaceResults.js) does not disable the triggering button itself, so a fast double-click can fire two overlapping POSTs that both pass the "results already exist" check before either commits, doubling every result. The Tabulate button in [`editparticipants.js`](app/src/rrwebapp/static/editparticipants.js) shows the mitigation pattern: disable the button synchronously in the click handler (before the async request fires), and re-enable it via a document-level `ajaxComplete` listener filtered on the endpoint URL — `ajax_update_db_noform`'s own `callback` only fires on success, so it can't be used to re-enable after a failure or overwrite-confirmation response.
