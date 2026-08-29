"""Models used for tool discovery."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolDefinition(BaseModel):
    """Agent-visible metadata for a registered tool."""

    model_config = ConfigDict(frozen=True)

    name: str
    domain: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)


class ToolListResponse(BaseModel):
    """Response returned by the tool-discovery endpoint."""

    tools: list[ToolDefinition]
    count: int


class ToolInvocationRequest(BaseModel):
    """Arguments supplied when invoking a registered tool."""

    model_config = ConfigDict(extra="forbid")

    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolInvocationResponse(BaseModel):
    """Result returned by a successful tool invocation."""

    tool: str
    result: Any
