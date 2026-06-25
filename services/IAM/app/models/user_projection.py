from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserProjection(Base):
    """
    Read-only user projection maintained by the IAM Service.

    Purpose:
        This table is a local materialized view (projection) of user data
        owned by the User Service. It exists to eliminate synchronous
        dependencies between IAM and User Service during authorization,
        role assignment, access reviews, and user lookups.

    Ownership:
        - Source of truth: User Service
        - Local cache/read model: IAM Service

    Synchronization:
        Records are created and updated asynchronously through domain events:

            user.created
            user.updated
            user.deleted

    Important:
        This entity MUST NEVER contain sensitive or security-critical data
        such as:

            ❌ password hashes
            ❌ MFA secrets
            ❌ phone numbers
            ❌ profile preferences
            ❌ recovery information

        Only authorization-related display data should be replicated.

    Design Notes:
        - No foreign keys to external services.
        - Eventual consistency is acceptable.
        - Used for read operations only.
        - Writes must always originate from User Service.
    """

    __tablename__ = "user_projections"
    __table_args__ = (Index("idx_user_projection_tenant_email", "tenant_id", "email"),)

    #: Globally unique identifier from User Service.
    #: Reuses the original user_id to simplify event correlation.
    id: Mapped[UUID] = mapped_column(
        primary_key=True, comment="User identifier originating from User Service."
    )

    #: Tenant to which the user belongs.
    #: Indexed because most IAM queries are tenant-scoped.
    tenant_id: Mapped[UUID] = mapped_column(
        index=True, nullable=False, comment="Owning tenant identifier."
    )

    #: User email replicated for search, access reviews,
    #: audit displays, and administration screens.
    email: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        comment="Replicated email address from User Service.",
    )

    #: Human-readable name used in UI responses,
    #: audit logs, and role assignment pages.
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User display name replicated from User Service.",
    )

    #: Lifecycle status received from User Service.
    #: Typical values:
    #: active, suspended, locked, deleted.
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Current user lifecycle status."
    )

    #: Timestamp of the most recent successful synchronization
    #: event processed by IAM.
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Last successful synchronization timestamp.",
    )
