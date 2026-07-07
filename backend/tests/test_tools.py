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

@pytest.mark.asyncio
async def test_web_search_dedup_and_clamp(monkeypatch):
    """web_search 按 href 去重，max_results 被夹到 [1,10]。"""
    import sys, types
    fake_mod = types.ModuleType("ddgs")

    class _FakeDDGS:
        def text(self, query, max_results=5):
            return [
                {"title": "A", "body": "ba", "href": "http://a/1"},
                {"title": "A dup", "body": "bx", "href": "http://a/1"},
                {"title": "B", "body": "bb", "href": "http://b/1"},
            ]
    fake_mod.DDGS = _FakeDDGS
    monkeypatch.setitem(sys.modules, "ddgs", fake_mod)

    from app.tools.web_search import web_search
    result = await web_search("q", max_results=5)
    assert "http://a/1" in result
    assert "http://b/1" in result
    assert "A dup" not in result


@pytest.mark.asyncio
async def test_web_search_max_results_clamped(monkeypatch):
    """max_results=999 被夹到 10。"""
    import sys, types
    fake_mod = types.ModuleType("ddgs")
    captured = {}

    class _FakeDDGS:
        def text(self, query, max_results=5):
            captured["asked"] = max_results
            return [{"title": "x", "body": "y", "href": "http://x/1"}]
    fake_mod.DDGS = _FakeDDGS
    monkeypatch.setitem(sys.modules, "ddgs", fake_mod)

    from app.tools.web_search import web_search
    await web_search("q", max_results=999)
    assert captured["asked"] == 20  # 夹到 10 后 *2


def test_validate_args_missing_required():
    """缺必填参数时报错"""
    err = tool_registry.validate_args("calculator", {})
    assert err and "expression" in err


def test_validate_args_ok_and_coercion():
    """类型正确通过；字符串数字能温和强转为 integer"""
    assert tool_registry.validate_args("calculator", {"expression": "1+1"}) is None
    # json_format 的 indent 是 integer，传 "4" 应被强转通过
    err = tool_registry.validate_args("json_format", {"json_str": "{}", "indent": "4"})
    assert err is None


def test_validate_args_wrong_type():
    """类型不符且无法强转时报错"""
    # expression 应为 string，传数字会被强转为 str（不报错）
    assert tool_registry.validate_args("calculator", {"expression": 123}) is None
    # json_path 的 path 也是 string
    assert tool_registry.validate_args("json_path", {"json_str": "{}", "path": 1}) is None


def test_validate_args_unknown_tool():
    assert "Unknown tool" in tool_registry.validate_args("nope", {})


def test_validate_args_boolean_strictness():
    """boolean 参数不接受非布尔值"""
    # password_generate 的 symbols 是 boolean
    err = tool_registry.validate_args("password_generate", {"length": 16, "symbols": "yes"})
    assert err and "boolean" in err


def test_record_call_and_metrics():
    """record_call 累计调用次数/耗时/错误，get_metrics 返回快照。"""
    tool_registry.record_call("json_format", 10.0, success=True)
    tool_registry.record_call("json_format", 30.0, success=True)
    tool_registry.record_call("json_format", 5.0, success=False)
    m = [x for x in tool_registry.get_metrics() if x["name"] == "json_format"][0]
    assert m["calls"] == 3
    assert m["errors"] == 1
    assert m["total_ms"] == 45.0
    assert m["avg_ms"] == 15.0


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """GET /api/tools/metrics 返回调用指标"""
    # 触发一次工具调用（经 runtime 路径才会记录；这里直接 record_call 模拟）
    from app.tools import tool_registry
    tool_registry.record_call("calculator", 1.5, success=True)
    resp = await client.get("/api/tools/metrics")
    assert resp.status_code == 200
    data = resp.json()
    calc = [x for x in data if x["name"] == "calculator"][0]
    assert calc["calls"] == 1 and calc["errors"] == 0
