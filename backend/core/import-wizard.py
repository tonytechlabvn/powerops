"""Import wizard — guided terraform import with HCL stub generation.

Step 1: Generate a minimal HCL resource stub for the target resource type.
Step 2: Run `terraform import <address> <id>` to pull live state.
Step 3: Validate the imported state is consistent.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import importlib.util as _ilu
import sys as _sys

logger = logging.getLogger(__name__)


def _load_sibling(filename: str, alias: str):
    full_name = f"backend.core.{alias}"
    if full_name in _sys.modules:
        return _sys.modules[full_name]
    spec = _ilu.spec_from_file_location(full_name, Path(__file__).parent / filename)
    mod = _ilu.module_from_spec(spec)  # type: ignore[arg-type]
    _sys.modules[full_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_subprocess_executor = _load_sibling("subprocess-executor.py", "subprocess_executor")
run_process = _subprocess_executor.run_process

# Minimal HCL stubs for well-known resource types.
# Keys are resource_type strings; values are HCL template strings.
_HCL_STUBS: dict[str, str] = {
    "aws_instance": (
        'resource "aws_instance" "{name}" {{\n'
        "  # Populated by terraform import — run `terraform show` to see values\n"
        '  ami           = ""\n'
        '  instance_type = ""\n'
        "}}\n"
    ),
    "aws_s3_bucket": (
        'resource "aws_s3_bucket" "{name}" {{\n'
        '  bucket = ""\n'
        "}}\n"
    ),
    "aws_security_group": (
        'resource "aws_security_group" "{name}" {{\n'
        '  name   = ""\n'
        '  vpc_id = ""\n'
        "}}\n"
    ),
    "aws_vpc": (
        'resource "aws_vpc" "{name}" {{\n'
        '  cidr_block = ""\n'
        "}}\n"
    ),
    "aws_subnet": (
        'resource "aws_subnet" "{name}" {{\n'
        '  vpc_id     = ""\n'
        '  cidr_block = ""\n'
        "}}\n"
    ),
    "proxmox_vm_qemu": (
        'resource "proxmox_vm_qemu" "{name}" {{\n'
        '  name        = ""\n'
        '  target_node = ""\n'
        "}}\n"
    ),
}

_DEFAULT_STUB = (
    'resource "{resource_type}" "{name}" {{\n'
    "  # Populated by terraform import — run `terraform show` to see full config\n"
    "}}\n"
)


class ImportWizard:
    """Guide the user through importing existing infrastructure into Terraform.

    Args:
        binary:  Path to the terraform executable.
        timeout: Per-operation timeout in seconds.
    """

    def __init__(self, binary: str = "terraform", timeout: int = 300):
        self.binary = binary
        self.timeout = timeout
        self._env = dict(os.environ)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_import_config(
        self,
        resource_type: str,
        resource_id: str,
        tf_name: str,
    ) -> str:
        """Generate a minimal HCL stub for the given resource.

        Args:
            resource_type: Terraform resource type, e.g. "aws_instance".
            resource_id:   Cloud provider resource ID, e.g. "i-0abc123".
            tf_name:       Desired Terraform logical name, e.g. "web".

        Returns:
            HCL string with a placeholder resource block.
        """
        template = _HCL_STUBS.get(resource_type, _DEFAULT_STUB)
        hcl = template.format(name=tf_name, resource_type=resource_type)
        comment = f"# Import source: {resource_type} ID={resource_id}\n"
        return comment + hcl

    async def run_import(
        self,
        resource_type: str,
        resource_id: str,
        tf_address: str,
        workspace_dir: str | Path,
    ) -> dict:
        """Run `terraform import <tf_address> <resource_id>`.

        Args:
            resource_type:  Resource type label (informational only).
            resource_id:    Provider resource ID to import.
            tf_address:     Terraform resource address, e.g. "aws_instance.web".
            workspace_dir:  Directory containing terraform configuration.

        Returns:
            Dict with keys: success, address, resource_id, output, error.
        """
        ws_dir = Path(workspace_dir).resolve()
        if not ws_dir.exists():
            return {
                "success": False,
                "address": tf_address,
                "resource_id": resource_id,
                "output": "",
                "error": f"Workspace directory not found: {ws_dir}",
            }

        cmd = [self.binary, "import", "-no-color", tf_address, resource_id]
        result = await run_process(cmd, ws_dir, self._env, self.timeout)

        if not result.success:
            return {
                "success": False,
                "address": tf_address,
                "resource_id": resource_id,
                "output": result.stdout,
                "error": result.stderr.strip() or f"terraform import exited {result.return_code}",
            }

        logger.info("Imported %s as %s", resource_id, tf_address)
        return {
            "success": True,
            "address": tf_address,
            "resource_id": resource_id,
            "output": result.stdout,
            "error": "",
        }

    async def bulk_import(
        self,
        mapping: list[dict],
        workspace_dir: str | Path,
    ) -> list[dict]:
        """Import multiple resources sequentially.

        Each entry in *mapping* must have keys:
          - resource_type  (str)
          - resource_id    (str)
          - tf_address     (str)

        Args:
            mapping:       List of import target dicts.
            workspace_dir: Directory containing terraform configuration.

        Returns:
            List of result dicts in the same order as *mapping*.
        """
        results: list[dict] = []
        for item in mapping:
            res = await self.run_import(
                resource_type=item.get("resource_type", ""),
                resource_id=item["resource_id"],
                tf_address=item["tf_address"],
                workspace_dir=workspace_dir,
            )
            results.append(res)
        return results
