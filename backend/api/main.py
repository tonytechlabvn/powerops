"""FastAPI application factory.

Creates the app with CORS, middleware, all routers, and lifespan hooks
for database initialisation and teardown.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.core.config import get_settings
from backend.core.exceptions import TerrabotError
from backend.db.database import close_db, init_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Kebab-case module loader (mirrors pattern from core/__init__.py)
# ---------------------------------------------------------------------------

import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

_API_DIR = _Path(__file__).parent


def _load(rel_path: str, alias: str):
    """Load a kebab-case module relative to the api package directory."""
    full_name = f"backend.api.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    spec = _ilu.spec_from_file_location(full_name, _API_DIR / rel_path)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# Load kebab-case service modules
_load("services/job-service.py", "services.job_service")
_load("services/approval-service.py", "services.approval_service")
_load("services/stream-service.py", "services.stream_service")

# Load kebab-case schema modules
_load("schemas/request-schemas.py", "schemas.request_schemas")
_load("schemas/response-schemas.py", "schemas.response_schemas")

# Load middleware modules
_error_handler = _load("middleware/error-handler.py", "middleware.error_handler")
_audit_mw      = _load("middleware/audit-middleware.py", "middleware.audit_middleware")
_auth_mw       = _load("middleware/auth-middleware.py", "middleware.auth_middleware")

# Load route modules — original
_health_routes   = _load("routes/health-routes.py",   "routes.health_routes")
_job_routes      = _load("routes/job-routes.py",       "routes.job_routes")
_template_routes = _load("routes/template-routes.py",  "routes.template_routes")
_terraform_routes = _load("routes/terraform-routes.py","routes.terraform_routes")
_approval_routes = _load("routes/approval-routes.py",  "routes.approval_routes")
_config_routes   = _load("routes/config-routes.py",    "routes.config_routes")
_stream_routes   = _load("routes/stream-routes.py",    "routes.stream_routes")

# Load route modules — Phase 7 advanced features
_drift_routes     = _load("routes/drift-routes.py",     "routes.drift_routes")
_workspace_routes = _load("routes/workspace-routes.py", "routes.workspace_routes")
_import_routes    = _load("routes/import-routes.py",    "routes.import_routes")

# Deploy routes (template → workspace → init → plan)
_deploy_routes      = _load("routes/deploy-routes.py",      "routes.deploy_routes")
_auto_deploy_routes = _load("routes/auto-deploy-routes.py", "routes.auto_deploy_routes")

# Phase 1: State management routes
_state_schemas = _load("schemas/state-schemas.py", "schemas.state_schemas")
_state_routes  = _load("routes/state-routes.py",   "routes.state_routes")

# Phase 2: Auth & RBAC routes
_auth_schemas  = _load("schemas/auth-schemas.py",  "schemas.auth_schemas")
_permission_mw = _load("middleware/permission-middleware.py", "middleware.permission_middleware")
_auth_routes   = _load("routes/auth-routes.py",    "routes.auth_routes")
_user_routes   = _load("routes/user-routes.py",    "routes.user_routes")
_team_routes   = _load("routes/team-routes.py",    "routes.team_routes")
_org_routes    = _load("routes/org-routes.py",     "routes.org_routes")

# Phase 3: VCS integration routes
_vcs_schemas     = _load("schemas/vcs-schemas.py",     "schemas.vcs_schemas")
_webhook_routes  = _load("routes/webhook-routes.py",   "routes.webhook_routes")
_vcs_routes      = _load("routes/vcs-routes.py",       "routes.vcs_routes")

# Phase 4: Policy routes
_policy_schemas = _load("schemas/policy-schemas.py", "schemas.policy_schemas")
_policy_routes  = _load("routes/policy-routes.py",   "routes.policy_routes")

# Phase 5: Project routes
_project_schemas = _load("schemas/project-schemas.py", "schemas.project_schemas")
_project_routes  = _load("routes/project-routes.py",   "routes.project_routes")

# Phase 5 (exec): Multi-module scaffold + execution routes
_project_exec_routes = _load("routes/project-execution-routes.py", "routes.project_execution_routes")

# Phase 5: Project templates + AI wizard
_tpl_schemas = _load("schemas/project-template-schemas.py", "schemas.project_template_schemas")
_tpl_routes  = _load("routes/project-template-routes.py",   "routes.project_template_routes")

# Phase 6: HCP Terraform Cloud routes
_tfc_schemas = _load("schemas/tfc-schemas.py", "schemas.tfc_schemas")
_tfc_routes  = _load("routes/tfc-routes.py",   "routes.tfc_routes")

# Standard Terraform Workflow — HCL file management (Phase 1)
_hcl_file_schemas  = _load("schemas/hcl-file-schemas.py",              "schemas.hcl_file_schemas")
_hcl_file_routes   = _load("routes/hcl-file-routes.py",               "routes.hcl_file_routes")
_hcl_dir_routes    = _load("routes/hcl-directory-routes.py",           "routes.hcl_directory_routes")

# Standard Terraform Workflow — Environment management (Phase 2)
_env_schemas       = _load("schemas/environment-schemas.py",           "schemas.environment_schemas")
_env_routes        = _load("routes/environment-routes.py",             "routes.environment_routes")

# Standard Terraform Workflow — Variable sets (Phase 3)
_vs_schemas        = _load("schemas/variable-set-schemas.py",          "schemas.variable_set_schemas")
_vs_routes         = _load("routes/variable-set-routes.py",            "routes.variable_set_routes")
_vs_assign_routes  = _load("routes/variable-set-assignment-routes.py", "routes.variable_set_assignment_routes")

# Standard Terraform Workflow — VCS workflow enhancement (Phase 4)
_vcs_plan_schemas  = _load("schemas/vcs-plan-schemas.py",              "schemas.vcs_plan_schemas")
_vcs_wf_routes     = _load("routes/vcs-workflow-routes.py",            "routes.vcs_workflow_routes")

# Standard Terraform Workflow — Module registry + stacks (Phase 5-7)
_registry_schemas  = _load("schemas/registry-schemas.py",              "schemas.registry_schemas")
_registry_routes   = _load("routes/registry-routes.py",                "routes.registry_routes")
_stack_schemas     = _load("schemas/stack-schemas.py",                  "schemas.stack_schemas")
_stack_routes      = _load("routes/stack-routes.py",                    "routes.stack_routes")

# Phases 8–11: AI editor, plan explainer, remediation, module generator
_ai_editor_schemas      = _load("schemas/ai-editor-schemas.py",       "schemas.ai_editor_schemas")
_plan_analysis_schemas  = _load("schemas/plan-analysis-schemas.py",   "schemas.plan_analysis_schemas")
_remediation_schemas    = _load("schemas/remediation-schemas.py",     "schemas.remediation_schemas")
_module_gen_schemas     = _load("schemas/module-generator-schemas.py","schemas.module_generator_schemas")
_ai_editor_routes       = _load("routes/ai-editor-routes.py",         "routes.ai_editor_routes")
_plan_analysis_routes   = _load("routes/plan-analysis-routes.py",     "routes.plan_analysis_routes")
_remediation_routes     = _load("routes/remediation-routes.py",       "routes.remediation_routes")
_module_gen_routes      = _load("routes/module-generator-routes.py",  "routes.module_generator_routes")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialise DB. Shutdown: close connection pool."""
    logger.info("TerraBot API starting up...")
    await init_db()
    logger.info("Database ready.")
    # Restore persisted provider credentials into env vars
    try:
        _config_routes.load_persisted_config()
    except Exception as exc:
        logger.warning("Could not load provider config: %s", exc)

    # Phase 4: Seed starter policies on first boot + sync all to OPA
    try:
        import importlib.util as _ilu2
        import sys as _sys2
        from pathlib import Path as _P2
        _core_dir = _P2(__file__).parent.parent / "core"
        _pe_name = "backend.core.policy_evaluator"
        if _pe_name not in _sys2.modules:
            _spec = _ilu2.spec_from_file_location(_pe_name, _core_dir / "policy-evaluator.py")
            _pe_mod = _ilu2.module_from_spec(_spec)
            _sys2.modules[_pe_name] = _pe_mod
            _spec.loader.exec_module(_pe_mod)
        else:
            _pe_mod = _sys2.modules[_pe_name]
        seeded = await _pe_mod.seed_starter_policies()
        if seeded:
            logger.info("Seeded %d starter policies.", seeded)
        synced = await _pe_mod.sync_policies_to_opa()
        logger.info("Synced %d policies to OPA.", synced)
    except Exception as exc:
        logger.warning("Policy init skipped: %s", exc)

    yield
    logger.info("TerraBot API shutting down...")
    await close_db()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="TerraBot API",
        description="AI-powered Terraform automation platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend dev server + any configured origins
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth middleware (runs before audit so user identity is available)
    app.add_middleware(_auth_mw.AuthMiddleware)

    # Audit logging middleware
    app.add_middleware(_audit_mw.AuditMiddleware)

    # Global exception handlers
    app.add_exception_handler(TerrabotError, _error_handler.terrabot_exception_handler)
    app.add_exception_handler(ValueError, _error_handler.value_error_handler)
    app.add_exception_handler(Exception, _error_handler.unhandled_exception_handler)

    # Register all routers — original
    app.include_router(_health_routes.router)
    app.include_router(_job_routes.router)
    app.include_router(_template_routes.router)
    app.include_router(_terraform_routes.router)
    app.include_router(_approval_routes.router)
    app.include_router(_config_routes.router)
    app.include_router(_stream_routes.router)

    # Register Phase 7 routers
    app.include_router(_drift_routes.router)
    app.include_router(_workspace_routes.router)
    app.include_router(_import_routes.router)

    # Deploy routes
    app.include_router(_deploy_routes.router)
    app.include_router(_auto_deploy_routes.router)

    # Phase 1: State management
    app.include_router(_state_routes.router)

    # Phase 2: Auth & RBAC
    app.include_router(_auth_routes.router)
    app.include_router(_user_routes.router)
    app.include_router(_team_routes.router)
    app.include_router(_org_routes.router)

    # Phase 3: VCS integration
    app.include_router(_webhook_routes.router)
    app.include_router(_vcs_routes.router)

    # Phase 4: Policy
    app.include_router(_policy_routes.router)

    # Phase 5: Projects
    app.include_router(_project_routes.router)
    app.include_router(_project_exec_routes.router)
    app.include_router(_tpl_routes.router)

    # Phase 6: HCP Terraform Cloud
    app.include_router(_tfc_routes.router)

    # Standard Terraform Workflow — HCL file management
    app.include_router(_hcl_file_routes.router)
    app.include_router(_hcl_dir_routes.search_router)
    app.include_router(_hcl_dir_routes.dir_router)

    # Standard Terraform Workflow — Environments
    app.include_router(_env_routes.router)

    # Standard Terraform Workflow — Variable sets
    app.include_router(_vs_routes.router)
    app.include_router(_vs_assign_routes.router)

    # Standard Terraform Workflow — VCS workflow
    app.include_router(_vcs_wf_routes.router)

    # Standard Terraform Workflow — Module registry + stacks
    app.include_router(_registry_routes.router)
    if hasattr(_registry_routes, 'v1_router'):
        app.include_router(_registry_routes.v1_router)
    app.include_router(_stack_routes.router)
    if hasattr(_stack_routes, 'upgrades_router'):
        app.include_router(_stack_routes.upgrades_router)
    if hasattr(_stack_routes, 'admin_router'):
        app.include_router(_stack_routes.admin_router)

    # Phases 8–11: AI editor, plan explainer, remediation, module generator
    app.include_router(_ai_editor_routes.router)
    app.include_router(_plan_analysis_routes.router)
    app.include_router(_remediation_routes.router)
    app.include_router(_module_gen_routes.router)

    # Terraform Registry service discovery (Phase 5)
    @app.get("/.well-known/terraform.json", include_in_schema=False)
    async def terraform_service_discovery():
        return {"modules.v1": "/api/registry/v1/modules/"}

    # Keycloak reverse proxy — single-domain setup
    # Routes /auth/* to internal Keycloak container so browser never hits raw IP
    import httpx as _httpx

    # Base URL is the raw Keycloak host (without /auth path) since we forward full /auth/* path
    _kc_base = settings.keycloak_url.replace("/auth", "").rstrip("/")
    _keycloak_client = _httpx.AsyncClient(base_url=_kc_base, timeout=30.0)

    @app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], include_in_schema=False)
    async def keycloak_proxy(path: str, request: Request):
        """Reverse proxy all /auth/* requests to Keycloak."""
        from starlette.responses import Response as StarletteResponse
        url = f"/auth/{path}"
        if request.url.query:
            url = f"{url}?{request.url.query}"
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        # Forward proxy headers so Keycloak generates correct public URLs
        headers["X-Forwarded-Host"] = "powerops.tonytechlab.com"
        headers["X-Forwarded-Proto"] = "https"
        headers["X-Forwarded-Port"] = "443"
        try:
            resp = await _keycloak_client.request(
                method=request.method, url=url,
                content=body, headers=headers,
            )
            excluded = {"transfer-encoding", "content-encoding", "content-length"}
            resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
            return StarletteResponse(
                content=resp.content, status_code=resp.status_code, headers=resp_headers,
            )
        except Exception as exc:
            logger.error("Keycloak proxy error: %s", exc)
            return JSONResponse(status_code=502, content={"detail": "Keycloak unavailable"})

    # Serve frontend static files in production (built React app at /app/static)
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.is_dir():

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            """Serve React SPA for all non-API routes."""
            # Serve actual files (JS, CSS, images, etc.)
            file_path = static_dir / full_path
            if file_path.is_file() and static_dir in file_path.resolve().parents:
                return FileResponse(file_path)
            # index.html: no-cache so browser always gets latest bundle references
            return FileResponse(
                static_dir / "index.html",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

    return app


# Module-level app instance for uvicorn
app = create_app()
