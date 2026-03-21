"""Async Terraform CLI wrapper.

TerraformRunner executes terraform subcommands in isolated workspace
directories, parses JSON output into Pydantic models, and supports
real-time stdout streaming.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from backend.core.exceptions import TerraformError, TimeoutError as TerrabotTimeoutError
from backend.core.models import (
    ApplyResult,
    ChangeAction,
    DestroyResult,
    InitResult,
    PlanResult,
    ResourceChange,
    ShowResult,
    ValidationResult,
)
import importlib.util as _ilu
import sys as _sys
from pathlib import Path as _Path

def _load_sibling(filename: str, alias: str):
    """Load a kebab-case sibling module without going through package __init__."""
    full_name = f"backend.core.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    spec = _ilu.spec_from_file_location(full_name, _Path(__file__).parent / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod

_subprocess_executor = _load_sibling("subprocess-executor.py", "subprocess_executor")
ProcessResult = _subprocess_executor.ProcessResult
run_process = _subprocess_executor.run_process
stream_process = _subprocess_executor.stream_process

logger = logging.getLogger(__name__)

# Sentinel return code when process is killed by timeout
_TIMEOUT_RC = -1


def _parse_change_action(actions: list[str]) -> ChangeAction:
    """Map terraform JSON action array to ChangeAction enum."""
    key = "+".join(sorted(actions))
    mapping = {
        "create": ChangeAction.create,
        "update": ChangeAction.update,
        "delete": ChangeAction.delete,
        "delete+create": ChangeAction.replace,
        "create+delete": ChangeAction.replace,
        "no-op": ChangeAction.no_op,
        "read": ChangeAction.read,
    }
    return mapping.get(key, ChangeAction.no_op)


def _extract_resource_changes(plan_json: dict) -> list[ResourceChange]:
    """Parse resource_changes array from terraform plan JSON output."""
    changes: list[ResourceChange] = []
    for rc in plan_json.get("resource_changes", []):
        change = rc.get("change", {})
        actions = change.get("actions", ["no-op"])
        if actions == ["no-op"]:
            continue
        changes.append(
            ResourceChange(
                address=rc.get("address", ""),
                type=rc.get("type", ""),
                name=rc.get("name", ""),
                action=_parse_change_action(actions),
                provider=rc.get("provider_name", ""),
            )
        )
    return changes


class TerraformRunner:
    """Execute terraform commands asynchronously in an isolated workspace.

    Args:
        working_dir: Directory containing terraform configuration files.
        binary: Path to terraform executable (default: "terraform").
        timeout: Per-operation timeout in seconds (default: 1800).
        extra_env: Additional environment variables injected into the process.
    """

    def __init__(
        self,
        working_dir: Path,
        binary: str = "terraform",
        timeout: int = 1800,
        extra_env: dict[str, str] | None = None,
    ):
        self.working_dir = Path(working_dir)
        self.binary = binary
        self.timeout = timeout
        self._env: dict[str, str] = {**os.environ, **(extra_env or {})}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run(self, *args: str) -> ProcessResult:
        """Run terraform with given args, raise on timeout or non-zero exit."""
        cmd = [self.binary, *args]
        result = await run_process(cmd, self.working_dir, self._env, self.timeout)

        if result.timed_out:
            raise TerrabotTimeoutError(
                f"terraform {args[0]} timed out after {self.timeout}s",
                command=args[0],
                timeout_seconds=self.timeout,
            )
        return result

    def _require_success(self, result: ProcessResult, command: str) -> None:
        """Raise TerraformError if process exited non-zero."""
        if not result.success:
            raise TerraformError(
                f"terraform {command} failed (rc={result.return_code})",
                command=command,
                working_dir=self.working_dir,
                return_code=result.return_code,
                stderr=result.stderr,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def init(self, upgrade: bool = False) -> InitResult:
        """Run `terraform init`.

        Args:
            upgrade: Pass -upgrade to update provider versions.

        Returns:
            InitResult with success flag and raw output.
        """
        args = ["init", "-no-color"]
        if upgrade:
            args.append("-upgrade")

        result = await self._run(*args)
        if not result.success:
            raise TerraformError(
                "terraform init failed",
                command="init",
                working_dir=self.working_dir,
                return_code=result.return_code,
                stderr=result.stderr,
            )
        return InitResult(success=True, raw_output=result.stdout, stderr=result.stderr)

    async def validate(self) -> ValidationResult:
        """Run `terraform validate -json`.

        Returns:
            ValidationResult parsed from JSON output.
        """
        result = await self._run("validate", "-json", "-no-color")
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return ValidationResult(valid=False, errors=[result.stderr or result.stdout])

        valid = data.get("valid", False)
        diags = data.get("diagnostics", [])
        errors = [d.get("summary", "") for d in diags if d.get("severity") == "error"]
        return ValidationResult(valid=valid, errors=errors)

    async def plan(
        self,
        var_file: str | None = None,
        out: str | None = None,
        destroy: bool = False,
    ) -> PlanResult:
        """Run `terraform plan -json`.

        Args:
            var_file: Optional path to a .tfvars file.
            out: Optional path to save the plan binary.
            destroy: If True, passes -destroy flag.

        Returns:
            PlanResult with structured resource changes.
        """
        args = ["plan", "-json", "-no-color"]
        if var_file:
            args += [f"-var-file={var_file}"]
        if out:
            args += [f"-out={out}"]
        if destroy:
            args.append("-destroy")

        result = await self._run(*args)

        # terraform plan exits 1 on error, 2 when changes present — both valid JSON
        if result.return_code not in (0, 2) and not result.stdout.strip():
            raise TerraformError(
                "terraform plan failed",
                command="plan",
                working_dir=self.working_dir,
                return_code=result.return_code,
                stderr=result.stderr,
            )

        # Plan JSON is emitted as a series of newline-delimited JSON objects;
        # find the final "planned_values" summary object.
        plan_data: dict = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") == "planned_changes" or "resource_changes" in obj:
                    plan_data = obj
            except json.JSONDecodeError:
                continue

        resource_changes = _extract_resource_changes(plan_data)
        return PlanResult(
            success=result.return_code in (0, 2),
            format_version=plan_data.get("format_version", ""),
            terraform_version=plan_data.get("terraform_version", ""),
            resource_changes=resource_changes,
            raw_output=result.stdout,
            stderr=result.stderr,
            plan_file=out or "",
        )

    async def apply(
        self,
        plan_file: str | None = None,
        auto_approve: bool = False,
        var_file: str | None = None,
    ) -> ApplyResult:
        """Run `terraform apply -json`.

        Args:
            plan_file: Optional path to a saved plan binary (skips interactive prompt).
            auto_approve: Pass -auto-approve when no plan_file given.
            var_file: Optional .tfvars file path.

        Returns:
            ApplyResult with resource changes and outputs.
        """
        args = ["apply", "-json", "-no-color"]
        if auto_approve and not plan_file:
            args.append("-auto-approve")
        if var_file:
            args += [f"-var-file={var_file}"]
        if plan_file:
            args.append(plan_file)

        result = await self._run(*args)
        self._require_success(result, "apply")

        resource_changes: list[ResourceChange] = []
        outputs: dict = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") == "apply_complete":
                    pass  # individual resource events
                if "resource_changes" in obj:
                    resource_changes = _extract_resource_changes(obj)
                if obj.get("type") == "outputs":
                    outputs = obj.get("outputs", {})
            except json.JSONDecodeError:
                continue

        return ApplyResult(
            success=True,
            resource_changes=resource_changes,
            outputs=outputs,
            raw_output=result.stdout,
            stderr=result.stderr,
        )

    async def destroy(self, auto_approve: bool = False, var_file: str | None = None) -> DestroyResult:
        """Run `terraform destroy`.

        Args:
            auto_approve: Pass -auto-approve to skip interactive confirmation.
            var_file: Optional .tfvars file path.

        Returns:
            DestroyResult with count of destroyed resources.
        """
        args = ["destroy", "-json", "-no-color"]
        if auto_approve:
            args.append("-auto-approve")
        if var_file:
            args += [f"-var-file={var_file}"]

        result = await self._run(*args)
        self._require_success(result, "destroy")

        destroyed = 0
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("type") == "apply_complete" and obj.get("@message", "").endswith("destroyed"):
                    destroyed += 1
            except json.JSONDecodeError:
                continue

        return DestroyResult(
            success=True,
            resources_destroyed=destroyed,
            raw_output=result.stdout,
            stderr=result.stderr,
        )

    async def output(self) -> dict:
        """Run `terraform output -json` and return parsed dict."""
        result = await self._run("output", "-json", "-no-color")
        self._require_success(result, "output")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}

    async def show(self, plan_file: str | None = None) -> ShowResult:
        """Run `terraform show -json [plan_file]`.

        Args:
            plan_file: Optional plan binary to inspect; shows current state if omitted.

        Returns:
            ShowResult with parsed state/plan JSON.
        """
        args = ["show", "-json", "-no-color"]
        if plan_file:
            args.append(plan_file)

        result = await self._run(*args)
        self._require_success(result, "show")

        try:
            state = json.loads(result.stdout)
        except json.JSONDecodeError:
            state = {}

        return ShowResult(success=True, state=state, raw_output=result.stdout)

    async def stream(self, *args: str) -> AsyncGenerator[str, None]:
        """Stream stdout lines from any terraform command in real time.

        Useful for long-running apply/destroy operations in a UI context.

        Args:
            *args: Terraform subcommand and flags, e.g. ("apply", "-auto-approve").

        Yields:
            Decoded stdout lines as they arrive.
        """
        cmd = [self.binary, *args]
        async for line in stream_process(cmd, self.working_dir, self._env, self.timeout):
            yield line
