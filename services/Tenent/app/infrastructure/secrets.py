"""Secrets backend for Control Plane connection credentials.

The Control Plane stores a `secret_ref`, never a raw password; this is what
turns that reference into an actual credential when a DSN is assembled. The
seam is deliberate: `EnvSecretsProvider` is a runnable stand-in that reads an
environment variable, and a production deployment swaps in a Vault/KMS-backed
provider without touching `ControlPlaneService`.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod

from app.domain.exceptions import TenantSecretUnavailableError

_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")


class SecretsProvider(ABC):
    @abstractmethod
    async def get(self, secret_ref: str) -> str:
        """Resolve a secret reference to its value, or raise
        TenantSecretUnavailableError so the caller fails closed."""
        raise NotImplementedError


class EnvSecretsProvider(SecretsProvider):
    """Resolves `secret_ref` from an env var `TENANT_DB_SECRET_<REF>`, where
    <REF> is the reference upper-cased with non-alphanumerics replaced by
    underscores (e.g. `tenant/acme/db` → `TENANT_DB_SECRET_TENANT_ACME_DB`)."""

    _PREFIX = "TENANT_DB_SECRET_"

    async def get(self, secret_ref: str) -> str:
        env_key = self._PREFIX + _NON_ALNUM.sub("_", secret_ref).upper()
        value = os.environ.get(env_key)
        if value is None:
            raise TenantSecretUnavailableError(secret_ref)
        return value
