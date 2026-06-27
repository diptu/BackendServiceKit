---
description: Ensure service configuration matches shared library standards
---
# Sync-Shared Skill
1. **Analyze**: Read `shared/observability/config/settings.py` as the source of truth.
2. **Compare**: Check the target service's `app/core/config.py` for deviations.
3. **Report/Fix**: If differences are found, suggest the necessary updates to the service to bring it into compliance with the shared library.