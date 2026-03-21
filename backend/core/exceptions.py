"""Custom exceptions for TerraBot core engine.

Each exception carries structured context for logging and API error responses.
"""
from pathlib import Path


class TerrabotError(Exception):
    """Base exception for all TerraBot errors."""

    def __init__(self, message: str, **context):
        super().__init__(message)
        self.message = message
        self.context = context

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, context={self.context})"


class TerraformError(TerrabotError):
    """Raised when a terraform subprocess command fails.

    Attributes:
        command: The terraform subcommand that failed (e.g. 'apply').
        working_dir: Workspace directory where the command ran.
        return_code: Process exit code.
        stderr: Captured stderr output from terraform.
    """

    def __init__(
        self,
        message: str,
        command: str = "",
        working_dir: Path | str = "",
        return_code: int = -1,
        stderr: str = "",
    ):
        super().__init__(
            message,
            command=command,
            working_dir=str(working_dir),
            return_code=return_code,
            stderr=stderr,
        )
        self.command = command
        self.working_dir = working_dir
        self.return_code = return_code
        self.stderr = stderr


class ValidationError(TerrabotError):
    """Raised when HCL syntax validation fails or resource whitelist is violated.

    Attributes:
        violations: List of human-readable violation descriptions.
    """

    def __init__(self, message: str, violations: list[str] | None = None):
        super().__init__(message, violations=violations or [])
        self.violations = violations or []


class TemplateError(TerrabotError):
    """Raised when a template cannot be found, loaded, or rendered.

    Attributes:
        template_name: The template identifier that caused the error.
    """

    def __init__(self, message: str, template_name: str = ""):
        super().__init__(message, template_name=template_name)
        self.template_name = template_name


class ConfigError(TerrabotError):
    """Raised when application configuration is invalid or missing.

    Attributes:
        field: The settings field that is invalid or missing.
    """

    def __init__(self, message: str, field: str = ""):
        super().__init__(message, field=field)
        self.field = field


class TimeoutError(TerrabotError):  # noqa: A001 — intentional override of builtin
    """Raised when a terraform operation exceeds the configured timeout.

    Attributes:
        command: The terraform subcommand that timed out.
        timeout_seconds: Configured timeout limit.
    """

    def __init__(self, message: str, command: str = "", timeout_seconds: int = 0):
        super().__init__(message, command=command, timeout_seconds=timeout_seconds)
        self.command = command
        self.timeout_seconds = timeout_seconds
