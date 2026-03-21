"""Shared pytest fixtures for TerraBot test suite."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@pytest.fixture
def sample_valid_hcl() -> str:
    return (_FIXTURES_DIR / "sample-hcl" / "valid-ec2.tf").read_text(encoding="utf-8")


@pytest.fixture
def sample_invalid_hcl() -> str:
    return (_FIXTURES_DIR / "sample-hcl" / "invalid-syntax.tf").read_text(encoding="utf-8")


@pytest.fixture
def sample_plan_json() -> dict:
    return json.loads(
        (_FIXTURES_DIR / "terraform-output" / "plan-create.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def sample_apply_json() -> dict:
    return json.loads(
        (_FIXTURES_DIR / "terraform-output" / "apply-success.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def template_dir(tmp_path: Path) -> Path:
    """Copy real templates into a temp directory for isolated engine tests."""
    dest = tmp_path / "templates"
    shutil.copytree(_TEMPLATES_DIR, dest)
    return dest
