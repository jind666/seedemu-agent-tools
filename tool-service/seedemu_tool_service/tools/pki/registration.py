"""Registration entry point for PKI-domain tools."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.registry import ToolRegistry
from seedemu_tool_service.tools.pki.certificate_inspection import (
    register_certificate_inspection_tools,
)
from seedemu_tool_service.tools.pki.expiration import register_expiration_tools
from seedemu_tool_service.tools.pki.remote_tls import register_remote_tls_tools
from seedemu_tool_service.tools.pki.trust_verification import (
    register_trust_verification_tools,
)


def register_pki_tools(registry: ToolRegistry, backend: RuntimeBackend) -> None:
    """Register all implemented PKI tool categories."""

    register_certificate_inspection_tools(registry, backend)
    register_remote_tls_tools(registry, backend)
    register_trust_verification_tools(registry, backend)
    register_expiration_tools(registry, backend)

