"""HTTP API smoke tests."""

from fastapi.testclient import TestClient

from seedemu_tool_service.api.dependencies import get_runtime_backend, get_tool_registry
from seedemu_tool_service.backends import RuntimeBackendError, RuntimeTargetNotFoundError
from seedemu_tool_service.main import app
from seedemu_tool_service.models.runtime import RuntimeCommandResult, RuntimeStatus
from seedemu_tool_service.registry import ToolRegistry
from seedemu_tool_service.tools.network import register_network_tools

client = TestClient(app)


class FakeRuntimeBackend:
    def __init__(
        self,
        result: RuntimeCommandResult | None = None,
        error: RuntimeBackendError | None = None,
    ) -> None:
        self.result = result or RuntimeCommandResult(exit_code=0, stdout="ping output", stderr="")
        self.error = error
        self.container: str | None = None
        self.command: list[str] | None = None

    def status(self) -> RuntimeStatus:
        return RuntimeStatus(backend="fake", available=self.error is None)

    def execute(self, container: str, command: list[str]) -> RuntimeCommandResult:
        self.container = container
        self.command = command
        if self.error is not None:
            raise self.error
        return self.result


def registry_with_network_backend(backend: FakeRuntimeBackend) -> ToolRegistry:
    registry = ToolRegistry()
    register_network_tools(registry, backend)
    return registry


def test_service_info() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "SEEDemu Agent Tool Service",
        "version": "0.1.0",
        "docs_url": "/docs",
    }


def test_health() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tool_registry_lists_registered_tools() -> None:
    response = client.get("/api/v1/tools")

    assert response.status_code == 200
    body = response.json()

    tool_names = [tool["name"] for tool in body["tools"]]

    assert body["count"] == len(tool_names)
    assert tool_names == sorted(tool_names)

    expected_tools = {
        "bgp.summary",
        "dns.lookup",
        "network.inspect_ip_address",
        "network.ping",
        "pki.check_certificate_expiration",
        "pki.inspect_certificate_file",
        "pki.inspect_remote_tls_certificate",
        "pki.verify_certificate_chain",
    }
    assert expected_tools.issubset(tool_names)

    assert body["tools"][0]["domain"] == "bgp"


def test_invoke_tool_over_http() -> None:
    response = client.post(
        "/api/v1/tools/network.inspect_ip_address/invoke",
        json={"arguments": {"address": "2001:0db8::1"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "tool": "network.inspect_ip_address",
        "result": {
            "address": "2001:db8::1",
            "version": 6,
            "is_private": True,
            "is_loopback": False,
            "is_multicast": False,
            "is_global": False,
        },
    }


def test_invoke_unknown_tool_returns_not_found() -> None:
    response = client.post(
        "/api/v1/tools/network.missing/invoke",
        json={"arguments": {}},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Tool not found: network.missing"}


def test_invoke_tool_rejects_invalid_arguments() -> None:
    response = client.post(
        "/api/v1/tools/network.ping/invoke",
        json={
            "arguments": {
                "source": "source-node",
                "target": "192.0.2.1",
                "count": 0,
            }
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["detail"]["message"] == "Invalid tool arguments"
    assert body["detail"]["errors"][0]["loc"] == ["count"]


def test_invoke_docker_backed_tool_over_http() -> None:
    backend = FakeRuntimeBackend()
    app.dependency_overrides[get_tool_registry] = lambda: registry_with_network_backend(backend)
    try:
        response = client.post(
            "/api/v1/tools/network.ping/invoke",
            json={
                "arguments": {
                    "source": "as150-host-0",
                    "target": "10.151.0.2",
                    "count": 2,
                    "timeout_seconds": 4,
                }
            },
        )
    finally:
        app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 200
    assert backend.container == "as150-host-0"
    assert backend.command == ["ping", "-c", "2", "-W", "4", "10.151.0.2"]
    assert response.json()["result"]["reachable"] is True


def test_invoke_reports_unreachable_target_as_tool_result() -> None:
    backend = FakeRuntimeBackend(
        result=RuntimeCommandResult(exit_code=1, stdout="", stderr="destination unreachable")
    )
    app.dependency_overrides[get_tool_registry] = lambda: registry_with_network_backend(backend)
    try:
        response = client.post(
            "/api/v1/tools/network.ping/invoke",
            json={"arguments": {"source": "as150-host-0", "target": "192.0.2.1"}},
        )
    finally:
        app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 200
    assert response.json()["result"]["reachable"] is False
    assert response.json()["result"]["exit_code"] == 1


def test_invoke_returns_not_found_for_missing_runtime_target() -> None:
    backend = FakeRuntimeBackend(
        error=RuntimeTargetNotFoundError("Emulated node not found: missing-node")
    )
    app.dependency_overrides[get_tool_registry] = lambda: registry_with_network_backend(backend)
    try:
        response = client.post(
            "/api/v1/tools/network.ping/invoke",
            json={"arguments": {"source": "missing-node", "target": "192.0.2.1"}},
        )
    finally:
        app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 404
    assert response.json() == {"detail": "Emulated node not found: missing-node"}


def test_invoke_returns_service_unavailable_for_backend_failure() -> None:
    backend = FakeRuntimeBackend(error=RuntimeBackendError("Docker command execution failed"))
    app.dependency_overrides[get_tool_registry] = lambda: registry_with_network_backend(backend)
    try:
        response = client.post(
            "/api/v1/tools/network.ping/invoke",
            json={"arguments": {"source": "as150-host-0", "target": "192.0.2.1"}},
        )
    finally:
        app.dependency_overrides.pop(get_tool_registry, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "Docker command execution failed"}


def test_runtime_status() -> None:
    class AvailableBackend:
        def status(self) -> RuntimeStatus:
            return RuntimeStatus(
                backend="docker",
                available=True,
                daemon_version="test-version",
            )

    app.dependency_overrides[get_runtime_backend] = AvailableBackend
    try:
        response = client.get("/api/v1/runtime")
    finally:
        app.dependency_overrides.pop(get_runtime_backend, None)

    assert response.status_code == 200
    assert response.json() == {
        "backend": "docker",
        "available": True,
        "daemon_version": "test-version",
    }


def test_openapi_includes_public_routes() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
    assert "/api/v1/runtime" in response.json()["paths"]
    assert "/api/v1/tools" in response.json()["paths"]
    assert "/api/v1/tools/{tool_name}/invoke" in response.json()["paths"]
