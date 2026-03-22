"""SQLAlchemy ORM models for TerraBot persistence layer.

Existing models (original + Phase 7):
  Job, AuditLog, Approval, Workspace, DriftCheck

New models by phase:
  Phase 1 — StateVersion, StateLock
  Phase 2 — Organization, User (rewritten), Team, TeamMembership,
            WorkspacePermission, APIToken
  Phase 3 — VCSConnection, WebhookDelivery
  Phase 4 — Policy, PolicySet, PolicySetMember, PolicySetAssignment,
            PolicyCheckResult

These models are distinct from the Pydantic schemas in core/models.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer,
    LargeBinary, String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Original models
# ---------------------------------------------------------------------------


class Job(Base):
    """Terraform operation record (init/plan/apply/destroy/etc).

    Phase 3 adds VCS trigger metadata fields.
    """
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    workspace_dir: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )
    output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")

    # Phase 3: VCS trigger context
    vcs_commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True, default=None)
    vcs_pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    vcs_trigger: Mapped[str | None] = mapped_column(String(32), nullable=True, default=None)

    # Relationships
    policy_results: Mapped[list[PolicyCheckResult]] = relationship(back_populates="job", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Job id={self.id!r} type={self.type!r} status={self.status!r}>"


class AuditLog(Base):
    """Append-only audit trail for all user-initiated platform actions."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r} user={self.user!r}>"


class Approval(Base):
    """Plan approval queue — one record per completed plan job.

    Phase 4 adds policy override fields.
    """
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workspace: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    plan_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )
    decided_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Phase 4: policy override support
    policy_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    policy_override_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<Approval id={self.id!r} status={self.status!r}>"


class Workspace(Base):
    """Registered Terraform workspace with provider and environment metadata.

    Phase 2 adds org_id foreign key.
    """
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    environment: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    workspace_dir: Mapped[str] = mapped_column(Text, nullable=False, default="")
    org_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    last_used: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )

    # Relationships
    state_versions: Mapped[list[StateVersion]] = relationship(back_populates="workspace", lazy="selectin")
    vcs_connection: Mapped[VCSConnection | None] = relationship(back_populates="workspace", uselist=False, lazy="selectin")
    permissions: Mapped[list[WorkspacePermission]] = relationship(back_populates="workspace", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Workspace name={self.name!r} provider={self.provider!r}>"


class DriftCheck(Base):
    """Historical record of a drift detection run for a workspace."""
    __tablename__ = "drift_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    has_drift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    drifted_resources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True,
    )

    def __repr__(self) -> str:
        return f"<DriftCheck workspace={self.workspace!r} has_drift={self.has_drift}>"


# ---------------------------------------------------------------------------
# Phase 1: State Management
# ---------------------------------------------------------------------------


class StateVersion(Base):
    """Versioned, encrypted Terraform state stored in PostgreSQL."""
    __tablename__ = "state_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    serial: Mapped[int] = mapped_column(Integer, nullable=False)
    lineage: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    state_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    created_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")

    __table_args__ = (
        UniqueConstraint("workspace_id", "serial", name="uq_state_workspace_serial"),
    )

    # Relationships
    workspace: Mapped[Workspace] = relationship(back_populates="state_versions")

    def __repr__(self) -> str:
        return f"<StateVersion workspace_id={self.workspace_id!r} serial={self.serial}>"


class StateLock(Base):
    """Workspace-level mutex for Terraform state operations."""
    __tablename__ = "state_locks"

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True,
    )
    lock_id: Mapped[str] = mapped_column(String(64), nullable=False)
    holder: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    info: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<StateLock workspace_id={self.workspace_id!r} holder={self.holder!r}>"


# ---------------------------------------------------------------------------
# Phase 2: Organizations, Users, Teams, RBAC
# ---------------------------------------------------------------------------


