"""Certificate expiration PKI tool implementations."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.tools.pki.expiration.models import CertificateExpirationResult
from seedemu_tool_service.tools.pki.shared.parsing import parse_prefixed_value


class ExpirationTools:
    """Bound-method tools for certificate expiration checks."""

    def __init__(self, backend: RuntimeBackend) -> None:
        self._backend = backend

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
            not_after=parse_prefixed_value(details, "notAfter"),
            details=details,
            exit_code=result.exit_code,
            stderr=result.stderr,
        )

