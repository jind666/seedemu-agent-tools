"""Argument and result models for PKI-domain tools."""

from pydantic import BaseModel, ConfigDict, Field


class ToolArguments(BaseModel):
    """Base model for strict PKI tool argument validation."""

    model_config = ConfigDict(extra="forbid")


class InspectCertificateFileArguments(ToolArguments):
    """Arguments accepted by the certificate-file inspection tool."""

    source: str = Field(description="Name or ID of the emulated source container")
    path: str = Field(min_length=1, description="Certificate path inside the source container")


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


class VerifyCertificateChainArguments(ToolArguments):
    """Arguments accepted by the certificate-chain verification tool."""

    source: str = Field(description="Name or ID of the emulated source container")
    certificate_path: str = Field(min_length=1, description="Certificate path inside the source")
    ca_file_path: str | None = Field(
        default=None,
        description="Optional CA bundle file path inside the source container",
    )
    ca_directory_path: str | None = Field(
        default=None,
        description="Optional hashed CA certificate directory inside the source container",
    )
    untrusted_chain_path: str | None = Field(
        default=None,
        description="Optional intermediate certificate chain path inside the source container",
    )


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


class CertificateFields(BaseModel):
    """Common parsed X.509 certificate fields."""

    subject: str | None = None
    issuer: str | None = None
    serial: str | None = None
    not_before: str | None = None
    not_after: str | None = None
    fingerprint_sha256: str | None = None


class CertificateInspectionResult(BaseModel):
    """Result of inspecting an X.509 certificate file."""

    source: str
    path: str
    successful: bool
    certificate: CertificateFields
    details: str
    exit_code: int
    stderr: str


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


class CertificateChainVerificationResult(BaseModel):
    """Result of verifying a certificate chain against trusted CA material."""

    source: str
    certificate_path: str
    ca_file_path: str | None
    ca_directory_path: str | None
    untrusted_chain_path: str | None
    trusted: bool
    output: str
    exit_code: int
    stderr: str


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
