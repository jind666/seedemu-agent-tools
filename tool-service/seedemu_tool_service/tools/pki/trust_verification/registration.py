"""Registry bindings for certificate trust verification PKI tools."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.models.tool import ToolDefinition
from seedemu_tool_service.registry import ToolRegistry
from seedemu_tool_service.tools.pki.trust_verification.models import (
    VerifyCertificateChainArguments,
)
from seedemu_tool_service.tools.pki.trust_verification.tools import TrustVerificationTools


def register_trust_verification_tools(
    registry: ToolRegistry,
    backend: RuntimeBackend,
) -> None:
    """Register certificate trust verification tools."""

    tools = TrustVerificationTools(backend)
    registry.register(
        definition=ToolDefinition(
            name="pki.verify_certificate_chain",
            domain="pki",
            description="Verify a certificate chain against trusted CA material.",
        ),
        handler=tools.verify_certificate_chain,
        arguments_model=VerifyCertificateChainArguments,
    )

