"""Unit tests for AI Template Studio service and helpers.

Tests parsing utilities, dataclasses, validation, and save/load operations.
Claude API calls are mocked for deterministic testing.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Module loading helpers (kebab-case files)
# ---------------------------------------------------------------------------

def _load_helpers():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-template-studio-helpers.py", "ai_template_studio_helpers")


def _load_studio():
    from backend.core import load_kebab_module
    return load_kebab_module("ai-template-studio.py", "ai_template_studio")


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestTemplateStudioHelpers:
    """Test parsing and validation utilities."""

    def test_parse_template_files_extracts_file_tags(self):
        h = _load_helpers()
        raw = '<file name="main.tf.j2">resource "aws_instance" "web" {}</file>'
        files = h.parse_template_files(raw)
        assert "main.tf.j2" in files
        assert 'aws_instance' in files["main.tf.j2"]

    def test_parse_template_files_handles_multiple_files(self):
        h = _load_helpers()
        raw = (
            '<file name="main.tf.j2">{{ instance_type }}</file>\n'
            '<file name="variables.json">{"variables": []}</file>\n'
            '<file name="metadata.json">{"name": "test"}</file>'
        )
        files = h.parse_template_files(raw)
        assert len(files) == 3
        assert "main.tf.j2" in files
        assert "variables.json" in files
        assert "metadata.json" in files

    def test_parse_template_files_returns_empty_on_no_tags(self):
        h = _load_helpers()
        files = h.parse_template_files("Just some random text without tags")
        assert files == {}

    def test_parse_variables_json_dict_format(self):
        h = _load_helpers()
        raw = json.dumps({"variables": [{"name": "region", "type": "string", "default": "us-east-1"}]})
        variables = h.parse_variables_json(raw)
        assert len(variables) == 1
        assert variables[0]["name"] == "region"

    def test_parse_variables_json_list_format(self):
        h = _load_helpers()
        raw = json.dumps([{"name": "port", "type": "number", "default": 8080}])
        variables = h.parse_variables_json(raw)
        assert len(variables) == 1
        assert variables[0]["name"] == "port"

    def test_parse_variables_json_invalid_returns_empty(self):
        h = _load_helpers()
        assert h.parse_variables_json("not json") == []
        assert h.parse_variables_json("") == []

    def test_parse_metadata_json_valid(self):
        h = _load_helpers()
        raw = json.dumps({"name": "aws/test", "provider": "aws", "tags": ["test"]})
        meta = h.parse_metadata_json(raw)
        assert meta["name"] == "aws/test"
        assert meta["provider"] == "aws"

    def test_parse_metadata_json_invalid_returns_empty(self):
        h = _load_helpers()
        assert h.parse_metadata_json("not json") == {}

    def test_validate_jinja2_syntax_valid(self):
        h = _load_helpers()
        errors = h.validate_jinja2_syntax("{{ variable_name }}")
        assert errors == []

    def test_validate_jinja2_syntax_with_conditionals(self):
        h = _load_helpers()
        errors = h.validate_jinja2_syntax("{% if auto_mode %}enabled{% endif %}")
        assert errors == []

    def test_validate_jinja2_syntax_catches_errors(self):
        h = _load_helpers()
        errors = h.validate_jinja2_syntax("{{ broken")
        assert len(errors) > 0

    def test_validate_template_structure_all_present(self):
        h = _load_helpers()
        files = {
            "main.tf.j2": "resource {}",
            "variables.json": json.dumps({"variables": [{"name": "x"}]}),
            "metadata.json": '{"name": "test"}',
        }
        warnings = h.validate_template_structure(files)
        assert warnings == []

    def test_validate_template_structure_flags_missing_main(self):
        h = _load_helpers()
        files = {"variables.json": "{}"}
        warnings = h.validate_template_structure(files)
        assert any("main.tf.j2" in w for w in warnings)

    def test_validate_template_structure_flags_empty_main(self):
        h = _load_helpers()
        files = {"main.tf.j2": "", "variables.json": "{}", "metadata.json": "{}"}
        warnings = h.validate_template_structure(files)
        assert any("empty" in w.lower() for w in warnings)

    def test_generated_template_dataclass(self):
        h = _load_helpers()
        t = h.GeneratedTemplate(
            name="aws/test",
            providers=["aws"],
            description="Test template",
            files={"main.tf.j2": "resource {}"},
            tags=["test"],
        )
        assert t.name == "aws/test"
        assert t.providers == ["aws"]
        assert "main.tf.j2" in t.files
        assert t.version == "1.0.0"


# ---------------------------------------------------------------------------
# Service tests (mocked Claude)
# ---------------------------------------------------------------------------

class TestAITemplateStudio:
    """Test service methods with mocked Claude API."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock LLMClient for testing."""
        return MagicMock()

    @pytest.fixture
    def studio(self, mock_client, tmp_path):
        studio_mod = _load_studio()
        return studio_mod.AITemplateStudio(
            client=mock_client,
            template_dir=tmp_path / "templates",
            max_tokens=4096,
        )

    def _mock_llm_response(self, text: str):
        """Create a mock LLMResponse with given text content."""
        from backend.core.llm import LLMResponse, LLMUsage
        return LLMResponse(text=text, usage=LLMUsage(input_tokens=100, output_tokens=200))

    @pytest.mark.asyncio
    async def test_generate_template_returns_generated_template(self, studio):
        raw_response = (
            '<file name="main.tf.j2">resource "aws_instance" "web" { instance_type = "{{ instance_type }}" }</file>\n'
            '<file name="variables.json">{"variables": [{"name": "instance_type", "type": "string", "default": "t3.micro"}]}</file>\n'
            '<file name="metadata.json">{"name": "aws/ec2-web", "provider": "aws", "display_name": "EC2 Web Server"}</file>'
        )
        studio._client.complete = AsyncMock(return_value=self._mock_llm_response(raw_response))

        result = await studio.generate_template("Simple EC2 web server", ["aws"], "simple")
        assert result.providers == ["aws"]
        assert "main.tf.j2" in result.files
        assert "variables.json" in result.files

    @pytest.mark.asyncio
    async def test_extract_template_parameterizes_values(self, studio):
        raw_response = (
            '<file name="main.tf.j2">resource "aws_instance" "web" { instance_type = "{{ instance_type }}" }</file>\n'
            '<file name="variables.json">{"variables": [{"name": "instance_type", "type": "string", "default": "t3.micro"}]}</file>\n'
            '<file name="metadata.json">{"name": "aws/extracted", "provider": "aws"}</file>'
        )
        studio._client.complete = AsyncMock(return_value=self._mock_llm_response(raw_response))

        hcl = 'resource "aws_instance" "web" { instance_type = "t3.micro" }'
        result = await studio.extract_template(hcl)
        assert "main.tf.j2" in result.files

    @pytest.mark.asyncio
    async def test_refine_template_preserves_name(self, studio):
        h = _load_helpers()
        current = h.GeneratedTemplate(
            name="aws/original",
            providers=["aws"],
            description="Original",
            files={"main.tf.j2": "original content"},
        )
        raw_response = '<file name="main.tf.j2">refined content</file>'
        studio._client.complete = AsyncMock(return_value=self._mock_llm_response(raw_response))

        result = await studio.refine_template(current, "Add a VPC")
        assert result.name == "aws/original"
        assert "refined" in result.files.get("main.tf.j2", "")

    def test_save_template_writes_files(self, studio, tmp_path):
        h = _load_helpers()
        template = h.GeneratedTemplate(
            name="aws/test-save",
            providers=["aws"],
            description="Test",
            files={
                "main.tf.j2": "resource {}",
                "variables.json": "{}",
                "metadata.json": "{}",
            },
        )
        path = studio.save_template(template)
        assert Path(path).exists()
        assert (Path(path) / "main.tf.j2").exists()

    def test_save_template_rejects_path_traversal(self, studio):
        h = _load_helpers()
        template = h.GeneratedTemplate(
            name="../../../etc/passwd",
            providers=["aws"],
            description="Malicious",
            files={"main.tf.j2": "hack"},
        )
        with pytest.raises(ValueError, match="path traversal"):
            studio.save_template(template)

    def test_save_template_rejects_overwrite_by_default(self, studio, tmp_path):
        h = _load_helpers()
        template = h.GeneratedTemplate(
            name="aws/no-overwrite",
            providers=["aws"],
            description="Test",
            files={"main.tf.j2": "content"},
        )
        studio.save_template(template)
        with pytest.raises(ValueError, match="already exists"):
            studio.save_template(template)

    def test_load_template_reads_files(self, studio, tmp_path):
        h = _load_helpers()
        # Write files first
        template = h.GeneratedTemplate(
            name="aws/test-load",
            providers=["aws"],
            description="Load test",
            files={
                "main.tf.j2": "resource {}",
                "variables.json": '{"variables": []}',
                "metadata.json": '{"name": "aws/test-load", "provider": "aws"}',
            },
        )
        studio.save_template(template)

        # Load and verify roundtrip
        loaded = studio.load_template("aws/test-load")
        assert loaded is not None
        assert loaded.name == "aws/test-load"
        assert "main.tf.j2" in loaded.files

    def test_load_template_returns_none_for_missing(self, studio):
        result = studio.load_template("aws/nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_validate_template_catches_jinja2_errors(self, studio):
        h = _load_helpers()
        template = h.GeneratedTemplate(
            name="aws/broken",
            providers=["aws"],
            description="Broken",
            files={"main.tf.j2": "{{ broken", "variables.json": "{}", "metadata.json": "{}"},
        )
        result = await studio.validate_template(template)
        assert not result.valid
        assert len(result.jinja2_errors) > 0

    @pytest.mark.asyncio
    async def test_validate_template_passes_valid(self, studio):
        h = _load_helpers()
        template = h.GeneratedTemplate(
            name="aws/valid",
            providers=["aws"],
            description="Valid",
            files={
                "main.tf.j2": '{{ instance_type }}',
                "variables.json": '{"variables": [{"name": "instance_type", "default": "t3.micro"}]}',
                "metadata.json": '{}',
            },
        )
        result = await studio.validate_template(template)
        assert len(result.jinja2_errors) == 0
