"""Remote TLS PKI tool implementations."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.tools.pki.remote_tls.models import (
    RemoteTLSCertificateInspectionResult,
)
from seedemu_tool_service.tools.pki.shared.parsing import parse_certificate_fields


class RemoteTLSTools:
    """Bound-method tools for inspecting remote TLS services."""

    def __init__(self, backend: RuntimeBackend) -> None:
        self._backend = backend

    def inspect_remote_tls_certificate(
        self,
        source: str,
        target: str,
        port: int = 443,
        server_name: str | None = None,
        timeout_seconds: int = 5,
    ) -> RemoteTLSCertificateInspectionResult:
        """Inspect the certificate presented by a remote TLS service."""

        command = [
            "timeout",
            str(timeout_seconds),
            "openssl",
            "s_client",
            "-connect",
            f"{target}:{port}",
            "-showcerts",
        ]
        if server_name is not None:
            command.extend(["-servername", server_name])

        result = self._backend.execute(source, command)
        details = result.stdout
        return RemoteTLSCertificateInspectionResult(
            source=source,
            target=target,
            port=port,
            server_name=server_name,
            successful=result.exit_code == 0,
            certificate=parse_certificate_fields(details),
            details=details,
            exit_code=result.exit_code,
            stderr=result.stderr,
        )

