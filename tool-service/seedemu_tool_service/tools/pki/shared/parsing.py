"""OpenSSL output parsing helpers for PKI tools."""

from seedemu_tool_service.tools.pki.shared.models import CertificateFields


def parse_certificate_fields(output: str) -> CertificateFields:
    """Extract common fields from OpenSSL text output when present."""

    return CertificateFields(
        subject=parse_prefixed_value(output, "subject"),
        issuer=parse_prefixed_value(output, "issuer"),
        serial=parse_prefixed_value(output, "serial"),
        not_before=parse_prefixed_value(output, "notBefore"),
        not_after=parse_prefixed_value(output, "notAfter"),
        fingerprint_sha256=parse_prefixed_value(output, "sha256 Fingerprint"),
    )


def parse_prefixed_value(output: str, key: str) -> str | None:
    """Return the value from an OpenSSL key=value line."""

    prefix = f"{key}="
    prefix_lower = prefix.lower()
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix_lower):
            return stripped[len(prefix) :].strip()
    return None


def parse_subject_common_name(subject: str | None) -> str | None:
    """Extract a simple CN component from an OpenSSL subject string."""

    if subject is None:
        return None

    for separator in (",", "/"):
        for part in subject.split(separator):
            stripped = part.strip()
            if stripped.startswith("CN="):
                return stripped[3:].strip()
            if " = " in stripped:
                key, value = stripped.split(" = ", 1)
                if key.strip() == "CN":
                    return value.strip()
    return None


def parse_subject_alt_names(output: str) -> list[str]:
    """Extract SAN entries from OpenSSL extension output."""

    names: list[str] = []
    lines = output.splitlines()
    for index, line in enumerate(lines):
        if "Subject Alternative Name" not in line:
            continue

        for san_line in lines[index + 1 :]:
            stripped = san_line.strip()
            if not stripped:
                break
            if stripped.startswith("X509v3 ") or stripped.startswith("Signature Algorithm"):
                break
            names.extend(part.strip() for part in stripped.split(",") if part.strip())
        break
    return names


def parse_extension_value(output: str, extension_name: str) -> str | None:
    """Extract the value lines for a named X.509 extension."""

    lines = output.splitlines()
    for index, line in enumerate(lines):
        if extension_name not in line:
            continue

        values: list[str] = []
        for extension_line in lines[index + 1 :]:
            stripped = extension_line.strip()
            if not stripped:
                break
            if stripped.startswith("X509v3 ") or stripped.startswith("Signature Algorithm"):
                break
            values.append(stripped)
        return "; ".join(values) if values else None
    return None


def parse_public_key_algorithm(output: str) -> str | None:
    """Extract public-key algorithm from OpenSSL text output."""

    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Public Key Algorithm:"):
            return stripped.split(":", 1)[1].strip()
    return None


def parse_public_key_bits(output: str) -> int | None:
    """Extract public-key size from OpenSSL text output."""

    marker = "Public-Key: ("
    for line in output.splitlines():
        stripped = line.strip()
        if marker not in stripped:
            continue
        after_marker = stripped.split(marker, 1)[1]
        bits_text = after_marker.split(" bit", 1)[0]
        try:
            return int(bits_text)
        except ValueError:
            return None
    return None

