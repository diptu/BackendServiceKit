---
name: test-harness
description: Scaffold unit/integration tests using enterprise standard fixtures.
---
# Test Harness Protocol

1. **Detection**: Identify the target service and the desired test type (`unit`, `integration`, `e2e`).
2. **Standardization**:
   - For `unit`, use `pytest.mark.asyncio`.
   - For `integration`, inject the `test_db_session` fixture from `shared/testing/fixtures.py`.
3. **Execution**:
   - Generate the test file in `services/<service>/tests/<type>/`.
   - Ensure imports use absolute paths from `app`.
   - Include a `conftest.py` check to ensure standard service-level fixtures are loaded.