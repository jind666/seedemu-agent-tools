"""Models for certificate trust verification PKI tools."""

from pydantic import BaseModel, Field

from seedemu_tool_service.tools.pki.shared.models import ToolArguments


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

