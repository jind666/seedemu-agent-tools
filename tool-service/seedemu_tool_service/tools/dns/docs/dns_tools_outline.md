# DNS Tool Design Outline

## 1. Basic Tools

Basic tools perform individual, read-only DNS information queries. They do not modify zones or
determine whether an entire delegation is correct.

### `dns.lookup`

- Query A, AAAA, NS, MX, TXT, SOA, CNAME, and other record types.
- Use the `source` node's default resolver or query a specified DNS server.
- Distinguish command execution failure, DNS response status, and an empty answer.
- Provide the fundamental query capability used by other diagnostic tools.

### `dns.reverse_lookup`

- Perform a PTR reverse lookup for an IPv4 or IPv6 address.
- Generate the corresponding reverse DNS name automatically.
- Return PTR records and the DNS response status.

### `dns.batch_lookup`

- Query multiple names and record types in one invocation to reduce repeated Agent tool calls.
- Return an independent status for each query so that one failure does not discard other results.
- Collect information such as SOA, NS, A, and AAAA records for a zone in one operation.

## 2. Domain Registration and Update Tools

These tools change domain ownership, delegation, or zone content. They must authenticate and authorize
the current `source` and provide idempotency and status lookup for write operations.

#### `registrar_find`

- Locate a Registrar frontend that the `source` is allowed to use in the current emulated environment.
- Return only the registration service location, without listing callable interfaces or returning
  secrets.
- Let the Agent read the Registrar's public web pages and same-origin JavaScript to understand the
  registration workflow.

#### `registrar_request`

- Read Registrar frontend resources and send restricted same-origin requests.
- Support real-world business operations such as availability checks, registration quotes,
  registrations, operation queries, domain queries, and nameserver updates.
- Do not act as an arbitrary HTTP proxy; restrict the Registrar origin, redirects, and dangerous
  requests.
- Support both combined registration and delegation and nameserver updates after registration.

#### `dns_configure`

- Provide one interface for dynamic zone provisioning and record maintenance on self-hosted
  authoritative DNS servers.
- When a zone does not exist, verify the `source` authorization and provision the Primary and
  Secondary.
- After the zone is loaded, add, replace, or delete records through RFC 2136 with an update TSIG.
- Use a separate transfer TSIG for Primary-Secondary synchronization.
- Verify the SOA, NS, serial, authoritative responses, and Primary-Secondary convergence.

## 3. Diagnostic Tools

Diagnostic tools remain read-only. Rather than returning only one query result, they compare multiple
observation points, explain resolution paths, and locate configuration errors.

### `dns.compare`

- Query the same record on multiple DNS servers from one `source`.
- Compare response statuses, answers, TTLs, latency, and timeouts.
- Identify cache differences, Primary-Secondary inconsistencies, or differing results across resolvers.

### `dns.trace`

- Trace the complete DNS delegation chain starting at the root zone.
- Show the referral, authoritative servers, and final answer at each level.
- Identify the parent or child zone at which resolution fails.

### `dns.check_delegation`

- Compare the referral and glue returned by the parent zone with the NS records returned by the child
  authoritative servers.
- Check whether delegation targets, glue addresses, and child-zone authoritative configuration are
  consistent.
- Verify the delegation after the Registrar updates the parent zone.

### `dns.zone_transfer`

- Perform AXFR/IXFR with explicit authorization to inspect the complete zone actually served by an
  authoritative server.
- Diagnose missing Secondary data, serial inconsistencies, or transfer authorization errors.
- Reject unauthorized targets by default and limit returned data to prevent arbitrary zone
  enumeration.

### `dns.validate_dnssec`

- Validate the DNSSEC chain of trust formed by DS, DNSKEY, and RRSIG records.
- Distinguish DNSSEC not being enabled, expired signatures, DS mismatches, and validation failures.

### `dns.observe_cache`

- Repeat queries from the same `source` to observe TTL changes, cache hits, and refreshes after expiry.
- Diagnose cases where authoritative records have changed but a recursive resolver still returns stale
  data.
- Observe only; do not clear or modify the resolver cache.

### `dns.diagnose_resolver`

- Check the reachability, recursion capability, and basic response behavior of a specified recursive
  resolver.
- Distinguish authoritative DNS configuration errors from failures in the resolver used by `source`.
- Share underlying query capabilities with `dns.lookup` and `dns.compare`, while producing output
  focused on resolver health.
