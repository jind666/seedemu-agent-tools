"""PKI-domain tool tests."""

from collections.abc import Sequence

import anyio

from seedemu_tool_service.models.runtime import RuntimeCommandResult, RuntimeStatus
from seedemu_tool_service.registry import ToolRegistry
from seedemu_tool_service.tools.pki import register_pki_tools


class FakeRuntimeBackend:
    def __init__(self, result: RuntimeCommandResult | None = None) -> None:
        self.result = result or RuntimeCommandResult(
            exit_code=0,
            stdout=(
                "subject=CN=example.test\n"
                "issuer=CN=Example CA\n"
                "serial=01\n"
                "notBefore=Aug 20 00:00:00 2026 GMT\n"
                "notAfter=Aug 20 00:00:00 2027 GMT\n"
                "sha256 Fingerprint=AA:BB:CC\n"
            ),
            stderr="",
        )
        self.container: str | None = None
        self.command: list[str] | None = None

    def status(self) -> RuntimeStatus:
        return RuntimeStatus(backend="fake", available=True)

    def execute(self, container: str, command: Sequence[str]) -> RuntimeCommandResult:
        self.container = container
        self.command = list(command)
        return self.result


def test_pki_domain_registers_certificate_tool() -> None:
    registry = ToolRegistry()

    register_pki_tools(registry, FakeRuntimeBackend())

    definitions = registry.list_tools()
    assert [tool.name for tool in definitions] == [
        "pki.check_certificate_expiration",
        "pki.inspect_certificate_file",
        "pki.inspect_remote_tls_certificate",
        "pki.verify_certificate_chain",
    ]
    assert definitions[0].domain == "pki"
    assert set(definitions[1].input_schema["properties"]) == {"source", "path"}


def test_inspect_certificate_executes_openssl_in_source() -> None:
    backend = FakeRuntimeBackend()
    registry = ToolRegistry()
    register_pki_tools(registry, backend)

    result = anyio.run(
        registry.invoke,
        "pki.inspect_certificate_file",
        {"source": "web-server", "path": "/etc/ssl/certs/server.pem"},
    )

    assert backend.container == "web-server"
    assert backend.command == [
        "openssl",
        "x509",
        "-in",
        "/etc/ssl/certs/server.pem",
        "-noout",
        "-subject",
        "-issuer",
        "-serial",
        "-dates",
        "-fingerprint",
        "-sha256",
    ]
    assert result.successful is True
    assert "subject=CN=example.test" in result.details
    assert result.certificate.subject == "CN=example.test"
    assert result.certificate.issuer == "CN=Example CA"
    assert result.certificate.fingerprint_sha256 == "AA:BB:CC"


def test_inspect_certificate_reports_command_failure() -> None:
    backend = FakeRuntimeBackend(
        RuntimeCommandResult(exit_code=1, stdout="", stderr="unable to load certificate")
    )
    registry = ToolRegistry()
    register_pki_tools(registry, backend)

    result = anyio.run(
        registry.invoke,
        "pki.inspect_certificate_file",
        {"source": "web-server", "path": "/missing.pem"},
    )

    assert result.successful is False
    assert result.stderr == "unable to load certificate"


def test_inspect_remote_tls_certificate_executes_s_client_from_source() -> None:
    backend = FakeRuntimeBackend()
    registry = ToolRegistry()
    register_pki_tools(registry, backend)

    result = anyio.run(
        registry.invoke,
        "pki.inspect_remote_tls_certificate",
        {
            "source": "client",
            "target": "web1",
            "port": 443,
            "server_name": "www.example.test",
            "timeout_seconds": 7,
        },
    )

    assert backend.container == "client"
    assert backend.command == [
        "timeout",
        "7",
        "openssl",
        "s_client",
        "-connect",
        "web1:443",
        "-showcerts",
        "-servername",
        "www.example.test",
    ]
    assert result.successful is True
    assert result.certificate.not_after == "Aug 20 00:00:00 2027 GMT"


def test_inspect_remote_tls_certificate_can_omit_server_name() -> None:
    backend = FakeRuntimeBackend()
    registry = ToolRegistry()
    register_pki_tools(registry, backend)

    result = anyio.run(
        registry.invoke,
        "pki.inspect_remote_tls_certificate",
        {"source": "client", "target": "web1"},
    )

    assert backend.command == [
        "timeout",
        "5",
        "openssl",
        "s_client",
        "-connect",
        "web1:443",
        "-showcerts",
    ]
    assert result.server_name is None


def test_verify_certificate_chain_executes_openssl_verify() -> None:
    backend = FakeRuntimeBackend(
        RuntimeCommandResult(exit_code=0, stdout="/tmp/server.pem: OK\n", stderr="")
    )
    registry = ToolRegistry()
    register_pki_tools(registry, backend)

    result = anyio.run(
        registry.invoke,
        "pki.verify_certificate_chain",
        {
            "source": "client",
            "certificate_path": "/tmp/server.pem",
            "ca_file_path": "/etc/ssl/certs/ca.pem",
            "untrusted_chain_path": "/tmp/intermediate.pem",
        },
    )

    assert backend.command == [
        "openssl",
        "verify",
        "-CAfile",
        "/etc/ssl/certs/ca.pem",
        "-untrusted",
        "/tmp/intermediate.pem",
        "/tmp/server.pem",
    ]
    assert result.trusted is True
    assert result.output == "/tmp/server.pem: OK\n"


def test_verify_certificate_chain_reports_untrusted_certificate() -> None:
    backend = FakeRuntimeBackend(
        RuntimeCommandResult(exit_code=2, stdout="", stderr="certificate verify failed")
    )
    registry = ToolRegistry()
    register_pki_tools(registry, backend)

    result = anyio.run(
        registry.invoke,
        "pki.verify_certificate_chain",
        {"source": "client", "certificate_path": "/tmp/server.pem"},
    )

    assert result.trusted is False
    assert result.stderr == "certificate verify failed"


def test_check_certificate_expiration_reports_valid_certificate() -> None:
    backend = FakeRuntimeBackend(
        RuntimeCommandResult(
            exit_code=0,
            stdout=(
                "notAfter=Aug 20 00:00:00 2027 GMT\n"
                "Certificate will not expire\n"
            ),
            stderr="",
        )
    )
    registry = ToolRegistry()
    register_pki_tools(registry, backend)

    result = anyio.run(
        registry.invoke,
        "pki.check_certificate_expiration",
        {"source": "web-server", "path": "/etc/ssl/certs/server.pem"},
    )

    assert backend.command == [
        "openssl",
        "x509",
        "-in",
        "/etc/ssl/certs/server.pem",
        "-noout",
        "-enddate",
        "-checkend",
        "0",
    ]
    assert result.successful is True
    assert result.expired is False
    assert result.expires_within_warning_window is False
    assert result.not_after == "Aug 20 00:00:00 2027 GMT"


def test_check_certificate_expiration_reports_warning_window() -> None:
    backend = FakeRuntimeBackend(
        RuntimeCommandResult(
            exit_code=1,
            stdout="notAfter=Aug 20 00:00:00 2026 GMT\nCertificate will expire\n",
            stderr="",
        )
    )
    registry = ToolRegistry()
    register_pki_tools(registry, backend)

    result = anyio.run(
        registry.invoke,
        "pki.check_certificate_expiration",
        {
            "source": "web-server",
            "path": "/etc/ssl/certs/server.pem",
            "warning_seconds": 86400,
        },
    )

    assert backend.command[-1] == "86400"
    assert result.expired is None
    assert result.expires_within_warning_window is True
