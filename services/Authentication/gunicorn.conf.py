"""Gunicorn configuration for the Authentication service.

Puts the mono-repo root on ``sys.path`` so ``shared`` resolves at runtime.

``shared/`` lives two levels up from this service directory and is imported
during app startup (``app.infrastructure.database.tenant_routing`` →
``shared.db``). Tests get it via pytest's ``pythonpath = [".", "../.."]``
in ``pyproject.toml``; there is no equivalent for a plain
``gunicorn app.main:app`` launched from ``services/Authentication/``, which is why the
workers failed to boot with ``ModuleNotFoundError: No module named 'shared'``.

Gunicorn auto-loads this file when it is present in the working directory, so
no ``-c`` flag is needed. The ``sys.path`` mutation runs in the master process
and is inherited by forked workers.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
