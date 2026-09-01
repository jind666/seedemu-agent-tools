"""Registry bindings for remote TLS PKI tools."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.models.tool import ToolDefinition
from seedemu_tool_service.registry import ToolRegistry
from seedemu_tool_service.tools.pki.remote_tls.models import (
    InspectRemoteTLSCertificateArguments,
)
from seedemu_tool_service.tools.pki.remote_tls.tools import RemoteTLSTools


def register_remote_tls_tools(registry: ToolRegistry, backend: RuntimeBackend) -> None:
    """Register remote TLS inspection tools."""

    tools = RemoteTLSTools(backend)
    registry.register(
        definition=ToolDefinition(
            name="pki.inspect_remote_tls_certificate",
            domain="pki",
            description="Inspect the certificate presented by a remote TLS service.",
        ),
        handler=tools.inspect_remote_tls_certificate,
        arguments_model=InspectRemoteTLSCertificateArguments,
    )

