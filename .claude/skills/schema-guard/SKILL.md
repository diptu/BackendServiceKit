---
name: schema-guard
description: Detect breaking changes in Pydantic schemas against DB models.
---
# Schema Guard Protocol

1. **Diff Analysis**: Compare changes in `app/schemas/` against the latest migration file in `alembic/versions/`.
2. **Conflict Detection**:
   - **Breaking**: Rename/Removal of fields, changing type without migration update.
   - **Non-Breaking**: Addition of optional fields.
3. **Resolution**: 
   - If a breaking change is detected, block the proposed commit.
   - Prompt the user: "Generate an Alembic migration script to match this schema update?"