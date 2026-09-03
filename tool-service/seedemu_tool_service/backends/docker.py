"""Docker Engine runtime backend."""

from collections.abc import Sequence
from typing import Any

import docker
from docker.errors import DockerException, NotFound

from seedemu_tool_service.models.runtime import RuntimeCommandResult, RuntimeStatus


class RuntimeBackendError(RuntimeError):
    """Base error raised when a runtime-backend operation fails."""


class RuntimeTargetNotFoundError(RuntimeBackendError):
    """Raised when an emulated node cannot be found."""


class RuntimeTargetAmbiguousError(RuntimeBackendError):
    """Raised when project and service labels do not identify exactly one container."""


class DockerRuntimeBackend:
    """Access the Docker Engine configured through the process environment."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def status(self) -> RuntimeStatus:
        """Check access to the Docker daemon and report its version."""

        try:
            client = self._get_client()
            if not client.ping():
                return RuntimeStatus(backend="docker", available=False)
            daemon_version = client.version().get("Version")
        except DockerException:
            return RuntimeStatus(backend="docker", available=False)

        return RuntimeStatus(
            backend="docker",
            available=True,
            daemon_version=daemon_version,
        )

    def execute(self, container: str, command: Sequence[str]) -> RuntimeCommandResult:
        """Execute a command in a container through the Docker Engine API."""

        try:
            target = self._get_client().containers.get(container)
            exit_code, output = target.exec_run(list(command), demux=True)
        except NotFound as error:
            raise RuntimeTargetNotFoundError(f"Emulated node not found: {container}") from error
        except DockerException as error:
            raise RuntimeBackendError("Docker command execution failed") from error

        stdout_bytes, stderr_bytes = output
        return RuntimeCommandResult(
            exit_code=exit_code,
            stdout=self._decode_output(stdout_bytes),
            stderr=self._decode_output(stderr_bytes),
        )

    def list_project_containers(self, project: str) -> list[dict[str, Any]]:
        """List containers bound to one Compose project without exposing daemon access."""

        try:
            containers = self._get_client().containers.list(
                all=True,
                filters={"label": f"com.docker.compose.project={project}"},
            )
        except DockerException as error:
            raise RuntimeBackendError("Docker project inventory failed") from error
        return sorted(
            [
                {
                    "service": container.labels.get("com.docker.compose.service"),
                    "name": container.name,
                    "status": container.status,
                    "image": container.image.tags[0]
                    if container.image.tags
                    else container.image.id,
                }
                for container in containers
            ],
            key=lambda item: (item["service"] or "", item["name"]),
        )

    def list_projects(self) -> list[dict[str, Any]]:
        """Discover Compose projects from container labels (read-only)."""

        try:
            containers = self._get_client().containers.list(all=True)
        except DockerException as error:
            raise RuntimeBackendError("Docker project discovery failed") from error
        projects: dict[str, dict[str, int]] = {}
        for container in containers:
            project = container.labels.get("com.docker.compose.project")
            if not project:
                continue
            entry = projects.setdefault(project, {"total": 0, "running": 0})
            entry["total"] += 1
            if container.status == "running":
                entry["running"] += 1
        return sorted(
            [
                {
                    "project": name,
                    "total": counts["total"],
                    "running": counts["running"],
                }
                for name, counts in projects.items()
            ],
            key=lambda item: item["project"],
        )

    def describe_project(self, project: str) -> dict[str, Any]:
        """Describe service/network bindings through the Engine API without CLI use."""

        try:
            containers = self._get_client().containers.list(
                all=True,
                filters={"label": f"com.docker.compose.project={project}"},
            )
        except DockerException as error:
            raise RuntimeBackendError("Docker project description failed") from error
        services = []
        network_names: set[str] = set()
        for container in containers:
            container.reload()
            bindings = []
            for name, details in sorted(
                (container.attrs.get("NetworkSettings", {}).get("Networks") or {}).items()
            ):
                network_names.add(name)
                bindings.append({
                    "network": name,
                    "ipv4_address": details.get("IPAddress") or None,
                    "ipv6_address": details.get("GlobalIPv6Address") or None,
                })
            services.append({
                "service": container.labels.get("com.docker.compose.service"),
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else container.image.id,
                "networks": bindings,
            })
        return {
            "project": project,
            "services": sorted(services, key=lambda item: (item["service"] or "", item["name"])),
            "networks": [{"name": name} for name in sorted(network_names)],
        }

    def execute_service(
        self, project: str, service: str, command: Sequence[str]
    ) -> RuntimeCommandResult:
        """Resolve a target by immutable Compose labels before executing a command."""

        try:
            containers = self._get_client().containers.list(
                all=True,
                filters={
                    "label": [
                        f"com.docker.compose.project={project}",
                        f"com.docker.compose.service={service}",
                    ]
                },
            )
        except DockerException as error:
            raise RuntimeBackendError("Docker service resolution failed") from error
        if not containers:
            raise RuntimeTargetNotFoundError(
                f"No container for Compose project {project!r} service {service!r}"
            )
        if len(containers) != 1:
            raise RuntimeTargetAmbiguousError(
                f"Multiple containers for Compose project {project!r} service {service!r}"
            )
        target = containers[0]
        try:
            exit_code, output = target.exec_run(list(command), demux=True)
        except DockerException as error:
            raise RuntimeBackendError("Docker service command execution failed") from error
        stdout_bytes, stderr_bytes = output
        return RuntimeCommandResult(
            exit_code=exit_code,
            stdout=self._decode_output(stdout_bytes),
            stderr=self._decode_output(stderr_bytes),
        )

    def _resolve_service(self, project: str, service: str) -> Any:
        try:
            containers = self._get_client().containers.list(
                all=True,
                filters={
                    "label": [
                        f"com.docker.compose.project={project}",
                        f"com.docker.compose.service={service}",
                    ]
                },
            )
        except DockerException as error:
            raise RuntimeBackendError("Docker service resolution failed") from error
        if not containers:
            raise RuntimeTargetNotFoundError(
                f"No container for Compose project {project!r} service {service!r}"
            )
        if len(containers) != 1:
            raise RuntimeTargetAmbiguousError(
                f"Multiple containers for Compose project {project!r} service {service!r}"
            )
        return containers[0]

    def service_status(self, project: str, service: str) -> dict[str, Any]:
        target = self._resolve_service(project, service)
        target.reload()
        return {"project": project, "service": service, "status": target.status,
                "running": target.status == "running"}

    def stop_service(self, project: str, service: str) -> dict[str, Any]:
        target = self._resolve_service(project, service)
        try:
            target.stop(timeout=10)
            target.reload()
        except DockerException as error:
            raise RuntimeBackendError("Docker service stop failed") from error
        return {"project": project, "service": service, "status": target.status,
                "running": target.status == "running"}

    def start_service(self, project: str, service: str) -> dict[str, Any]:
        target = self._resolve_service(project, service)
        try:
            target.start()
            target.reload()
        except DockerException as error:
            raise RuntimeBackendError("Docker service start failed") from error
        return {"project": project, "service": service, "status": target.status,
                "running": target.status == "running"}

    @staticmethod
    def _decode_output(output: bytes | None) -> str:
        return output.decode("utf-8", errors="replace") if output else ""
