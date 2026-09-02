"""Models for certificate expiration PKI tools."""

from pydantic import BaseModel, Field

from seedemu_tool_service.tools.pki.shared.models import ToolArguments


class CheckCertificateExpirationArguments(ToolArguments):
    """Arguments accepted by the certificate-expiration check tool."""

    source: str = Field(description="Name or ID of the emulated source container")
    path: str = Field(min_length=1, description="Certificate path inside the source container")
    warning_seconds: int = Field(
        default=0,
        ge=0,
        le=31_536_000,
        description="Warn if the certificate expires within this many seconds",
    )


class CertificateExpirationResult(BaseModel):
    """Result of checking a certificate's expiration window."""

    source: str
    path: str
    successful: bool
    expired: bool | None
    expires_within_warning_window: bool | None
    not_after: str | None
    details: str
    exit_code: int
    stderr: str

