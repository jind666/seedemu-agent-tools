"""Tool discovery and invocation endpoints."""

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError, BaseModel

from seedemu_tool_service.api.dependencies import get_tool_registry
from seedemu_tool_service.backends import RuntimeBackendError, RuntimeTargetNotFoundError
from seedemu_tool_service.models.tool import (
    ToolInvocationRequest,
    ToolInvocationResponse,
    ToolListResponse,
)
from seedemu_tool_service.registry import ToolNotFoundError, ToolRegistry

router = APIRouter(tags=["tools"])


@router.get("", response_model=ToolListResponse)
def list_tools(
    registry: Annotated[ToolRegistry, Depends(get_tool_registry)],
) -> ToolListResponse:
    """List tools currently registered with the service."""

    tools = registry.list_tools()
    return ToolListResponse(tools=tools, count=len(tools))


@router.post("/{tool_name}/invoke", response_model=ToolInvocationResponse)
async def invoke_tool(
    tool_name: str,
    request: ToolInvocationRequest,
    registry: Annotated[ToolRegistry, Depends(get_tool_registry)],
) -> ToolInvocationResponse:
    """Validate and invoke a registered tool by name."""

    try:
        started = time.perf_counter()
        result = await registry.invoke(tool_name, request.arguments)
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
    except ToolNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        ) from error
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Invalid tool arguments",
                "errors": error.errors(include_url=False),
            },
        ) from error
    except RuntimeTargetNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except RuntimeBackendError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    payload = result.model_dump() if isinstance(result, BaseModel) else result
    return ToolInvocationResponse(tool=tool_name, result=payload, duration_ms = duration_ms)