class Organization(Base):
    """Top-level org container. Multi-org schema, single-org runtime initially."""
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # Relationships
    teams: Mapped[list[Team]] = relationship(back_populates="organization", lazy="selectin")
    users: Mapped[list[User]] = relationship(back_populates="organization", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Organization name={self.name!r}>"


class User(Base):
    """User with email/password auth. Keycloak SSO optional (keycloak_id linked when enabled)."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    keycloak_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    org_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, default=None,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )

    # Relationships
    organization: Mapped[Organization | None] = relationship(back_populates="users")
    team_memberships: Mapped[list[TeamMembership]] = relationship(back_populates="user", lazy="selectin")
    api_tokens: Mapped[list[APIToken]] = relationship(back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User email={self.email!r} name={self.name!r}>"


class Team(Base):
    """Named team within an organization."""
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_team_org_name"),
    )

    # Relationships
    organization: Mapped[Organization] = relationship(back_populates="teams")
    memberships: Mapped[list[TeamMembership]] = relationship(back_populates="team", lazy="selectin")
    workspace_permissions: Mapped[list[WorkspacePermission]] = relationship(
        back_populates="team", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Team name={self.name!r} is_admin={self.is_admin}>"


class TeamMembership(Base):
    """Many-to-many link between teams and users."""
    __tablename__ = "team_memberships"

    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # Relationships
    team: Mapped[Team] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="team_memberships")


class WorkspacePermission(Base):
    """Team-level permission on a workspace: read | plan | write | admin."""
    __tablename__ = "workspace_permissions"

    team_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True,
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True,
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="read")

    # Relationships
    team: Mapped[Team] = relationship(back_populates="workspace_permissions")
    workspace: Mapped[Workspace] = relationship(back_populates="permissions")

    def __repr__(self) -> str:
        return f"<WorkspacePermission team={self.team_id!r} ws={self.workspace_id!r} level={self.level!r}>"


class APIToken(Base):
    """Long-lived API token for CLI/automation access."""
    __tablename__ = "api_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="api_tokens")

    def __repr__(self) -> str:
        return f"<APIToken name={self.name!r} user_id={self.user_id!r}>"


# ---------------------------------------------------------------------------
# Phase 3: VCS Integration
# ---------------------------------------------------------------------------


class VCSConnection(Base):
    """Links a workspace to a GitHub repository + branch for VCS-driven runs."""
    __tablename__ = "vcs_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    installation_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    branch: Mapped[str] = mapped_column(String(128), nullable=False, default="main")
    working_directory: Mapped[str] = mapped_column(String(256), nullable=False, default=".")
    auto_apply: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)

    # Relationships
    workspace: Mapped[Workspace] = relationship(back_populates="vcs_connection")

    def __repr__(self) -> str:
        return f"<VCSConnection repo={self.repo_full_name!r} branch={self.branch!r}>"


class WebhookDelivery(Base):
    """Tracks processed GitHub webhook deliveries for idempotency."""
    __tablename__ = "webhook_deliveries"

    delivery_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    repo_full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="processed")


# ---------------------------------------------------------------------------
# Phase 4: Policy as Code (OPA)
# ---------------------------------------------------------------------------


class Policy(Base):
    """Individual OPA policy with Rego source code."""
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rego_code: Mapped[str] = mapped_column(Text, nullable=False)
    enforcement: Mapped[str] = mapped_column(String(16), nullable=False, default="advisory")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )
    created_by: Mapped[str] = mapped_column(String(36), nullable=False, default="system")

    def __repr__(self) -> str:
        return f"<Policy name={self.name!r} enforcement={self.enforcement!r}>"


class PolicySet(Base):
    """Named group of policies assignable to workspaces or org-wide."""
    __tablename__ = "policy_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="workspace")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # Relationships
    members: Mapped[list[PolicySetMember]] = relationship(back_populates="policy_set", lazy="selectin")
    assignments: Mapped[list[PolicySetAssignment]] = relationship(
        back_populates="policy_set", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PolicySet name={self.name!r} scope={self.scope!r}>"


class PolicySetMember(Base):
    """Many-to-many: policy belongs to policy set."""
    __tablename__ = "policy_set_members"

    policy_set_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policy_sets.id", ondelete="CASCADE"), primary_key=True,
    )
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policies.id", ondelete="CASCADE"), primary_key=True,
    )

    # Relationships
    policy_set: Mapped[PolicySet] = relationship(back_populates="members")
    policy: Mapped[Policy] = relationship()


class PolicySetAssignment(Base):
    """Assigns a policy set to a workspace (NULL workspace_id = org-wide)."""
    __tablename__ = "policy_set_assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    policy_set_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policy_sets.id", ondelete="CASCADE"), nullable=False,
    )
    workspace_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("policy_set_id", "workspace_id", name="uq_psa_set_workspace"),
    )

    # Relationships
    policy_set: Mapped[PolicySet] = relationship(back_populates="assignments")


class PolicyCheckResult(Base):
    """Result of evaluating one policy against one run's plan."""
    __tablename__ = "policy_check_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policies.id", ondelete="CASCADE"), nullable=False,
    )
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    enforcement: Mapped[str] = mapped_column(String(16), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    violations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # Relationships
    job: Mapped[Job] = relationship(back_populates="policy_results")

    def __repr__(self) -> str:
        return f"<PolicyCheckResult policy={self.policy_name!r} passed={self.passed}>"


# ---------------------------------------------------------------------------
# Phase 5: Projects — multi-provider orchestration
# ---------------------------------------------------------------------------


class Project(Base):
    """Top-level project grouping modules, members, credentials, and runs."""
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    config_yaml: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    org_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organizations.id"), nullable=True, default=None,
    )
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_project_org_name"),
    )

    # Relationships
    modules: Mapped[list[ProjectModule]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan",
    )
    members: Mapped[list[ProjectMember]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan",
    )
    credentials: Mapped[list[ProjectCredential]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan",
    )
    runs: Mapped[list[ProjectRun]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan",
    )
    activities: Mapped[list[ProjectActivity]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Project name={self.name!r} status={self.status!r}>"


class ProjectModule(Base):
    """A Terraform module within a project (e.g. aws-networking, proxmox-database)."""
    __tablename__ = "project_modules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    path: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    depends_on: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    last_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_module_name"),
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="modules")

    def __repr__(self) -> str:
        return f"<ProjectModule name={self.name!r} provider={self.provider!r}>"


