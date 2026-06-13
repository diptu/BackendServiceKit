# 🔐 IAM Service (RBAC Microservice)

High-performance, production-ready Identity and Access Management service built with FastAPI, utilizing Role-Based Access Control (RBAC) and strict architectural separation of concerns.

---

## 🏗️ Separation of Concerns

| Layer | Responsibility |
| :--- | :--- |
| **api** | HTTP delivery layer & endpoint Routing (`FastAPI`) |
| **services** | Orchestrates business logic, domain constraints, and transactions |
| **repositories** | Decoupled data access layer containing raw database queries (`SQLAlchemy`) |
| **models** | Declarative database schemas (`PostgreSQL`) |
| **schemas** | Strict request/response data validation and serialization (`Pydantic v2`) |
| **core** | Low-level security primitives, hashing algorithms, and JWT mechanics |

---

## 💾 Relational Schema Design

```sql
-- Core Identity & Session Entities
CREATE TABLE iam.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE iam.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES iam.users(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL,
    user_agent TEXT,
    ip_address TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);

-- RBAC Entities
CREATE TABLE iam.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE iam.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL, -- Format: 'resource:action' (e.g., 'document:write')
    description TEXT,
    created_at TIMESTAMP DEFAULT now()
);

-- Many-to-Many Bridge Tables
CREATE TABLE iam.user_roles (
    user_id UUID REFERENCES iam.users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES iam.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE iam.role_permissions (
    role_id UUID REFERENCES iam.roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES iam.permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Domain Specific Profile & Observability Tables
CREATE TABLE profile.user_profiles (
    user_id UUID PRIMARY KEY REFERENCES iam.users(id) ON DELETE CASCADE,
    full_name VARCHAR(150),
    avatar_url TEXT,
    phone VARCHAR(30),
    bio TEXT,
    date_of_birth DATE,
    country VARCHAR(100),
    city VARCHAR(100),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE iam.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    action VARCHAR(100), -- login, role_assigned, permission_revoked
    entity_type VARCHAR(50),
    entity_id UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT now()
);
```

---

## 📂 Layout & Project Structure

```text
services/iam/
├── app/
│   ├── api/v1/routes/     # Auth, Users, Roles, Permissions, RBAC
│   ├── core/              # Config, Security, JWT matrix, Exception handlers
│   ├── db/                # Sessions, base declarations, migrations
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic validation schemas
│   ├── repositories/      # Encapsulated query boundaries
│   ├── services/          # Core domain business logic pipelines
│   └── dependencies/      # FastAPI Dependency Injection guards (Auth/RBAC)
└── tests/                 # Isolated Pytest suites per context
```

---

## 🔌 API Matrix (`/api/v1`)

### 🔐 Authentication
* `POST /auth/register` - Registers a unique account. Accepts payload with credential context.
* `POST /auth/login` - Validates keys, issues stateful access/refresh token matrices.
* `POST /auth/refresh` - Evaluates refresh token validity, rotates key states.
* `POST /auth/logout` - Revokes explicit active sessions.

### 👤 User Management
* `GET /users/me` - Retreives contextual state of authorized client.
* `GET /users` | `GET /users/{id}` - Complete and resource-isolated entity lookup (Admin Guarded).
* `PUT /users/{id}` | `DELETE /users/{id}` - Mutation and soft-deletion operations.
* `POST /users/{id}/roles` | `DELETE /users/{id}/roles/{role_id}` - Real-time role inheritance mapping.

### 🧩 Role & Permission Governance
* `POST` | `GET` | `PUT` | `DELETE` `/roles` - Full lifecycle control of system access groups.
* `POST` | `DELETE` `/roles/{id}/permissions` - Aggregates discrete action allowances to specified structural groups.
* `POST` | `GET` | `PUT` | `DELETE` `/permissions` - Fine-grained declarative action boundary specifications.

### 🔎 Authorization & Audit
* `POST /auth/check` - Verifies explicit token authorization state.
* `GET /users/{id}/permissions` | `GET /users/{id}/roles` - Returns evaluated permissions and assigned roles.
* `GET /audit-logs` | `GET /users/{id}/audit-logs` - Context-aware security and operations telemetry extraction.
* `GET /health` - Liveness/Readiness validation probe.