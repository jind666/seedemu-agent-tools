"""Runtime backend contract."""

from collections.abc import Sequence
from typing import Any, Protocol

from seedemu_tool_service.models.runtime import RuntimeCommandResult, RuntimeStatus


class RuntimeBackend(Protocol):
    """Interface implemented by emulator runtime backends."""

    def status(self) -> RuntimeStatus:
        """Return backend connectivity and version information."""

        ...

    def execute(self, container: str, command: Sequence[str]) -> RuntimeCommandResult:
        """Execute an argument-vector command inside an emulated node."""

        ...

    def list_project_containers(self, project: str) -> list[dict[str, Any]]:
        """Return stable metadata for containers in one Compose project."""

        ...

    def list_projects(self) -> list[dict[str, Any]]:
        """Return Compose projects discovered from container labels."""

        ...

    def describe_project(self, project: str) -> dict[str, Any]:
        """Return a read-only service/network description for one Compose project."""

        ...

    def execute_service(
        self, project: str, service: str, command: Sequence[str]
    ) -> RuntimeCommandResult:
        """Execute a fixed argument vector after server-side project/service resolution."""

        ...

    def service_status(self, project: str, service: str) -> dict[str, Any]:
        """Return status for exactly one project-scoped Compose service."""

        ...

    def stop_service(self, project: str, service: str) -> dict[str, Any]:
        """Stop exactly one project-scoped Compose service."""

        ...

    def start_service(self, project: str, service: str) -> dict[str, Any]:
        """Start exactly one project-scoped Compose service."""

        ...
