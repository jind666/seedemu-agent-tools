"""Registry bindings for certificate expiration PKI tools."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.models.tool import ToolDefinition
from seedemu_tool_service.registry import ToolRegistry
from seedemu_tool_service.tools.pki.expiration.models import (
    CheckCertificateExpirationArguments,
)
from seedemu_tool_service.tools.pki.expiration.tools import ExpirationTools


def register_expiration_tools(registry: ToolRegistry, backend: RuntimeBackend) -> None:
    """Register certificate expiration tools."""

    tools = ExpirationTools(backend)
    registry.register(
        definition=ToolDefinition(
            name="pki.check_certificate_expiration",
            domain="pki",
            description="Check whether a certificate is expired or near expiration.",
        ),
        handler=tools.check_certificate_expiration,
        arguments_model=CheckCertificateExpirationArguments,
    )

