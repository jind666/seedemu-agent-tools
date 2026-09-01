# PKI Tool Design

## Overview

The PKI tool domain provides certificate and TLS diagnostics for agents operating
SEED-Emulator environments through the Tool Service.

The current task catalog emphasizes service diagnosis, deployment, and security
response. PKI tools support those tasks when the network path and service port are
available, but HTTPS/TLS still fails because of certificate, trust-chain, or
expiration issues.

Example agent tasks that require PKI support include:

- determine why a client can reach `web1:443` but HTTPS requests fail;
- verify that a web service is presenting the expected certificate after deployment;
- detect whether DNS manipulation redirects a client to a service with an unexpected
  certificate;
- check whether an outage is caused by an expired certificate;
- verify whether a client trusts the CA that signed a service certificate.

## Design Goals

- Provide structured, agent-friendly PKI observations instead of unstructured shell
  output only.
- Keep the first implementation read-only so it is safe to use during diagnosis.
- Preserve raw command output for human debugging and parser improvements.
- Use explicit Pydantic argument and result models for every tool.
- Execute commands through the runtime backend using argument vectors, not shell
  strings.
- Separate diagnostic tools from state-changing repair and deployment tools.

## Current State

The current PKI domain exposes read-only diagnostics:

- `pki.inspect_certificate_file`
- `pki.inspect_certificate_names`
- `pki.inspect_certificate_extensions`
- `pki.inspect_certificate_public_key`
- `pki.get_certificate_fingerprint`
- `pki.inspect_remote_tls_certificate`
- `pki.verify_certificate_chain`
- `pki.check_certificate_expiration`

These tools use OpenSSL inside a selected emulated node container and return
structured results plus raw output.

The implementation is organized by PKI tool category:

