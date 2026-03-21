"""Unit tests for backend.core.template-engine."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.core import template_engine as te
from backend.core.exceptions import TemplateError, ValidationError
from backend.core.models import Template, TemplateMetadata, TemplateVariable


def _patch_template_root(tmp_dir: Path):
    """Context manager: override _template_root() to use tmp_dir."""
    return patch.object(te, "_template_root", return_value=tmp_dir)


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------


def test_list_templates_returns_all(template_dir: Path) -> None:
    with _patch_template_root(template_dir):
        templates = te.list_templates()
    assert len(templates) > 0
    # All objects are Template instances
    assert all(isinstance(t, Template) for t in templates)


def test_list_templates_filter_by_provider(template_dir: Path) -> None:
    with _patch_template_root(template_dir):
        aws_templates = te.list_templates(provider="aws")
        proxmox_templates = te.list_templates(provider="proxmox")

    assert len(aws_templates) > 0
    assert all(t.metadata.provider == "aws" for t in aws_templates)
    assert len(proxmox_templates) > 0
    assert all(t.metadata.provider == "proxmox" for t in proxmox_templates)


def test_list_templates_unknown_provider_returns_empty(template_dir: Path) -> None:
    with _patch_template_root(template_dir):
        result = te.list_templates(provider="unknown_provider")
    assert result == []


def test_list_templates_missing_root_returns_empty(tmp_path: Path) -> None:
    nonexistent = tmp_path / "no-templates"
    with _patch_template_root(nonexistent):
        result = te.list_templates()
    assert result == []


# ---------------------------------------------------------------------------
# get_template
# ---------------------------------------------------------------------------


def test_get_template_returns_metadata_and_variables(template_dir: Path) -> None:
    with _patch_template_root(template_dir):
        tmpl = te.get_template("aws/ec2-web-server")

    assert isinstance(tmpl, Template)
    assert tmpl.metadata.name == "aws/ec2-web-server"
    assert tmpl.metadata.provider == "aws"
    assert len(tmpl.variables) > 0


def test_get_template_variables_have_required_fields(template_dir: Path) -> None:
    with _patch_template_root(template_dir):
        tmpl = te.get_template("aws/ec2-web-server")

    names = {v.name for v in tmpl.variables}
    assert "key_name" in names  # required, no default
    assert "instance_type" in names


def test_get_template_raises_for_missing(template_dir: Path) -> None:
    with _patch_template_root(template_dir):
        with pytest.raises(TemplateError):
            te.get_template("aws/does-not-exist")


# ---------------------------------------------------------------------------
# validate_variables
# ---------------------------------------------------------------------------


def _make_template_with_vars(*vars_: TemplateVariable) -> Template:
    meta = TemplateMetadata(name="test/tmpl", provider="test")
    return Template(metadata=meta, variables=list(vars_))


def test_validate_variables_passes_when_all_required_supplied() -> None:
    tmpl = _make_template_with_vars(
        TemplateVariable(name="key_name", type="string", required=True),
    )
    errors = te.validate_variables(tmpl, {"key_name": "my-key"})
    assert errors == []


def test_validate_variables_catches_missing_required() -> None:
    tmpl = _make_template_with_vars(
        TemplateVariable(name="key_name", type="string", required=True),
    )
    errors = te.validate_variables(tmpl, {})
    assert len(errors) == 1
    assert "key_name" in errors[0]


def test_validate_variables_optional_with_default_not_required() -> None:
    tmpl = _make_template_with_vars(
        TemplateVariable(name="region", type="string", default="us-east-1", required=False),
    )
    errors = te.validate_variables(tmpl, {})
    assert errors == []


def test_validate_variables_type_mismatch_reported() -> None:
    tmpl = _make_template_with_vars(
        TemplateVariable(name="count", type="number", required=True),
    )
    errors = te.validate_variables(tmpl, {"count": "not-a-number"})
    assert len(errors) == 1
    assert "count" in errors[0]


# ---------------------------------------------------------------------------
# render_template
# ---------------------------------------------------------------------------


def test_render_template_produces_valid_hcl(template_dir: Path) -> None:
    with _patch_template_root(template_dir):
        output = te.render_template("aws/ec2-web-server", {"key_name": "my-key"})

    assert "aws_instance" in output
    assert "aws_security_group" in output


def test_render_template_raises_validation_error_on_missing_required(
    template_dir: Path,
) -> None:
    with _patch_template_root(template_dir):
        with pytest.raises(ValidationError):
            te.render_template("aws/ec2-web-server", {})  # key_name is required


def test_render_template_raises_for_unknown_template(template_dir: Path) -> None:
    with _patch_template_root(template_dir):
        with pytest.raises(TemplateError):
            te.render_template("aws/ghost-template", {"key_name": "k"})
