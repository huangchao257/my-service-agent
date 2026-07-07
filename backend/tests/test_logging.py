"""结构化日志单测 — 验证 JSON 格式化器输出与 extra 透传。"""
import json
import logging

from app.core.logging import _JsonFormatter, setup_logging, get_logger


def test_json_formatter_includes_fields():
    """formatter 输出单行 JSON，含 ts/level/logger/msg 与 extra 字段。"""
    fmt = _JsonFormatter()
    record = logging.LogRecord(
        name="test.logger", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    # 通过 extra 透传的字段
    record.conversation_id = "conv-123"
    record.rounds = 3

    line = fmt.format(record)
    payload = json.loads(line)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["msg"] == "hello world"
    assert payload["conversation_id"] == "conv-123"
    assert payload["rounds"] == 3
    assert "ts" in payload


def test_json_formatter_handles_exception():
    """异常信息被序列化进 exc 字段。"""
    fmt = _JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="x", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="failed", args=(), exc_info=sys.exc_info(),
        )
    payload = json.loads(fmt.format(record))
    assert "ValueError" in payload["exc"]
    assert "boom" in payload["exc"]


def test_setup_logging_idempotent():
    """重复调用 setup_logging 不会重复添加 handler。"""
    import sys
    before = len(logging.getLogger().handlers)
    setup_logging("DEBUG")
    after_first = len(logging.getLogger().handlers)
    setup_logging("INFO")
    after_second = len(logging.getLogger().handlers)
    assert after_first == after_second  # 第二次不新增 handler
    assert logging.getLogger().level == logging.INFO


def test_get_logger_returns_named_logger():
    assert get_logger("a.b").name == "a.b"
