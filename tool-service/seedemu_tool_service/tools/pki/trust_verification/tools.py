"""Certificate trust verification PKI tool implementations."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.tools.pki.trust_verification.models import (
    CertificateChainVerificationResult,
)


class TrustVerificationTools:
    """Bound-method tools for certificate trust verification."""

    def __init__(self, backend: RuntimeBackend) -> None:
        self._backend = backend

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