```text
tools/pki/
|-- shared/                  # Shared PKI models and OpenSSL parsing helpers
|-- certificate_inspection/  # Local certificate-file inspection tools
|-- remote_tls/              # Remote TLS service inspection tools
|-- trust_verification/      # Certificate-chain and trust verification tools
|-- expiration/              # Certificate expiration checks
|-- models.py                # Compatibility exports for PKI models
|-- tools.py                 # Compatibility aggregate for PKI tool classes
`-- registration.py          # PKI registration entry point
```

## Tool Categories

### 1. Certificate Inspection

Certificate inspection tools examine certificate files that already exist inside an
emulated node.

These tools answer questions such as:

- Who was this certificate issued to?
- Who signed this certificate?
- When does the certificate become valid and expire?
- Which DNS names or IP addresses does the certificate cover?
- What public-key and signature algorithms does it use?
- What is the certificate fingerprint?

Current tools:

| Tool | Status | Purpose |
| --- | --- | --- |
| `pki.inspect_certificate_file` | Implemented | Inspect a certificate file and return common X.509 fields. |
| `pki.inspect_certificate_names` | Implemented | Return subject CN and SAN entries in a focused result. |
| `pki.inspect_certificate_extensions` | Implemented | Return key usage, extended key usage, basic constraints, and related extensions. |
| `pki.inspect_certificate_public_key` | Implemented | Return public-key algorithm and key size. |
| `pki.get_certificate_fingerprint` | Implemented | Return a certificate fingerprint for comparison tasks. |

### 2. Remote TLS Service Inspection

Remote TLS inspection tools connect from one emulated node to a TLS service and inspect
what the service actually presents to the client.

This is different from reading a local certificate file. A service may present a
different certificate because of SNI, reverse-proxy configuration, stale service state,
or DNS redirection.

These tools answer questions such as:

- What certificate does `web1:443` actually present?
- Does SNI change the presented certificate?
- Is the server sending a full certificate chain?
- Which TLS version and cipher were negotiated?
- Is the certificate seen by the client the same as the certificate file on the server?

Current tools:

| Tool | Status | Purpose |
| --- | --- | --- |
| `pki.inspect_remote_tls_certificate` | Implemented | Connect to a TLS service and inspect the presented certificate. |
| `pki.inspect_remote_tls_chain` | Proposed | Return every certificate presented by the remote service. |
| `pki.inspect_tls_handshake` | Proposed | Return negotiated TLS version, cipher, peer certificate summary, and verification status. |
| `pki.check_tls_hostname` | Proposed | Check whether the presented certificate matches an expected hostname. |
| `pki.check_tls_protocols` | Proposed | Check which TLS protocol versions are accepted by a service. |
| `pki.check_tls_cipher` | Proposed | Check whether a service accepts or negotiates expected ciphers. |

### 3. Certificate Chain And Trust Verification

Trust verification tools determine whether a certificate chains to trusted CA material
from the perspective of an emulated node.

These tools answer questions such as:

- Does this certificate chain to the expected CA?
- Is the failure caused by a missing intermediate certificate?
- Is the certificate self-signed or signed by an unknown authority?
- Does a client trust the CA used by a service?

Current tools:

| Tool | Status | Purpose |
| --- | --- | --- |
| `pki.verify_certificate_chain` | Implemented | Verify a certificate against CA files, CA directories, and optional intermediate chains. |
| `pki.verify_remote_tls_chain` | Proposed | Connect to a remote TLS service and verify the presented chain. |
| `pki.verify_certificate_against_ca` | Proposed | Focused wrapper for checking a certificate against one CA file. |
| `pki.verify_certificate_with_intermediates` | Proposed | Focused wrapper for checking a leaf certificate with supplied intermediate certificates. |
| `pki.explain_verification_failure` | Proposed | Normalize common OpenSSL verification errors into structured reasons. |

### 4. Expiration And Rotation Diagnosis

Expiration tools detect certificates that are already expired or close to expiry.

These tools answer questions such as:

- Is this certificate currently expired?
- Will it expire within a specified warning window?
- Is the remote service still presenting an old certificate after a file was replaced?
- Which certificates in a directory are near expiration?

Current tools:

| Tool | Status | Purpose |
| --- | --- | --- |
| `pki.check_certificate_expiration` | Implemented | Check whether a certificate file is expired or expires within a warning window. |
| `pki.check_remote_certificate_expiration` | Proposed | Check expiration for the certificate presented by a remote TLS service. |
| `pki.list_expiring_certificates` | Proposed | Scan a constrained directory for certificates expiring within a window. |
| `pki.compare_certificate_versions` | Proposed | Compare fingerprints and validity periods between certificate files or remote services. |

### 5. Private Key And CSR Tools

Private-key and CSR tools support controlled certificate creation workflows. These
tools write files and should be treated as state-changing tools.

These tools answer questions such as:

- Does a private key match a certificate?
- What subject and SANs are requested by a CSR?
- Can an agent generate a CSR for a new HTTPS service?

Current tools:

| Tool | Status | Purpose |
| --- | --- | --- |
| `pki.inspect_private_key` | Proposed | Return key type and size without exposing private-key material. |
| `pki.verify_private_key_matches_certificate` | Proposed | Check whether a private key corresponds to a certificate. |
| `pki.generate_private_key` | Proposed | Generate a private key in an allowed output path. |
| `pki.generate_csr` | Proposed | Generate a CSR from a private key and requested subject/SANs. |
| `pki.inspect_csr` | Proposed | Inspect subject, SANs, public key, and extensions requested by a CSR. |

### 6. Certificate Issuance Tools

Issuance tools create certificates from CSRs or create self-signed certificates for
controlled lab scenarios.

In real deployments, certificate issuance is usually handled by a CA, ACME client,
Kubernetes cert-manager, enterprise PKI system, or cloud certificate manager. In
SEED-Emulator environments, issuance should usually use a local lab CA rather than a
public CA.

Current tools:

| Tool | Status | Purpose |
| --- | --- | --- |
| `pki.create_local_ca` | Proposed | Create a lab CA certificate and key in a controlled path. |
| `pki.create_self_signed_certificate` | Proposed | Create a self-signed service certificate for isolated experiments. |
| `pki.sign_certificate_with_ca` | Proposed | Sign a CSR using a local lab CA. |
| `pki.issue_server_certificate` | Proposed | Higher-level helper for issuing a serverAuth certificate. |
| `pki.issue_client_certificate` | Proposed | Higher-level helper for issuing a clientAuth certificate. |

### 7. Certificate Installation And Deployment

Installation tools place certificate material where services can use it. These tools
are state-changing and may affect service availability.

These tools answer questions such as:

- Can the agent deploy a new certificate without overwriting unrelated files?
- Can the agent roll back certificate material after a failed repair?
- Did the service reload and begin presenting the new certificate?

Current tools:

| Tool | Status | Purpose |
| --- | --- | --- |
| `pki.backup_certificate_material` | Proposed | Back up certificate/key/chain files before replacement. |
| `pki.install_certificate` | Proposed | Install a certificate file to an approved destination. |
| `pki.install_private_key` | Proposed | Install a private key with restrictive permissions. |
| `pki.install_certificate_chain` | Proposed | Install a certificate chain bundle. |
| `pki.restore_certificate_material` | Proposed | Restore backed-up certificate material. |

These tools should usually be paired with service tools:

```text
service.reload_service
service.restart_service
service.http_request
pki.inspect_remote_tls_certificate
```

### 8. Trust Store And CA Management

Trust-store tools inspect or modify which CAs a client trusts. These tools are included
in the PKI domain because they directly affect certificate validation behavior.

These tools answer questions such as:

- Does a client trust the lab CA?
- Was an attacker CA installed in a client trust store?
- Does adding a CA make HTTPS verification succeed?

Current tools:

| Tool | Status | Purpose |
| --- | --- | --- |
| `pki.inspect_trust_store` | Proposed | List trusted CA material in a constrained trust-store location. |
| `pki.check_ca_installed` | Proposed | Check whether a specific CA certificate is trusted. |
| `pki.install_ca_certificate` | Proposed | Install a CA certificate into an approved trust store. |
| `pki.remove_ca_certificate` | Proposed | Remove a CA certificate from an approved trust store. |
| `pki.update_trust_store` | Proposed | Run the platform-specific trust-store update command. |

## Tool Response Envelope

The Tool Service can use a common response envelope across tool domains while allowing
each tool to define its own structured `data` payload. The envelope keeps agent-facing
responses predictable without forcing DNS, BGP, network, and PKI tools to return the
same domain-specific fields.

Example successful read-only response:

```json
{
  "tool": "pki.inspect_remote_tls_certificate",
  "source": "client1",
  "successful": true,
  "data": {
    "target": "web1",
    "port": 443,
    "server_name": "bank32.com",
    "certificate": {
      "subject": "CN=bank32.com",
      "issuer": "CN=SEED Lab CA",
      "serial": "01",
      "not_before": "Aug 01 00:00:00 2026 GMT",
      "not_after": "Aug 01 00:00:00 2027 GMT",
      "subject_alt_names": ["DNS:bank32.com"],
      "fingerprint_sha256": "AA:BB:CC"
    }
  },
  "raw_output": "openssl output, if useful for debugging",
  "error": null,
  "policy": {
    "task_id": "tls-diagnosis-001",
    "decision": "allowed",
    "matched_rule": "read-only-pki-diagnostics"
  }
}
```

Example denied response:

```json
{
  "tool": "pki.install_ca_certificate",
  "source": "client1",
  "successful": false,
  "data": null,
  "raw_output": null,
  "error": {
    "category": "policy_denied",
    "message": "This task does not allow trust-store modification."
  },
  "policy": {
    "task_id": "tls-diagnosis-001",
    "decision": "denied",
    "matched_rule": "diagnosis-tools-only"
  }
}
```

For state-changing tools, the domain-specific `data` payload can include side-effect
fields only when they are relevant:

```json
{
  "tool": "pki.generate_private_key",
  "source": "web1",
  "successful": true,
  "data": {
    "algorithm": "rsa",
    "bits": 2048,
    "created_paths": ["/tmp/seed-agent-pki/web1.key"],
    "overwritten_paths": []
  },
  "raw_output": null,
  "error": null,
  "policy": {
    "task_id": "tls-repair-001",
    "decision": "allowed",
    "matched_rule": "pki-artifact-generation"
  }
}
```

Initial task-level policy support can be expressed through the envelope and enforced
before a tool handler runs:

- `tool`: the fully qualified tool name used for allow/deny checks;
- `source`: the emulated node or container used for source restrictions;
- `policy.task_id`: the task whose policy was applied;
- `policy.decision`: whether the call was allowed or denied;
- `policy.matched_rule`: the policy rule that explained the decision;
- `error.category`: a stable error category such as `policy_denied`,
  `file_not_found`, `certificate_expired`, or `unknown_error`;
- `data.created_paths`, `data.modified_paths`, `data.backup_paths`: optional fields
  returned only by tools that create or modify artifacts.

The benchmark or Tool Service can keep a more complete audit log internally. The
agent-facing response should stay compact and include only the policy and side-effect
fields that are useful for the current call.
