# FastAPI Production Master Skill & Best Practices

A practical guide to building scalable, secure, high-performance, and production-ready FastAPI applications.

---
- **Execution**: Run `/fastapi <service_name>`.
## 0: Organize the Project as Independent Services

As the application grows, organize it into **domain-oriented services**. Each service owns its APIs, business logic, models, repositories, schemas, tests, documentation, and TODOs.

### Recommended Project Structure

```text
.
├── Dockerfile
├── README.md
├── TODO.md                          # Auto-generated master TODO
├── pyproject.toml
├── uv.lock
├── alembic/
├── alembic.ini
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── router.py
│   │   ├── __init__.py
│   │   ├── v1/
│   │   └── v2/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   └── security.py
│   │
│   ├── domain/
│   │   ├── enums.py
│   │   ├── events.py
│   │   └── exceptions.py
│   │
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── notifications/
│   │   └── security/
│   │
│   ├── consumers/
│   │
│   ├── services/
│   │   │
│   │   ├── tenant_management/
│   │   │   ├── api/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   ├── validators/
│   │   │   ├── dependencies/
│   │   │   ├── events/
│   │   │   ├── tests/
│   │   │   ├── docs/
│   │   │   ├── README.md
│   │   │   └── TODO.md
│   │   │
│   │   ├── organization_management/
│   │   ├── iam/
│   │   ├── user_management/
│   │   ├── authentication/
│   │   ├── authorization/
│   │   ├── abac_policy_management/
│   │   ├── abac_policy_evaluation/
│   │   ├── tenant_isolation/
│   │   ├── audit_logging/
│   │   ├── observability/
│   │   ├── health_check/
│   │   └── seed_data/
│   │
│   └── shared/
│       ├── enums/
│       ├── constants/
│       ├── dto/
│       ├── pagination/
│       ├── validators/
│       └── utils/
│
├── scripts/
│   ├── bootstrap.sh
│   ├── lint.sh
│   ├── release.sh
│   ├── fix.sh
│   ├── test_db_connection.py
│   └── todo_manager.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── performance/
│
├── logs/
└── tmp/
```

### Standard Service Structure

Every service should follow the same layout.

```text
tenant_management/
│
├── api/
│   ├── router.py
│   ├── endpoints/
│   └── dependencies.py
│
├── models/
├── schemas/
├── repositories/
├── services/
├── validators/
├── dependencies/
├── events/
├── tests/
├── docs/
├── README.md
└── TODO.md
```

### Service Responsibilities

Each service should own:

* API routes
* Business logic
* Database models
* Repository layer
* Pydantic schemas
* Validation
* Dependencies
* Domain events
* Tests
* Documentation
* TODO list

Avoid placing unrelated business logic into another service.

### Shared Components

Only reusable, cross-cutting code belongs in shared locations.

Examples include:

* Common DTOs
* Pagination
* Generic validators
* Utility functions
* Shared enums
* Shared constants

Business-specific code should never live in shared modules.

### Documentation

Every service should include:

```text
README.md
```

Describing:

* Purpose
* Responsibilities
* API endpoints
* Dependencies
* Events
* Architecture

and

```text
TODO.md
```

Containing:

* Current tasks
* Planned work
* Technical debt
* Future enhancements

The project-level `TODO.md` should be generated automatically by aggregating all service TODO files:

```bash
python scripts/todo_manager.py --sync
```

### Development Workflow

For every new service:

1. Create the service directory.
2. Create the standard folder structure.
3. Write `README.md`.
4. Create `TODO.md`.
5. Register API routes.
6. Implement models.
7. Implement repositories.
8. Implement business services.
9. Implement schemas.
10. Implement validators.
11. Write unit and integration tests.
12. Register seed data.
13. Update documentation.
14. Synchronize the master TODO.

```bash
python scripts/todo_manager.py --sync
```

# 1. Concurrency Architecture & Async Rules

## Rule 1: Never Use `async def` for Blocking Operations

### Anti-Pattern

