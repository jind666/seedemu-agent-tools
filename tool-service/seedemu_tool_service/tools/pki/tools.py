"""PKI-domain tool implementations."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.tools.pki.models import (
    CertificateChainVerificationResult,
    CertificateExpirationResult,
    CertificateFields,
    CertificateInspectionResult,
    RemoteTLSCertificateInspectionResult,
)


class PKITools:
    """Bound-method tools for PKI inspection and operations."""

    def __init__(self, backend: RuntimeBackend) -> None:
        self._backend = backend

    def inspect_certificate_file(
        self,
        source: str,
        path: str,
    ) -> CertificateInspectionResult:
        """Inspect an X.509 certificate file inside an emulated node."""

        command = [
            "openssl",
            "x509",
            "-in",
            path,
            "-noout",
            "-subject",
            "-issuer",
            "-serial",
            "-dates",
            "-fingerprint",
            "-sha256",
        ]
        result = self._backend.execute(source, command)
        return CertificateInspectionResult(
            source=source,
            path=path,
            successful=result.exit_code == 0,
            certificate=_parse_certificate_fields(result.stdout),
            details=result.stdout,
            exit_code=result.exit_code,
            stderr=result.stderr,
        )

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
            certificate=_parse_certificate_fields(details),
            details=details,
            exit_code=result.exit_code,
            stderr=result.stderr,
        )

    def verify_certificate_chain(
        self,
        source: str,
        certificate_path: str,
        ca_file_path: str | None = None,
        ca_directory_path: str | None = None,
        untrusted_chain_path: str | None = None,
    ) -> CertificateChainVerificationResult:
        """Verify a certificate against CA material inside an emulated node."""

        command = ["openssl", "verify"]
        if ca_file_path is not None:
            command.extend(["-CAfile", ca_file_path])
        if ca_directory_path is not None:
            command.extend(["-CApath", ca_directory_path])
        if untrusted_chain_path is not None:
            command.extend(["-untrusted", untrusted_chain_path])
        command.append(certificate_path)

        result = self._backend.execute(source, command)
        return CertificateChainVerificationResult(
            source=source,
            certificate_path=certificate_path,
            ca_file_path=ca_file_path,
            ca_directory_path=ca_directory_path,
            untrusted_chain_path=untrusted_chain_path,
            trusted=result.exit_code == 0,
            output=result.stdout,
            exit_code=result.exit_code,
            stderr=result.stderr,
        )

    def check_certificate_expiration(
        self,
        source: str,
        path: str,
        warning_seconds: int = 0,
    ) -> CertificateExpirationResult:
        """Check whether a certificate is expired or near expiration."""

        command = [
            "openssl",
            "x509",
            "-in",
            path,
            "-noout",
            "-enddate",
            "-checkend",
            str(warning_seconds),
        ]
        result = self._backend.execute(source, command)
        details = result.stdout
        successful = "notAfter=" in details
        expires_within_window = result.exit_code != 0 if successful else None
        expired = expires_within_window if successful and warning_seconds == 0 else None

        return CertificateExpirationResult(
            source=source,
            path=path,
            successful=successful,
            expired=expired,
            expires_within_warning_window=expires_within_window,
            not_after=_parse_prefixed_value(details, "notAfter"),
            details=details,
            exit_code=result.exit_code,
            stderr=result.stderr,
        )


def _parse_certificate_fields(output: str) -> CertificateFields:
    """Extract common fields from OpenSSL text output when present."""

    return CertificateFields(
        subject=_parse_prefixed_value(output, "subject"),
        issuer=_parse_prefixed_value(output, "issuer"),
        serial=_parse_prefixed_value(output, "serial"),
        not_before=_parse_prefixed_value(output, "notBefore"),
        not_after=_parse_prefixed_value(output, "notAfter"),
        fingerprint_sha256=_parse_prefixed_value(output, "sha256 Fingerprint"),
    )


def _parse_prefixed_value(output: str, key: str) -> str | None:
    prefix = f"{key}="
    prefix_lower = prefix.lower()
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix_lower):
            return stripped[len(prefix) :].strip()
    return None
