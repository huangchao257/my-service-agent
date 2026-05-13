import os
from app.tools.base import tool_registry

ALLOWED_PATHS = {"/tmp", os.getcwd()}


def _is_safe_path(path: str) -> bool:
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(p) for p in ALLOWED_PATHS)


@tool_registry.register(
    name="read_file",
    description="Read contents of a file",
    parameters={"type": "object", "properties": {"path": {"type": "string", "description": "Absolute path to the file"}}, "required": ["path"]},
    risk="medium",
)
async def read_file(path: str) -> str:
    if not _is_safe_path(path):
        return f"Error: access denied for path '{path}'"
    try:
        with open(path) as f:
            content = f.read(4096)
            truncated = len(content) >= 4096
            return content[:4096] + ("\n...[truncated]" if truncated else "")
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error reading file: {e}"


@tool_registry.register(
    name="write_file",
    description="Write content to a file",
    parameters={"type": "object", "properties": {"path": {"type": "string", "description": "Absolute path"}, "content": {"type": "string", "description": "Content to write"}}, "required": ["path", "content"]},
    risk="high",
)
async def write_file(path: str, content: str) -> str:
    if not _is_safe_path(path):
        return f"Error: access denied for path '{path}'"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"File written: {path} ({len(content)} bytes)"
    except Exception as e:
        return f"Error writing file: {e}"