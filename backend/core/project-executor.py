"""Dependency-aware Terraform execution pipeline for multi-module projects.

Resolves module dependency order, decrypts credentials, runs terraform
plan/apply per module in topological layers, and persists run records.
"""
from __future__ import annotations

import base64
import importlib.util as _ilu
import json
import logging
import sys as _sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sibling module loader
# ---------------------------------------------------------------------------


def _load_sibling(filename: str, alias: str):
    full_name = f"backend.core.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    spec = _ilu.spec_from_file_location(full_name, Path(__file__).parent / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_dep_resolver = _load_sibling("dependency-resolver.py", "dependency_resolver")
_enc_mod = _load_sibling("state-encryption.py", "state_encryption")
_tf_runner_mod = _load_sibling("terraform-runner.py", "terraform_runner")

# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------


def _decrypt_credentials(cred_row) -> dict:
    """Decrypt a ProjectCredential row and parse JSON. Returns {} on failure."""
    from backend.core.config import get_settings
    s = get_settings()
    if not s.state_encryption_key:
        logger.warning("No encryption key configured — cannot decrypt credentials")
        return {}
    try:
        key = base64.b64decode(s.state_encryption_key)
        plaintext = _enc_mod.decrypt_state(cred_row.credential_data, key)
        return json.loads(plaintext.decode())
    except Exception as exc:
        logger.error("Failed to decrypt credentials for provider %s: %s", cred_row.provider, exc)
        return {}


def _build_env_vars(credentials: list) -> dict[str, str]:
    """Convert decrypted credential dicts into TF_VAR_* environment variables."""
    env: dict[str, str] = {}
    for cred in credentials:
        data = _decrypt_credentials(cred)
        for k, v in data.items():
            # Map known provider keys → TF_VAR_* or standard provider env vars
            env_key = f"TF_VAR_{k}" if not k.startswith("TF_") else k
            env[env_key] = str(v)
    return env


# ---------------------------------------------------------------------------
# Single-module execution
# ---------------------------------------------------------------------------


