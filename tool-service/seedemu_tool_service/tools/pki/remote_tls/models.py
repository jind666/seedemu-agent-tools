"""Models for remote TLS PKI tools."""

from pydantic import BaseModel, Field

from seedemu_tool_service.tools.pki.shared.models import CertificateFields, ToolArguments


class InspectRemoteTLSCertificateArguments(ToolArguments):
    """Arguments accepted by the remote TLS certificate inspection tool."""

    source: str = Field(description="Name or ID of the emulated source container")
    target: str = Field(min_length=1, description="TLS service host or address to connect to")
    port: int = Field(default=443, ge=1, le=65535, description="TLS service port")
    server_name: str | None = Field(
        default=None,
        description="Optional Server Name Indication value for virtual-hosted TLS services",
    )
    timeout_seconds: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Maximum time allowed for the TLS connection attempt",
    )


class RemoteTLSCertificateInspectionResult(BaseModel):
    """Result of inspecting the certificate presented by a TLS service."""

    source: str
    target: str
    port: int
    server_name: str | None
    successful: bool
    certificate: CertificateFields
    details: str
    exit_code: int
    stderr: str

