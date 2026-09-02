"""Compatibility aggregate for PKI-domain tool implementations."""

from seedemu_tool_service.tools.pki.certificate_inspection.tools import (
    CertificateInspectionTools,
)
from seedemu_tool_service.tools.pki.expiration.tools import ExpirationTools
from seedemu_tool_service.tools.pki.remote_tls.tools import RemoteTLSTools
from seedemu_tool_service.tools.pki.trust_verification.tools import TrustVerificationTools


class PKITools(
    CertificateInspectionTools,
    RemoteTLSTools,
    TrustVerificationTools,
    ExpirationTools,
):
    """Backward-compatible aggregate of implemented PKI tool categories."""


__all__ = [
    "CertificateInspectionTools",
    "ExpirationTools",
    "PKITools",
    "RemoteTLSTools",
    "TrustVerificationTools",
]

