---
name: doc-gen
description: Generate READMEs for specific services.
---
# Enterprise Doc-Gen Protocol

- **Execution**: Run `/doc-gen <service_name>`.
- **Constraint**: NEVER scan beyond `services/<service_name>/`.
- **Steps**:
    1. Read `services/<service_name>/app/api/` to extract endpoints.
    2. Read `services/<service_name>/README.md` to identify current structure.
    3. Update with: Overview, Setup (from Dockerfile), Architecture (referencing Hierarchy.md), and API Reference.
    4. Include local .png references.