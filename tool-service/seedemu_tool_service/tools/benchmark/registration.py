"""Register topology facts and generic project-scoped operations."""

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.models.tool import ToolDefinition
from seedemu_tool_service.registry import ToolRegistry
from seedemu_tool_service.tools.benchmark.models import (
    DNSProbeArguments,
    DNSSetNameserverArguments,
    FirewallRuleArguments,
    NetemApplyArguments,
    NetemArguments,
    NetworkProbeArguments,
    ProjectArguments,
    RuntimeProjectsArguments,
    ServiceArguments,
    TopologyDiscoverArguments,
    TopologyLifecycleArguments,
)
from seedemu_tool_service.tools.benchmark.tools import BenchmarkTools


def register_benchmark_tools(registry: ToolRegistry, backend: RuntimeBackend) -> None:
    """Register the stateless Benchmark-facing tool surface."""

    tools = BenchmarkTools(backend)
    definitions = [
        (
            "benchmark.runtime.projects",
            "List Compose projects from labels.",
            tools.runtime_projects,
            RuntimeProjectsArguments,
        ),
        (
            "benchmark.runtime.describe",
            "Describe one running Compose project.",
            tools.runtime_describe,
            ProjectArguments,
        ),
        (
            "benchmark.runtime.service_capabilities",
            "Collect bounded read-only operation facts.",
            tools.runtime_service_capabilities,
            ServiceArguments,
        ),
        (
            "benchmark.topology.discover_python",
            "Trial-compile a SEED Python topology without Docker.",
            tools.discover_python_topology,
            TopologyDiscoverArguments,
        ),
        (
            "benchmark.topology.lifecycle",
            "Run the approved Compose lifecycle for one artifact.",
            tools.topology_lifecycle,
            TopologyLifecycleArguments,
        ),
        (
            "operation.container.inspect",
            "Inspect one project-scoped service.",
            tools.container_inspect,
            ServiceArguments,
        ),
        (
            "operation.container.stop",
            "Stop one project-scoped service.",
            tools.container_stop,
            ServiceArguments,
        ),
        (
            "operation.container.start",
            "Start one project-scoped service.",
            tools.container_start,
            ServiceArguments,
        ),
        (
            "operation.dns.inspect",
            "Read resolver state.",
            tools.dns_inspect,
            ServiceArguments,
        ),
        (
            "operation.dns.probe",
            "Run one bounded resolver query.",
            tools.dns_probe,
            DNSProbeArguments,
        ),
        (
            "operation.dns.set_nameserver",
            "Set one validated resolver address.",
            tools.dns_set_nameserver,
            DNSSetNameserverArguments,
        ),
        (
            "operation.firewall.inspect_drop",
            "Inspect one exact OUTPUT drop rule.",
            tools.firewall_inspect,
            FirewallRuleArguments,
        ),
        (
            "operation.firewall.add_drop",
            "Add one exact OUTPUT drop rule.",
            tools.firewall_add_drop,
            FirewallRuleArguments,
        ),
        (
            "operation.firewall.delete_drop",
            "Delete one exact OUTPUT drop rule.",
            tools.firewall_delete_drop,
            FirewallRuleArguments,
        ),
        (
            "operation.netem.inspect",
            "Inspect qdisc state on one interface.",
            tools.netem_inspect,
            NetemArguments,
        ),
        (
            "operation.netem.apply",
            "Apply bounded netem parameters.",
            tools.netem_apply,
            NetemApplyArguments,
        ),
        (
            "operation.network.probe",
            "Run a bounded reachability and latency probe.",
            tools.network_probe,
            NetworkProbeArguments,
        ),
    ]
    for name, description, handler, arguments in definitions:
        registry.register(
            definition=ToolDefinition(
                name=name,
                domain=name.split(".", 1)[0],
                description=description,
            ),
            handler=handler,
            arguments_model=arguments,
        )
