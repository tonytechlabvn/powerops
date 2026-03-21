"""Unit tests for backend.core.hcl-validator."""
from __future__ import annotations

import pytest

from backend.core.hcl_validator import (
    DEFAULT_ALLOWED_RESOURCES,
    check_resource_whitelist,
    parse_resources,
    validate_syntax,
)
from backend.core.models import Resource


# ---------------------------------------------------------------------------
# validate_syntax
# ---------------------------------------------------------------------------


def test_validate_syntax_valid_hcl(sample_valid_hcl: str) -> None:
    result = validate_syntax(sample_valid_hcl)
    assert result.valid is True
    assert result.errors == []


def test_validate_syntax_invalid_hcl(sample_invalid_hcl: str) -> None:
    result = validate_syntax(sample_invalid_hcl)
    assert result.valid is False
    assert len(result.errors) > 0


def test_validate_syntax_empty_string() -> None:
    result = validate_syntax("")
    assert result.valid is True


# ---------------------------------------------------------------------------
# parse_resources
# ---------------------------------------------------------------------------


def test_parse_resources_extracts_types_and_names(sample_valid_hcl: str) -> None:
    resources = parse_resources(sample_valid_hcl)
    assert len(resources) == 2
    types = {r.type for r in resources}
    names = {r.name for r in resources}
    assert "aws_instance" in types
    assert "aws_security_group" in types
    assert "web" in names


def test_parse_resources_returns_address(sample_valid_hcl: str) -> None:
    resources = parse_resources(sample_valid_hcl)
    addresses = {r.address for r in resources}
    assert "aws_instance.web" in addresses
    assert "aws_security_group.web" in addresses


def test_parse_resources_invalid_hcl_returns_empty(sample_invalid_hcl: str) -> None:
    resources = parse_resources(sample_invalid_hcl)
    assert resources == []


def test_parse_resources_empty_string_returns_empty() -> None:
    assert parse_resources("") == []


# ---------------------------------------------------------------------------
# check_resource_whitelist
# ---------------------------------------------------------------------------


def test_check_resource_whitelist_all_allowed(sample_valid_hcl: str) -> None:
    resources = parse_resources(sample_valid_hcl)
    violations = check_resource_whitelist(resources)
    assert violations == []


def test_check_resource_whitelist_detects_disallowed() -> None:
    bad = [Resource(type="aws_nonexistent", name="bad", address="aws_nonexistent.bad")]
    violations = check_resource_whitelist(bad)
    assert len(violations) == 1
    assert violations[0].resource_type == "aws_nonexistent"
    assert violations[0].resource_name == "bad"


def test_check_resource_whitelist_custom_allowed() -> None:
    resource = [Resource(type="my_custom_resource", name="x", address="my_custom_resource.x")]
    # Default — violation expected
    assert len(check_resource_whitelist(resource)) == 1
    # Custom whitelist — no violation
    assert check_resource_whitelist(resource, allowed={"my_custom_resource"}) == []


def test_check_resource_whitelist_empty_list() -> None:
    assert check_resource_whitelist([]) == []


# ---------------------------------------------------------------------------
# DEFAULT_ALLOWED_RESOURCES whitelist content
# ---------------------------------------------------------------------------


def test_default_whitelist_contains_common_aws_resources() -> None:
    for rtype in ("aws_instance", "aws_vpc", "aws_security_group", "aws_s3_bucket"):
        assert rtype in DEFAULT_ALLOWED_RESOURCES


def test_default_whitelist_contains_proxmox_resources() -> None:
    assert "proxmox_vm_qemu" in DEFAULT_ALLOWED_RESOURCES
    assert "proxmox_lxc" in DEFAULT_ALLOWED_RESOURCES
