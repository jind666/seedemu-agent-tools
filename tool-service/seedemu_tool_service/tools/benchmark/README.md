# Topology and operation tools

<!-- README_SYNC_REQUIRED: Update this file, drivers/README.md, and tool-service/README.md with every interface change. -->

This package is a thin deterministic adapter. `runtime.describe` and `topology.discover_python` return pure topology facts; neither returns `available_faults` or makes benchmark decisions. `runtime.service_capabilities` runs a fixed read-only probe set and returns operation facts.

All callers use `operation.container.*`, `operation.dns.*`, `operation.firewall.*`, `operation.netem.*`, and `operation.network.probe`. Inputs remain project/service scoped, typed, bounded, and executed without caller-provided shell strings. This package contains no session, grant, recovery-token, candidate-policy, or fault-semantic state; Benchmark Agent and its Adapter own those concerns.

`config.py` owns only this domain's local artifact root, TestRunner interpreter, and Compose build environment. `registration.py` owns schemas and names, `models.py` owns argument validation, and `tools.py` owns the stateless topology/runtime adapter. LLM calls, fault value, Scenario selection, qualification, authorization policy, and scoring belong to Benchmark Agent, not Tool Service.

| Environment variable | Default | Benchmark-only purpose |
| --- | --- | --- |
| `SEEDEMU_ARTIFACT_ROOT` | `/tmp/seedemu-benchmark-artifacts` | Trial-compile artifacts and compatibility state. |
| `SEEDEMU_TESTRUNNER_PYTHON` | `/usr/bin/python3` | Python interpreter used to trial-compile a SEED topology. |
| `SEEDEMU_BUILD_ENV` | BuildKit/Bake/64-way parallelism | JSON object of string environment pairs passed to the approved Compose lifecycle. |
