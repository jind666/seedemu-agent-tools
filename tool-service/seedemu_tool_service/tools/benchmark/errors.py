"""Domain-specific errors raised by benchmark tools."""


class ToolRejectedError(RuntimeError):
    """A typed Tool Service operation cannot be performed safely or correctly."""