async def _run_module(
    module,
    project_id: str,
    user_id: str,
    operation: str,
    extra_env: dict[str, str],
    session,
) -> dict:
    """Execute terraform init + plan/apply for one module.

    Creates a ProjectRun record, runs terraform in a temp workspace,
    updates module status and run record on completion.

    Returns a module result dict with keys: name, status, run_id, error.
    """
    from backend.db.models import ProjectRun
    TerraformRunner = _tf_runner_mod.TerraformRunner

    # Determine working directory: use module.path if set, else temp dir
    if module.path and Path(module.path).is_dir():
        work_dir = Path(module.path)
        owns_dir = False
    else:
        _tmp = tempfile.mkdtemp(prefix=f"terrabot_{module.name}_")
        work_dir = Path(_tmp)
        owns_dir = True

        # Write a minimal main.tf so terraform init succeeds in temp dir
        (work_dir / "main.tf").write_text(
            f"# Auto-generated placeholder for module: {module.name}\n",
            encoding="utf-8",
        )

    # Create run record
    run = ProjectRun(
        project_id=project_id,
        module_id=module.id,
        user_id=user_id,
        run_type=operation,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    await session.flush()

    result_status = "failed"
    error_msg = ""
    output_log = ""

    try:
        runner = TerraformRunner(working_dir=work_dir, extra_env=extra_env)

        # Always init first
        init_result = await runner.init()
        output_log += init_result.raw_output or ""

        if operation == "plan":
            plan_result = await runner.plan()
            output_log += plan_result.raw_output or ""
            result_status = "completed" if plan_result.success else "failed"

        elif operation == "apply":
            apply_result = await runner.apply(auto_approve=True)
            output_log += apply_result.raw_output or ""
            result_status = "completed"

        else:
            raise ValueError(f"Unsupported operation: {operation}")

        logger.info("Module '%s' %s: %s", module.name, operation, result_status)

    except Exception as exc:
        error_msg = str(exc)
        output_log += f"\nERROR: {error_msg}"
        logger.error("Module '%s' %s failed: %s", module.name, operation, exc)

    finally:
        # Cleanup temp dir if we created it
        if owns_dir:
            import shutil
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass

    # Persist run result
    run.status = result_status
    run.output_log = output_log[:65535]  # guard against very large logs
    run.completed_at = datetime.now(timezone.utc)
    session.add(run)

    # Update module status
    module.status = "applied" if result_status == "completed" and operation == "apply" else (
        "planned" if result_status == "completed" and operation == "plan" else "failed"
    )
    module.last_run_id = run.id
    session.add(module)

    await session.flush()

    return {
        "name": module.name,
        "status": result_status,
        "run_id": run.id,
        "error": error_msg,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def execute_project(
    project_id: str,
    operation: str,
    user_id: str = "system",
    module_names: list[str] | None = None,
) -> dict:
    """Run plan/apply across project modules in dependency order.

    Resolves execution layers via topological sort, then processes each layer
    sequentially. Modules within a layer are currently run sequentially for
    simplicity (parallel execution can be added later without API changes).

    Args:
        project_id:   UUID of the project to execute.
        operation:    'plan' or 'apply'.
        user_id:      ID of the user triggering the run (for audit records).
        module_names: Optional filter — only execute these named modules.
                      Dependencies are still resolved from the full graph.

    Returns:
        Dict with keys:
          - status:  'completed' | 'partial' | 'failed'
          - modules: list of per-module result dicts
          - errors:  list of error strings (empty on full success)

    Raises:
        ValueError: If project not found or invalid operation.
    """
    if operation not in ("plan", "apply"):
        raise ValueError(f"operation must be 'plan' or 'apply', got: {operation!r}")

    from backend.db.database import get_session
    from backend.db.models import Project
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import selectinload

    async with get_session() as session:
        project = (await session.execute(
            sa_select(Project)
            .where(Project.id == project_id)
            .options(
                selectinload(Project.modules),
                selectinload(Project.credentials),
            )
        )).scalar_one_or_none()

        if project is None:
            raise ValueError(f"Project '{project_id}' not found")

        # Filter active modules
        active_modules = [m for m in (project.modules or []) if m.status != "removed"]

        if not active_modules:
            return {"status": "completed", "modules": [], "errors": []}

        # Build module dicts for dependency resolver
        module_dicts = [
            {"name": m.name, "depends_on": m.depends_on or [], "_obj": m}
            for m in active_modules
        ]

        # Resolve execution layers
        layers = _dep_resolver.resolve_execution_order(module_dicts)

        # Build env from all project credentials
        extra_env = _build_env_vars(project.credentials or [])

        # Optionally filter to requested module names (keep full layer structure)
        target_names: set[str] | None = set(module_names) if module_names else None

        module_results: list[dict] = []
        all_errors: list[str] = []

        # Execute layer by layer (layers are sequential; within a layer parallel is possible)
        for layer in layers:
            for mod_dict in layer:
                mod_obj = mod_dict["_obj"]

                # Skip if caller specified a subset and this module isn't in it
                if target_names is not None and mod_obj.name not in target_names:
                    continue

                result = await _run_module(
                    module=mod_obj,
                    project_id=project_id,
                    user_id=user_id,
                    operation=operation,
                    extra_env=extra_env,
                    session=session,
                )
                module_results.append(result)

                if result["status"] == "failed":
                    all_errors.append(f"{mod_obj.name}: {result['error']}")

        # Determine overall status
        if not module_results:
            overall = "completed"
        elif all_errors and len(all_errors) == len(module_results):
            overall = "failed"
        elif all_errors:
            overall = "partial"
        else:
            overall = "completed"

        logger.info(
            "Project '%s' %s finished: %s (%d modules, %d errors)",
            project_id, operation, overall, len(module_results), len(all_errors),
        )

        return {
            "status": overall,
            "modules": module_results,
            "errors": all_errors,
        }
