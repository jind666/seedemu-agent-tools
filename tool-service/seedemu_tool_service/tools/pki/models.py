"""Compatibility exports for PKI-domain argument and result models."""

from seedemu_tool_service.tools.pki.certificate_inspection.models import (
    CertificateExtensions,
    CertificateExtensionsResult,
    CertificateFingerprintResult,
    CertificateInspectionResult,
    CertificateNames,
    CertificateNamesResult,
    CertificatePublicKey,
    CertificatePublicKeyResult,
    GetCertificateFingerprintArguments,
    InspectCertificateExtensionsArguments,
    InspectCertificateFileArguments,
    InspectCertificateNamesArguments,
    InspectCertificatePublicKeyArguments,
)
from seedemu_tool_service.tools.pki.expiration.models import (
    CertificateExpirationResult,
    CheckCertificateExpirationArguments,
)
from seedemu_tool_service.tools.pki.remote_tls.models import (
    InspectRemoteTLSCertificateArguments,
    RemoteTLSCertificateInspectionResult,
)
from seedemu_tool_service.tools.pki.shared.models import CertificateFields, ToolArguments
from seedemu_tool_service.tools.pki.trust_verification.models import (
    CertificateChainVerificationResult,
    VerifyCertificateChainArguments,
)

__all__ = [
    "CertificateChainVerificationResult",
    "CertificateExpirationResult",
    "CertificateExtensions",
    "CertificateExtensionsResult",
    "CertificateFields",
    "CertificateFingerprintResult",
    "CertificateInspectionResult",
    "CertificateNames",
    "CertificateNamesResult",
    "CertificatePublicKey",
    "CertificatePublicKeyResult",
    "CheckCertificateExpirationArguments",
    "GetCertificateFingerprintArguments",
    "InspectCertificateExtensionsArguments",
    "InspectCertificateFileArguments",
    "InspectCertificateNamesArguments",
    "InspectCertificatePublicKeyArguments",
    "InspectRemoteTLSCertificateArguments",
    "RemoteTLSCertificateInspectionResult",
    "ToolArguments",
    "VerifyCertificateChainArguments",
]

