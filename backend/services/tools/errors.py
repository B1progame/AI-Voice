from __future__ import annotations


class ToolError(RuntimeError):
    """A user-facing tool error.

    We keep the message safe to show to end users.
    """

    def __init__(self, message: str, *, code: str = "tool_error"):
        super().__init__(message)
        self.code = code