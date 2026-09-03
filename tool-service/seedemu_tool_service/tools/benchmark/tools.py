"""Stateless topology facts and generic project-scoped operations."""

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from seedemu_tool_service.backends import RuntimeBackend
from seedemu_tool_service.tools.benchmark.config import get_benchmark_settings
from seedemu_tool_service.tools.benchmark.errors import ToolRejectedError


def _fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class BenchmarkTools:
    """No policy state: facts and one bounded operation per call."""

    def __init__(self, backend: RuntimeBackend) -> None:
        self._backend = backend

    def runtime_projects(self) -> dict[str, Any]:
        return {"projects": self._backend.list_projects()}  # type: ignore[attr-defined]

    def runtime_describe(self, project: str) -> dict[str, Any]:
        return self._backend.describe_project(project)  # type: ignore[attr-defined]

    def runtime_service_capabilities(self, project: str, service: str) -> dict[str, Any]:
        checks = {
            "resolver": ["cat", "/etc/resolv.conf"],
            "iptables": ["iptables", "--version"],
            "tc": ["tc", "-V"],
            "interfaces": ["ip", "-o", "link", "show"],
        }
        evidence = {}
        for name, command in checks.items():
            result = self._execute(project, service, command)
            evidence[name] = {
                "available": result.exit_code == 0,
                "exit_code": result.exit_code,
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-1000:],
            }
        return {
            "project": project,
            "service": service,
            "operations": {
                "container.status": True,
                "container.stop_start": True,
                "dns.resolver": evidence["resolver"]["available"],
                "firewall.iptables": evidence["iptables"]["available"],
                "netem.tc": evidence["tc"]["available"],
                "network.interfaces": evidence["interfaces"]["available"],
            },
            "evidence": evidence,
            "read_only": True,
        }

    def discover_python_topology(
        self,
        seed_root: str,
        script_path: str,
        artifact_id: str,
        compile_timeout: int,
    ) -> dict[str, Any]:
        workspace = Path(seed_root).expanduser().resolve()
        if not (workspace / "seedemu" / "core").is_dir():
            raise ToolRejectedError("declared seed workspace is not a SEED Emulator checkout")
        try:
            script = Path(script_path).expanduser().resolve(strict=True)
        except OSError as error:
            raise ToolRejectedError(f"topology script not found: {script_path}") from error
        if script.suffix != ".py":
            raise ToolRejectedError("topology script must be a Python file")

        settings = get_benchmark_settings()
        artifact_dir = (settings.artifact_root / artifact_id).resolve()
        if settings.artifact_root not in artifact_dir.parents:
            raise ToolRejectedError("artifact directory escaped its allowed root")
        output = artifact_dir / "compiled"
        output.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(
            [
                settings.testrunner_python or sys.executable,
                str(script),
                "--platform",
                "amd",
                "--output",
                str(output),
            ],
            cwd=script.parent,
            env={
                **os.environ,
                "DOCKER_HOST": "unix:///nonexistent/seedemu-discovery.sock",
            },
            capture_output=True,
            text=True,
            timeout=compile_timeout,
            check=False,
        )
        candidates = sorted(output.rglob("docker-compose.y*ml"))
        if completed.returncode != 0 or len(candidates) != 1:
            return {
                "successful": False,
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-8000:],
                "stderr": completed.stderr[-8000:],
                "reason": "trial compile failed or did not produce exactly one Compose file",
            }

        compose = candidates[0]
        raw = yaml.safe_load(compose.read_text(encoding="utf-8")) or {}
        services_raw = raw.get("services") or {}
        networks_raw = raw.get("networks") or {}
        if (
            not isinstance(services_raw, dict)
            or not isinstance(networks_raw, dict)
            or not services_raw
            or len(services_raw) > 500
        ):
            raise ToolRejectedError(
                "compiled Compose must contain 1..500 service mappings and network mappings"
            )

        services = []
        for name, spec in sorted(services_raw.items()):
            spec = spec if isinstance(spec, dict) else {}
            bindings = spec.get("networks") or []
            network_values = (
                bindings
                if isinstance(bindings, (list, dict))
                else []
            )
            networks = sorted(str(item) for item in network_values)
            services.append(
                {
                    "service": str(name),
                    "image": str(spec.get("image") or ""),
                    "networks": networks,
                }
            )
        try:
            recorded_script_path = str(script.relative_to(workspace))
        except ValueError:
            recorded_script_path = str(script)
        descriptor = {
            "schema_version": 1,
            "mode": "python_discovered",
            "topology_id": script.parent.name,
            "name": script.stem,
            "source": {
                "seed_root": str(workspace),
                "script_path": recorded_script_path,
                "compose_path": str(compose),
                "artifact_id": artifact_id,
            },
            "project": artifact_id,
            "services": services,
            "networks": [{"name": str(name)} for name in sorted(networks_raw)],
            "default_probes": [
                {"type": "service_running", "service": item["service"]}
                for item in services
            ],
            "limits": {"service_count": len(services), "max_services": 500},
        }
        descriptor["fingerprint"] = _fingerprint(descriptor)
        return {
            "successful": True,
            "exit_code": 0,
            "descriptor": descriptor,
            "stdout": completed.stdout[-8000:],
            "stderr": completed.stderr[-8000:],
            "docker_invoked": False,
        }

    def topology_lifecycle(
        self,
        action: str,
        artifact_id: str,
        compose_path: str,
        project: str,
    ) -> dict[str, Any]:
        settings = get_benchmark_settings()
        artifact_dir = (settings.artifact_root / artifact_id).resolve()
        try:
            compose = Path(compose_path).expanduser().resolve(strict=True)
        except OSError as error:
            raise ToolRejectedError(
                f"discovered Compose artifact not found: {compose_path}"
            ) from error
        if artifact_dir not in compose.parents or compose.name not in {
            "docker-compose.yml",
            "docker-compose.yaml",
        }:
            raise ToolRejectedError("Compose artifact is outside the bound discovery artifact")

        if action == "readiness":
            containers = self._backend.list_project_containers(
                project
            )  # type: ignore[attr-defined]

            def is_dummy(container: dict[str, Any]) -> bool:
                service = str(container.get("service") or "")
                return len(service) == 32 and all(
                    character in "0123456789abcdef" for character in service
                )

            failed = [
                item
                for item in containers
                if item.get("status") != "running" and not is_dummy(item)
            ]
            successful = bool(containers) and not failed
            return {
                "action": action,
                "artifact_id": artifact_id,
                "compose_path": str(compose),
                "project": project,
                "successful": successful,
                "exit_code": 0 if successful else 1,
                "containers": containers,
                "stdout": "",
                "stderr": "" if successful else "not all discovered services are running",
            }

        operation = {
            "build": ["build"],
            "up": ["up", "-d"],
            "down": ["down", "--remove-orphans"],
        }[action]
        completed = subprocess.run(
            ["docker", "compose", "-p", project, "-f", str(compose), *operation],
            cwd=compose.parent,
            env={**os.environ, **settings.build_env},
            capture_output=True,
            text=True,
            timeout=2100 if action == "build" else 900,
            check=False,
        )
        return {
            "action": action,
            "artifact_id": artifact_id,
            "compose_path": str(compose),
            "project": project,
            "successful": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def container_inspect(self, project: str, service: str) -> dict[str, Any]:
        return self._backend.service_status(project, service)  # type: ignore[attr-defined]

    def container_stop(self, project: str, service: str) -> dict[str, Any]:
        return self._backend.stop_service(project, service)  # type: ignore[attr-defined]

    def container_start(self, project: str, service: str) -> dict[str, Any]:
        return self._backend.start_service(project, service)  # type: ignore[attr-defined]

    def dns_inspect(self, project: str, service: str) -> dict[str, Any]:
        result = self._execute(project, service, ["cat", "/etc/resolv.conf"])
        return self._result(project, service, result, content=result.stdout)

    def dns_probe(self, project: str, service: str, name: str) -> dict[str, Any]:
        result = self._execute(project, service, ["getent", "hosts", name])
        return self._result(
            project,
            service,
            result,
            name=name,
            healthy=result.exit_code == 0 and bool(result.stdout.strip()),
        )

    def dns_set_nameserver(
        self,
        project: str,
        service: str,
        nameserver: str,
    ) -> dict[str, Any]:
        content = f"nameserver {nameserver}\noptions ndots:0\n"
        encoded = base64.b64encode(content.encode()).decode()
        result = self._execute(
            project,
            service,
            [
                "sh",
                "-c",
                'printf "%s" "$1" | base64 -d > /etc/resolv.conf',
                "dns-config",
                encoded,
            ],
        )
        return self._result(
            project,
            service,
            result,
            nameserver=nameserver,
            changed=result.exit_code == 0,
        )

    def network_probe(
        self,
        project: str,
        service: str,
        destination: str,
        count: int,
        timeout_seconds: int,
        max_average_ms: float,
    ) -> dict[str, Any]:
        result = self._execute(
            project,
            service,
            ["ping", "-n", "-c", str(count), "-W", str(timeout_seconds), destination],
        )
        match = re.search(r"= [0-9.]+/([0-9.]+)/", result.stdout)
        average = float(match.group(1)) if match else None
        return self._result(
            project,
            service,
            result,
            destination=destination,
            average_ms=average,
            max_average_ms=max_average_ms,
            healthy=(
                result.exit_code == 0
                and average is not None
                and average <= max_average_ms
            ),
        )

    @staticmethod
    def _firewall_rule(destination: str, operation: str) -> list[str]:
        return ["iptables", operation, "OUTPUT", "-d", destination, "-j", "DROP"]

    def firewall_inspect(
        self,
        project: str,
        service: str,
        destination: str,
    ) -> dict[str, Any]:
        result = self._execute(
            project,
            service,
            self._firewall_rule(destination, "-C"),
        )
        return self._result(
            project,
            service,
            result,
            destination=destination,
            blocked=result.exit_code == 0,
        )

    def firewall_add_drop(
        self,
        project: str,
        service: str,
        destination: str,
    ) -> dict[str, Any]:
        if self.firewall_inspect(project, service, destination)["blocked"]:
            return {
                "project": project,
                "service": service,
                "destination": destination,
                "changed": False,
                "blocked": True,
            }
        result = self._execute(
            project,
            service,
            self._firewall_rule(destination, "-I"),
        )
        return self._result(
            project,
            service,
            result,
            destination=destination,
            changed=result.exit_code == 0,
            blocked=result.exit_code == 0,
        )

    def firewall_delete_drop(
        self,
        project: str,
        service: str,
        destination: str,
    ) -> dict[str, Any]:
        result = self._execute(
            project,
            service,
            self._firewall_rule(destination, "-D"),
        )
        return self._result(
            project,
            service,
            result,
            destination=destination,
            changed=result.exit_code == 0,
        )

    def netem_inspect(
        self,
        project: str,
        service: str,
        interface: str,
    ) -> dict[str, Any]:
        result = self._execute(
            project,
            service,
            ["tc", "qdisc", "show", "dev", interface],
        )
        return self._result(
            project,
            service,
            result,
            interface=interface,
            active=" netem " in f" {result.stdout} ",
        )

    def netem_apply(
        self,
        project: str,
        service: str,
        interface: str,
        delay_ms: int,
        jitter_ms: int,
        loss_percent: float,
    ) -> dict[str, Any]:
        result = self._execute(
            project,
            service,
            [
                "tc",
                "qdisc",
                "change",
                "dev",
                interface,
                "parent",
                "1:0",
                "handle",
                "10:",
                "netem",
                "delay",
                f"{delay_ms}ms",
                f"{jitter_ms}ms",
                "loss",
                f"{loss_percent}%",
            ],
        )
        return self._result(
            project,
            service,
            result,
            interface=interface,
            changed=result.exit_code == 0,
        )

    def _execute(self, project: str, service: str, command: list[str]) -> Any:
        return self._backend.execute_service(
            project,
            service,
            command,
        )  # type: ignore[attr-defined]

    @staticmethod
    def _result(
        project: str,
        service: str,
        result: Any,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "project": project,
            "service": service,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            **extra,
        }
