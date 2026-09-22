# Repository Guidelines

## Project Structure & Module Organization

This repository is a Django REST Framework API organized by domain:

- `gateway/`: project settings, root URLs, ASGI/WSGI entry points, and API router.
- `accounts/`: custom `User` model, role permissions, serializers, and admin setup.
- `customers/`: `Customer` and client-user profile models and endpoints.
- `billing/`: invoice, payment, and transaction models and endpoints.
- `<app>/migrations/`: committed database schema migrations.
- `schema.yml`: generated OpenAPI specification; update it when API contracts change.
- `manage.py`: Django command entry point.

Tests currently live in each app's `tests.py`. If a suite grows, replace it with a `tests/` package grouped by feature.

## Build, Test, and Development Commands

Activate the Windows virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
```

- `python -m pip install -r requirements.txt`: install pinned dependency ranges.
- `python manage.py migrate`: apply database migrations.
- `python manage.py runserver`: run the local server at `127.0.0.1:8000`.
- `python manage.py test`: run all Django tests.
- `python manage.py check`: validate configuration and model definitions.
- `python manage.py makemigrations`: generate migrations after model changes.
- `python manage.py spectacular --file schema.yml --validate`: refresh and validate OpenAPI documentation.

## Coding Style & Naming Conventions

Use four-space indentation and follow PEP 8. Use `snake_case` for variables and functions, `PascalCase` for classes, and singular model names (`Invoice`, not `Invoices`). Keep business logic in the owning domain app. Serializers validate API input; models enforce persistent invariants with constraints where practical. No formatter or linter is configured, so keep imports grouped as standard library, third-party, then local modules.

## Testing Guidelines

Tests use Django's `TestCase` and REST Framework test utilities when exercising endpoints. Name test classes after the unit under test and methods as `test_<expected_behavior>`. Add regression tests for validation, permissions, customer scoping, and billing state changes. Run `python manage.py test` before every pull request.

## Commit & Pull Request Guidelines

History currently contains only an initial commit, so no established convention exists. Use concise, imperative messages such as `Add invoice payment validation`. Pull requests should explain the change, identify schema or migration effects, link relevant issues, and include test results. Commit generated migrations and an updated `schema.yml` with API changes.

## Security & Configuration

Never commit secrets, tokens, `.env`, `.venv`, or local SQLite databases. Configure `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, and `DJANGO_ALLOWED_HOSTS` through environment variables. Preserve admin-only writes and customer-scoped reads when adding endpoints.
