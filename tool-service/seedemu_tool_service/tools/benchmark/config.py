"""Deployment-local configuration for Benchmark topology tools."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_ARTIFACT_ROOT = Path("/tmp/seedemu-benchmark-artifacts")
_DEFAULT_TESTRUNNER_PYTHON = "/usr/bin/python3"
_DEFAULT_BUILD_ENV = {
    "DOCKER_BUILDKIT": "1",
    "COMPOSE_BAKE": "true",
    "COMPOSE_PARALLEL_LIMIT": "64",
}


@dataclass(frozen=True, slots=True)
class BenchmarkSettings:
    """Resources used only by Python discovery and topology lifecycle tools.

    The SEED workspace is intentionally not configured here. A trusted caller
    declares its checkout for each discovery request, where the tool validates it.
    """

    artifact_root: Path = _DEFAULT_ARTIFACT_ROOT
    testrunner_python: str = _DEFAULT_TESTRUNNER_PYTHON
    build_env: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_BUILD_ENV))


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser().resolve() if raw else default


def _build_env_from_env() -> dict[str, str]:
    raw = os.environ.get("SEEDEMU_BUILD_ENV")
    if not raw:
        return dict(_DEFAULT_BUILD_ENV)
    try:
        value = json.loads(raw)
    except ValueError as error:
        raise ValueError("SEEDEMU_BUILD_ENV must be a JSON object of string pairs") from error
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    ):
        raise ValueError("SEEDEMU_BUILD_ENV must be a JSON object of string pairs")
    return value


def get_benchmark_settings() -> BenchmarkSettings:
    """Read Benchmark-domain deployment settings without affecting other domains."""

    return BenchmarkSettings(
        artifact_root=_path_from_env("SEEDEMU_ARTIFACT_ROOT", _DEFAULT_ARTIFACT_ROOT),
        testrunner_python=os.environ.get(
            "SEEDEMU_TESTRUNNER_PYTHON", _DEFAULT_TESTRUNNER_PYTHON
        ),
        build_env=_build_env_from_env(),
    )
