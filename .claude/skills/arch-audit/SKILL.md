---
name: arch-audit
description: Audit a service's directory structure against the Enterprise Clean Architecture standard.
---
- **Execution**: Run `/arch-audit <service_name>`.
# Architecture Audit Protocol

## 1. Compliance Standard
All services in `/services/` MUST follow this internal structure:
- `app/domain/`: Pure business logic (No database or external framework imports).
- `app/services/`: Application orchestrators (Uses domain models).
- `app/infrastructure/`: Concrete implementations (DB drivers, external API clients).
- `app/api/`: Request/Response handling (Depends only on services).

## 2. Audit Workflow
1. **Analyze**: Run a recursive scan of the target service’s `app/` directory.
2. **Layer Violation Check**:
   - Verify `app/domain/` does NOT import from `app/infrastructure/` or `app/api/`.
   - Verify `app/infrastructure/` does NOT contain business rules.
3. **Naming Convention**: Check that files inside `app/api/` end in `_router.py` or `_endpoints.py`.
4. **Shared Dependency Audit**: Ensure that any imports from `shared/` are limited to permitted modules (e.g., `observability`, `middleware`).

## 3. Execution
- Trigger: `/arch-audit [service_name]`
- Output: A report highlighting "Clean" components and "Violation" instances with suggestions for refactoring.