class ProjectMember(Base):
    """User assignment to a project with a role and optional module scope."""
    __tablename__ = "project_members"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    role_name: Mapped[str] = mapped_column(String(64), nullable=False, default="user")
    assigned_modules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return f"<ProjectMember project={self.project_id!r} user={self.user_id!r} role={self.role_name!r}>"


class ProjectCredential(Base):
    """Encrypted provider credentials scoped to a project."""
    __tablename__ = "project_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("project_id", "provider", name="uq_project_credential_provider"),
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="credentials")

    def __repr__(self) -> str:
        return f"<ProjectCredential project={self.project_id!r} provider={self.provider!r}>"


class ProjectRun(Base):
    """Record of a terraform plan/apply/destroy for a project module."""
    __tablename__ = "project_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    module_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("project_modules.id", ondelete="CASCADE"), nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    run_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    output_log: Mapped[str] = mapped_column(Text, nullable=False, default="")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="runs")
    module: Mapped[ProjectModule] = relationship()

    def __repr__(self) -> str:
        return f"<ProjectRun type={self.run_type!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# Phase 5 (extended): Project Activity Feed
# ---------------------------------------------------------------------------


class ProjectActivity(Base):
    """Append-only activity log for a project — members, runs, config changes."""
    __tablename__ = "project_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    module_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    # Relationships
    project: Mapped[Project] = relationship(back_populates="activities")

    def __repr__(self) -> str:
        return f"<ProjectActivity project={self.project_id!r} action={self.action!r}>"