Running blocking operations inside an `async def` endpoint blocks the event loop and destroys concurrency.

Examples:

* `time.sleep()`
* `requests`
* Synchronous database drivers (`psycopg2`, `pymongo`)
* CPU-intensive operations

```python
@app.get("/users")
async def get_users():
    time.sleep(2)  # Blocks the event loop
```

### Production Practice

Use standard `def` for endpoints containing blocking code.

FastAPI automatically executes synchronous endpoints in a thread pool.

```python
@app.get("/users")
def get_users():
    time.sleep(2)
    return {"status": "ok"}
```

---

## Rule 2: Prefer Async-Compatible Libraries

When using `async def`, every I/O operation should also be asynchronous.

### Recommended Replacements

| Blocking Library | Async Alternative     |
| ---------------- | --------------------- |
| `time.sleep()`   | `asyncio.sleep()`     |
| `requests`       | `httpx.AsyncClient()` |
| `pymongo`        | `motor`               |
| `psycopg2`       | `asyncpg`             |
| SQLAlchemy Sync  | SQLAlchemy Async      |

Example:

```python
import asyncio
import httpx

@app.get("/external")
async def fetch_data():
    await asyncio.sleep(1)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://example.com")

    return response.json()
```

---

## Rule 3: Offload Heavy Computation

FastAPI excels at I/O-bound workloads, not CPU-bound workloads.

### Lightweight Tasks (<100 ms)

Can run directly inside endpoints under low traffic.

### Heavy ML Inference

Use dedicated inference servers:

* Triton Inference Server
* TensorFlow Serving
* TorchServe

FastAPI should focus on:

* Request handling
* Validation
* Routing

### Long-Running Tasks

Use a queue-based architecture:

```text
FastAPI
    ↓
RabbitMQ / Redis
    ↓
Celery Workers
```

Examples:

* Video processing
* Image manipulation
* Batch jobs
* Report generation

---

## Rule 4: Apply the Same Rules to Dependencies

Dependencies should follow the same concurrency rules.

### Use `def` When

* Calling blocking libraries
* Using synchronous database drivers

### Use `async def` When

* Using async libraries
* Performing lightweight work

### Avoid

* Heavy computations inside dependencies

---

# 2. Background Processing & Task Orchestration

## Rule 5: Use Background Tasks for Lightweight Work

FastAPI's `BackgroundTasks` is ideal for fire-and-forget operations.

Examples:

* Sending emails
* Analytics logging
* Notifications

```python
from fastapi import BackgroundTasks

@app.post("/register")
async def register(background_tasks: BackgroundTasks):

    background_tasks.add_task(send_email)

    return {"message": "User created"}
```

### Limitations

Do **not** use `BackgroundTasks` when you need:

* Guaranteed delivery
* Retries
* Persistence across crashes

For mission-critical tasks, use:

* Celery
* RabbitMQ
* Redis

---

# 3. Security, Hardening & API Edge Controls

## Rule 6: Disable API Documentation in Production

### Anti-Pattern

Leaving these publicly exposed:

* `/docs`
* `/redoc`
* `/openapi.json`

This reveals:

* Internal schemas
* Endpoint structures
* Experimental APIs

### Production Practice

```python
from fastapi import FastAPI
from core.config import settings

app = FastAPI(
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
)
```

---

# 4. Pydantic Architecture & Validation

## Rule 7: Create a Custom Base Model

Avoid inheriting directly from `BaseModel` everywhere.

Create a centralized application base model.

### Benefits

* Global configuration
* Alias generators
* Shared encoders
* Consistent serialization

Example:

```python
from pydantic import BaseModel

class AppBaseModel(BaseModel):

    class Config:
        populate_by_name = True
```

Common use cases:

* Snake case → camel case conversion
* `datetime` serialization
* `Decimal` conversion
* MongoDB `ObjectId` conversion

---

## Rule 8: Let FastAPI Build Response Models

### Anti-Pattern

```python
return UserResponse(
    id=user.id,
    name=user.name
)
```

