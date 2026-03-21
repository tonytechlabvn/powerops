"""SQLAlchemy ORM models for TerraBot persistence layer.

Job        — tracks every terraform operation with status and output.
AuditLog   — append-only log of all user-initiated actions.
Approval   — plan approval queue; one record per completed plan job.
Workspace  — registered multi-workspace metadata.
DriftCheck — historical drift detection results per workspace.
User       — API key authentication records.

These models are distinct from the Pydantic schemas in core/models.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Job(Base):
    """Represents one terraform operation (init/plan/apply/destroy/etc).

    Columns:
        id            — UUID primary key.
        type          — terraform subcommand: plan | apply | destroy | init | validate.
        status        — pending | running | completed | failed | cancelled.
        workspace_dir — absolute path to the isolated workspace directory.
        created_at    — UTC timestamp when the job was enqueued.
        completed_at  — UTC timestamp when the job finished (NULL while running).
        output        — full stdout captured from terraform.
        error         — stderr or exception message on failure.
        is_hidden     — soft-delete flag; hidden jobs excluded from default listing.
    """

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    workspace_dir: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, default=None
    )
    output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id!r} type={self.type!r} status={self.status!r}>"


class AuditLog(Base):
    """Append-only audit trail for all user-initiated platform actions.

    Columns:
        id           — Auto-increment integer primary key.
        action       — Short action label, e.g. "apply_started", "template_rendered".
        user         — User identifier (username, API key prefix, or "system").
        details_json — JSON-encoded dict with action-specific context.
        timestamp    — UTC timestamp of the event.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r} user={self.user!r}>"


class Approval(Base):
    """Plan approval queue — one record created per completed plan job.

    Columns:
        id                — UUID primary key.
        job_id            — Foreign key to the plan Job that triggered this approval.
        workspace         — Workspace name/path for display.
        status            — pending | approved | rejected.
        plan_summary_json — JSON-encoded list of ResourceChange dicts from the plan.
        created_at        — UTC timestamp when the approval was created.
        decided_at        — UTC timestamp when a decision was recorded (NULL if pending).
        decided_by        — User identifier who made the decision (default "system").
        reason            — Optional human-readable explanation for the decision.
    """

    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workspace: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    plan_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, default=None
    )
    decided_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<Approval id={self.id!r} job_id={self.job_id!r} status={self.status!r}>"


class Workspace(Base):
    """Registered Terraform workspace with provider and environment metadata.

    Columns:
        id            — UUID primary key.
        name          — Unique logical workspace name.
        provider      — Cloud provider label: aws | proxmox | azure | gcp.
        environment   — Environment label: dev | staging | prod.
        workspace_dir — Absolute path to the workspace directory on disk.
        created_at    — UTC timestamp when the workspace was registered.
        last_used     — UTC timestamp of last switch or operation.
    """

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    environment: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    workspace_dir: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )
    last_used: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, default=None
    )

    def __repr__(self) -> str:
        return f"<Workspace name={self.name!r} provider={self.provider!r}>"


class DriftCheck(Base):
    """Historical record of a drift detection run for a workspace.

    Columns:
        id                     — Auto-increment integer primary key.
        workspace              — Logical workspace name.
        has_drift              — True if drift was detected.
        drifted_resources_json — JSON list of drifted resource dicts.
        error                  — Error message if the check failed.
        checked_at             — UTC timestamp when the check ran.
    """

    __tablename__ = "drift_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    has_drift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    drifted_resources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<DriftCheck workspace={self.workspace!r} has_drift={self.has_drift}>"


class User(Base):
    """API key authentication record.

    Columns:
        id           — UUID primary key.
        name         — Human-readable user/service name.
        api_key_hash — SHA-256 hex digest of the raw API key.
        created_at   — UTC timestamp when the user was created.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_uuid
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<User name={self.name!r}>"
