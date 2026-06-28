# Tenant Management Service — Internal Reference

Engineering documentation for the Tenant Management Service. Covers API contracts, business logic, functional and non-functional requirements, and tenant lifecycle design.

| Property | Value |
|---|---|
| Port | `8000` |
| API prefix | `/api/v1` |
| Database | PostgreSQL (`nutratenant_tenant`) |
| Runtime | Python 3.11.9 · FastAPI · SQLAlchemy 2 async |

---

## Navigation

- [API Reference](api-reference.md) — all 18 endpoints with descriptions
- [Functional Requirements](planning/FunctionalRequirements.md)
- [Non-Functional Requirements](planning/NonFunctionalRequirements.md)
- [Business Logic](planning/BusinessLogic.md)
- [Tenant States](planning/TenentStates.md)
- [Tenant Lifecycle](planning/TenentLifecycle.md)

---

## Architecture

```
api/ → services/ → domain/ ← infrastructure/
```

The `api` layer translates Pydantic schemas into domain commands. Services accept only domain command objects — no Pydantic imports cross into the service layer. Infrastructure (repositories, DB engine) depends on domain models, never on API schemas.

### Layer map

| Layer | Path | Responsibility |
|---|---|---|
| API | `app/api/v1/` | Route handlers, request/response schemas |
| Services | `app/services/` | Business orchestration, state transitions |
| Domain | `app/domain/` | Commands, enums, events, exceptions |
| Infrastructure | `app/infrastructure/` | ORM models, repositories, DB engine |

---

## Quality Gate

```bash
bash scripts/lint.sh   # ruff + mypy + pylint R0801 + pytest (131 tests)
```
