import subprocess
import tempfile
import os
from app.tools.base import tool_registry


@tool_registry.register(
    name="execute_code",
    description="Execute Python code in a subprocess",
    parameters={"type": "object", "properties": {"code": {"type": "string", "description": "Python code to execute"}, "language": {"type": "string", "description": "Only 'python' is supported"}}, "required": ["code"]},
    risk="high",
)
async def execute_code(code: str, language: str = "python") -> str:
    if language != "python":
        return f"Error: language '{language}' is not supported"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(["python3", tmp_path], capture_output=True, text=True, timeout=30, cwd="/tmp")
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        return output[:4096] or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: code execution timed out (30s)"
    except Exception as e:
        return f"Error executing code: {e}"
    finally:
        os.unlink(tmp_path)