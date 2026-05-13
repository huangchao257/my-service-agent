import pytest
from app.tools import tool_registry
from app.tools.system_tools import calculator, get_current_time


@pytest.mark.asyncio
async def test_calculator_basic():
    result = await calculator("2 + 3")
    assert result == "5"


@pytest.mark.asyncio
async def test_calculator_complex():
    result = await calculator("(10 * 5) / 2")
    assert "25" in result


@pytest.mark.asyncio
async def test_calculator_invalid_chars():
    result = await calculator("__import__('os')")
    assert "Error" in result


@pytest.mark.asyncio
async def test_get_current_time():
    result = await get_current_time()
    assert "Current time:" in result
    assert "UTC" in result


def test_tool_registry_has_all_builtins():
    names = [t.name for t in tool_registry.list_all()]
    assert "calculator" in names
    assert "get_current_time" in names
    assert "web_search" in names
    assert "read_file" in names
    assert "write_file" in names
    assert "execute_code" in names


def test_tool_risk_levels():
    assert tool_registry.requires_confirmation("calculator") is False
    assert tool_registry.requires_confirmation("web_search") is False
    assert tool_registry.requires_confirmation("write_file") is True
    assert tool_registry.requires_confirmation("execute_code") is True


def test_get_schemas():
    schemas = tool_registry.get_schemas(["calculator"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "calculator"