### Production Practice

Return raw objects:

```python
return {
    "id": user.id,
    "name": user.name
}
```

FastAPI automatically:

1. Validates
2. Serializes
3. Builds the response model

---

## Rule 9: Keep Validation Inside Pydantic

### Anti-Pattern

```python
if age < 18:
    raise Exception()
```

inside route handlers.

### Production Practice

Use validators:

```python
from pydantic import BaseModel, field_validator

class UserCreate(BaseModel):

    age: int

    @field_validator("age")
    @classmethod
    def validate_age(cls, value):

        if value < 18:
            raise ValueError("Age must be at least 18")

        return value
```

Benefits:

* Cleaner routes
* Better OpenAPI docs
* Reusable validation logic

---

# 5. Dependency Injection & Resource Management

## Rule 10: Move Resource Validation Into Dependencies

Examples:

* Ownership checks
* Permission checks
* Record existence validation

Benefits:

* Reusability
* Cleaner endpoints
* Automatic request-level caching

```python
@app.get("/items/{id}")
async def get_item(
    item=Depends(get_existing_item)
):
    return item
```

---

## Rule 11: Use Connection Pools Through Dependency Injection

### Anti-Pattern

Creating a database client for every request.

### Production Practice

Initialize pools once during startup.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.db_pool = await create_db_pool()

    yield

    await app.state.db_pool.close()


app = FastAPI(lifespan=lifespan)


async def get_db(request: Request):

    async with request.app.state.db_pool.acquire() as connection:
        yield connection
```

---

## Rule 12: Manage Global State with Lifespan

Avoid:

```python
@app.on_event("startup")
@app.on_event("shutdown")
```

Prefer:

```python
lifespan()
```

Use it for:

* Database pools
* Redis connections
* Kafka consumers
* Cache systems
* Background services

Benefits:

* Centralized initialization
* Better error handling
* Cleaner shutdown

---

# 6. Secure Configuration & Observability

## Rule 13: Centralize Configuration with Pydantic Settings

### Avoid

```python
os.environ["DATABASE_URL"]
```

scattered throughout the project.

### Production Practice

Use:

* `.env`
* `.env.example`
* `pydantic-settings`

Example:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    DATABASE_URL: str
    ENVIRONMENT: str

    class Config:
        env_file = ".env"


settings = Settings()
```

Benefits:

* Startup validation
* Fail fast on missing values
* Type safety

---

## Rule 14: Use Structured JSON Logging

### Avoid

```python
print("User logged in")
```

### Production Practice

Use:

* `logging`
* `structlog`
* `loguru`

Example:

```python
logger.info(
    "user_login",
    user_id=user.id,
    request_id=request_id
)
```

### Include Context

* request_id
* user_id
* trace_id

### Send Logs To

* Fluent Bit
* Logstash
* Elasticsearch

Benefits:

* Better observability
* Easier debugging
* Distributed tracing support

---

# 7. High-Performance Deployment

## Rule 15: Run Uvicorn Behind Gunicorn

Use:

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 5
```

### Why

Gunicorn provides:

* Process management
* Worker supervision
* Better production stability

Uvicorn provides:

* ASGI support
* High-performance networking

### Enable `uvloop`

FastAPI automatically benefits from `uvloop` for improved throughput.

### Worker Formula

```text
workers = (CPU_CORES × 2) + 1
```

Always benchmark before finalizing worker counts.

---

# Summary

### Concurrency

* Avoid blocking inside `async def`
* Use async libraries
* Offload CPU-heavy work

### Background Tasks

* Use native tasks only for lightweight operations
* Use Celery for reliability

### Security

* Disable docs in production

### Pydantic

* Create a custom base model
* Keep validation inside schemas

### Dependencies

* Reuse validation logic
* Use connection pools

### Configuration

* Centralize settings
* Validate at startup

### Observability

* Structured JSON logs
* Trace request context

### Deployment

* Gunicorn + Uvicorn
* Enable `uvloop`
* Benchmark worker counts
