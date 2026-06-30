"""Reusable FastAPI DI for job and tenant existence checks."""
from app.dependencies.provisioning import JobDep, get_active_job_or_404, get_job_or_404

__all__ = ["JobDep", "get_active_job_or_404", "get_job_or_404"]
