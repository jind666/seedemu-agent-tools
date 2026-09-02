"""Strict arguments for topology facts and generic operations."""

from ipaddress import ip_address, ip_network
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SAFE_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$"


class _Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectArguments(_Arguments):
    project: str = Field(pattern=_SAFE_ID)


class RuntimeProjectsArguments(_Arguments):
    pass


class ServiceArguments(ProjectArguments):
    service: str = Field(pattern=_SAFE_ID)


class TopologyDiscoverArguments(_Arguments):
    seed_root: str = Field(min_length=1)
    script_path: str = Field(min_length=1)
    artifact_id: str = Field(pattern=_SAFE_ID)
    compile_timeout: int = Field(default=300, ge=10, le=600)

    @field_validator("seed_root", "script_path")
    @classmethod
    def validate_paths(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("paths must not contain NUL")
        return value


class DNSProbeArguments(ServiceArguments):
    name: str = Field(min_length=1, max_length=253)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if any(character.isspace() for character in value):
            raise ValueError("name must not contain whitespace")
        return value


class DNSSetNameserverArguments(ServiceArguments):
    nameserver: str

    @field_validator("nameserver")
    @classmethod
    def validate_nameserver(cls, value: str) -> str:
        return str(ip_address(value))


class NetworkProbeArguments(ServiceArguments):
    destination: str
    count: int = Field(default=2, ge=1, le=5)
    timeout_seconds: int = Field(default=3, ge=1, le=10)
    max_average_ms: float = Field(default=250.0, ge=0.1, le=60000)

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        return str(ip_address(value))


class FirewallRuleArguments(ServiceArguments):
    destination: str

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: str) -> str:
        return str(ip_network(value, strict=False))


class NetemArguments(ServiceArguments):
    interface: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,32}$")


class NetemApplyArguments(NetemArguments):
    delay_ms: int = Field(default=0, ge=0, le=60000)
    jitter_ms: int = Field(default=0, ge=0, le=10000)
    loss_percent: float = Field(default=0, ge=0, le=100)


class TopologyLifecycleArguments(_Arguments):
    action: Literal["build", "up", "readiness", "down"]
    artifact_id: str = Field(pattern=_SAFE_ID)
    compose_path: str = Field(min_length=1)
    project: str = Field(pattern=_SAFE_ID)

    @field_validator("compose_path")
    @classmethod
    def validate_compose_path(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("compose_path must not contain NUL")
        return value
