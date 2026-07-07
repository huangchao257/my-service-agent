"""结构化日志配置。

提供 setup_logging() 在应用启动时调用，统一日志格式：JSON 单行，便于聚合检索。
关键节点（对话开始/结束、工具调用、LLM 重试、异常）通过 get_logger(__name__) 获取 logger 记录。

设计：
- 默认 INFO 级别，可通过 LOG_LEVEL 环境变量调整
- JSON 格式包含 timestamp / level / logger / message / 额外字段
- 测试可通过 caplog 或替换 handler 验证
"""
import json
import logging
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """把 LogRecord 格式化为单行 JSON。extra 字段通过 record.__dict__ 透传。"""

    _RESERVED = {"name", "msg", "args", "levelname", "levelno", "pathname", "filename",
                 "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                 "created", "msecs", "relativeCreated", "thread", "threadName",
                 "processName", "process", "message", "taskName"}

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # 透传调用方通过 extra= 传入的字段
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str | None = None) -> None:
    """配置根 logger：输出到 stdout，JSON 格式。幂等，可重复调用。"""
    root = logging.getLogger()
    # 避免重复添加 handler
    if any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, _JsonFormatter) for h in root.handlers):
        # 仅更新级别
        root.setLevel(level or logging.getLogger().level or logging.INFO)
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level or "INFO")


def get_logger(name: str) -> logging.Logger:
    """获取命名 logger。调用方无需关心是否已 setup_logging。"""
    return logging.getLogger(name)
