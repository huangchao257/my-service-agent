"""常用开发工具集合 — 覆盖 JSON / 时间戳 / 编码 / 文本 / 数值等高频开发场景。

设计要点：
- 全部基于 Python 标准库，无外部依赖，纯计算，risk=low
- 通过 @tool_registry.register 注册，自动出现在 Agent 可选工具列表
- 失败一律返回带 "Error:" 前缀的字符串，不抛异常（与内置工具一致）
"""

import base64 as _base64
import hashlib
import json as _json
import re
import time
import urllib.parse
import uuid as _uuid
from datetime import datetime, timezone, timedelta
from app.tools.base import tool_registry


# ────────────────────────── JSON 工具 ──────────────────────────

@tool_registry.register(
    name="json_format",
    description="Pretty-print or minify a JSON string. Useful for inspecting compact JSON.",
    parameters={
        "type": "object",
        "properties": {
            "json_str": {"type": "string", "description": "A JSON string to format"},
            "indent": {"type": "integer", "description": "Indentation spaces; 0 or omit to minify (default 2)"},
        },
        "required": ["json_str"],
    },
    risk="low",
    category="dev",
)
async def json_format(json_str: str, indent: int = 2) -> str:
    """格式化 JSON 字符串。indent<=0 时压缩为单行。"""
    try:
        data = _json.loads(json_str)
    except Exception as e:
        return f"Error: invalid JSON — {e}"
    if indent and indent > 0:
        return _json.dumps(data, indent=indent, ensure_ascii=False)
    return _json.dumps(data, ensure_ascii=False, separators=(",", ":"))


@tool_registry.register(
    name="json_validate",
    description="Validate a JSON string and report whether it parses, with error detail if not.",
    parameters={
        "type": "object",
        "properties": {"json_str": {"type": "string", "description": "JSON string to validate"}},
        "required": ["json_str"],
    },
    risk="low",
    category="dev",
)
async def json_validate(json_str: str) -> str:
    """校验 JSON 合法性，返回 ok 或错误位置信息。"""
    try:
        _json.loads(json_str)
        return "valid JSON"
    except _json.JSONDecodeError as e:
        return f"Error: invalid JSON at line {e.lineno} col {e.colno}: {e.msg}"
    except Exception as e:
        return f"Error: {e}"


@tool_registry.register(
    name="json_path",
    description="Extract a value from a JSON string by dotted path, e.g. 'a.b[0].c'. Returns the matched value as a string.",
    parameters={
        "type": "object",
        "properties": {
            "json_str": {"type": "string", "description": "JSON string"},
            "path": {"type": "string", "description": "Dotted path with [index] for arrays, e.g. 'users[0].name'"},
        },
        "required": ["json_str", "path"],
    },
    risk="low",
    category="dev",
)
async def json_path(json_str: str, path: str) -> str:
    """按点路径从 JSON 中取值。支持 a.b[0].c 形式。"""
    try:
        data = _json.loads(json_str)
    except Exception as e:
        return f"Error: invalid JSON — {e}"
    cur = data
    # 把 'a.b[0].c' 拆成 ['a','b','[0]','c'] 再处理 [i]
    tokens = re.findall(r"[^.\[\]]+|\[\d+\]", path)
    for tok in tokens:
        if tok.startswith("["):
            idx = int(tok[1:-1])
            if not isinstance(cur, list) or idx >= len(cur):
                return "Error: index out of range or not a list"
            cur = cur[idx]
        else:
            if not isinstance(cur, dict) or tok not in cur:
                return f"Error: key '{tok}' not found"
            cur = cur[tok]
    if isinstance(cur, (dict, list)):
        return _json.dumps(cur, ensure_ascii=False)
    return str(cur)


# ────────────────────────── 时间戳工具 ──────────────────────────

def _ts_to_datetime(ts: float) -> datetime:
    """把秒或毫秒时间戳转 datetime（自动识别量级）。"""
    # 毫秒时间戳通常 > 1e12，秒时间戳 < 1e11
    if abs(ts) > 1e12:
        ts = ts / 1000.0
    return datetime.fromtimestamp(ts, tz=timezone.utc)


@tool_registry.register(
    name="timestamp_to_date",
    description="Convert a Unix timestamp (seconds or milliseconds) to a human-readable ISO date string.",
    parameters={
        "type": "object",
        "properties": {
            "timestamp": {"type": "number", "description": "Unix timestamp in seconds or milliseconds"},
            "timezone_offset": {"type": "integer", "description": "Optional timezone offset in hours, e.g. 8 for UTC+8. Default 0 (UTC)."},
        },
        "required": ["timestamp"],
    },
    risk="low",
    category="dev",
)
async def timestamp_to_date(timestamp: float, timezone_offset: int = 0) -> str:
    """时间戳 → ISO 字符串，自动识别秒/毫秒，支持时区偏移。"""
    try:
        dt = _ts_to_datetime(float(timestamp))
        if timezone_offset:
            dt = dt + timedelta(hours=timezone_offset)
        return dt.strftime("%Y-%m-%d %H:%M:%S") + (f" (UTC{timezone_offset:+d})" if timezone_offset else " (UTC)")
    except Exception as e:
        return f"Error: {e}"


@tool_registry.register(
    name="date_to_timestamp",
    description="Convert a date string to a Unix timestamp (seconds). Accepts ISO 8601 or 'YYYY-MM-DD HH:MM:SS'.",
    parameters={
        "type": "object",
        "properties": {"date_str": {"type": "string", "description": "Date string, e.g. '2024-01-15' or '2024-01-15 12:30:00'"}},
        "required": ["date_str"],
    },
    risk="low",
    category="dev",
)
async def date_to_timestamp(date_str: str) -> str:
    """日期字符串 → Unix 秒时间戳。支持 ISO 与常见格式。"""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
            return str(int(dt.timestamp()))
        except ValueError:
            continue
    return f"Error: unparseable date '{date_str}' (try 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS')"


@tool_registry.register(
    name="timestamp_now",
    description="Get the current Unix timestamp in both seconds and milliseconds.",
    parameters={"type": "object", "properties": {}},
    risk="low",
    category="dev",
)
async def timestamp_now() -> str:
    """返回当前 Unix 时间戳（秒 + 毫秒）。"""
    now = time.time()
    return f"seconds: {int(now)}\nmilliseconds: {int(now * 1000)}\niso_utc: {datetime.now(timezone.utc).isoformat()}"


# ────────────────────────── 标识与编码工具 ──────────────────────────

@tool_registry.register(
    name="uuid_generate",
    description="Generate one or more random UUIDs (version 4).",
    parameters={
        "type": "object",
        "properties": {"count": {"type": "integer", "description": "Number of UUIDs to generate (1-100, default 1)"}},
    },
    risk="low",
    category="dev",
)
async def uuid_generate(count: int = 1) -> str:
    """生成 UUID v4。count 夹到 [1,100]。"""
    count = max(1, min(int(count), 100))
    return "\n".join(str(_uuid.uuid4()) for _ in range(count))


@tool_registry.register(
    name="base64_encode",
    description="Encode a UTF-8 string to Base64.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to encode"}},
        "required": ["text"],
    },
    risk="low",
    category="dev",
)
async def base64_encode(text: str) -> str:
    """UTF-8 文本 → Base64。"""
    return _base64.b64encode(text.encode("utf-8")).decode("ascii")


@tool_registry.register(
    name="base64_decode",
    description="Decode a Base64 string to UTF-8 text.",
    parameters={
        "type": "object",
        "properties": {"b64": {"type": "string", "description": "Base64 string to decode"}},
        "required": ["b64"],
    },
    risk="low",
    category="dev",
)
async def base64_decode(b64: str) -> str:
    """Base64 → UTF-8 文本。"""
    try:
        return _base64.b64decode(b64.encode("ascii")).decode("utf-8")
    except Exception as e:
        return f"Error: {e}"


@tool_registry.register(
    name="url_encode",
    description="Percent-encode a string for safe use in a URL query parameter.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to URL-encode"}},
        "required": ["text"],
    },
    risk="low",
    category="dev",
)
async def url_encode(text: str) -> str:
    """文本 → URL 百分号编码。"""
    return urllib.parse.quote(text, safe="")


@tool_registry.register(
    name="url_decode",
    description="Decode a percent-encoded URL string back to plain text.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "URL-encoded text to decode"}},
        "required": ["text"],
    },
    risk="low",
    category="dev",
)
async def url_decode(text: str) -> str:
    """URL 百分号编码 → 原文。"""
    return urllib.parse.unquote(text)


@tool_registry.register(
    name="hash_text",
    description="Compute a cryptographic hash (md5, sha1, sha256) of a text.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to hash"},
            "algorithm": {"type": "string", "description": "Hash algorithm: md5, sha1, or sha256 (default sha256)"},
        },
        "required": ["text"],
    },
    risk="low",
    category="dev",
)
async def hash_text(text: str, algorithm: str = "sha256") -> str:
    """计算文本哈希。支持 md5/sha1/sha256。"""
    algo = (algorithm or "sha256").lower()
    if algo not in ("md5", "sha1", "sha256"):
        return f"Error: unsupported algorithm '{algorithm}' (use md5/sha1/sha256)"
    h = hashlib.new(algo)
    h.update(text.encode("utf-8"))
    return h.hexdigest()


@tool_registry.register(
    name="regex_test",
    description="Test a regular expression against a text and return match groups. Uses Python re syntax.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Python regular expression"},
            "text": {"type": "string", "description": "Text to search"},
            "flags": {"type": "string", "description": "Flags: IGNORECASE, MULTILINE, DOTALL (comma-separated, optional)"},
        },
        "required": ["pattern", "text"],
    },
    risk="low",
    category="dev",
)
async def regex_test(pattern: str, text: str, flags: str = "") -> str:
    """用正则匹配文本，返回所有匹配及其分组。"""
    flag = 0
    for f in (flags or "").split(","):
        f = f.strip().upper()
        if f == "IGNORECASE":
            flag |= re.IGNORECASE
        elif f == "MULTILINE":
            flag |= re.MULTILINE
        elif f == "DOTALL":
            flag |= re.DOTALL
    try:
        matches = list(re.finditer(pattern, text, flag))
    except re.error as e:
        return f"Error: invalid regex — {e}"
    if not matches:
        return "no matches"
    lines = []
    for i, m in enumerate(matches, 1):
        groups = m.groups()
        span = f"[{m.start()}:{m.end()}]"
        if groups:
            lines.append(f"{i}. match={m.group(0)!r} span={span} groups={list(groups)}")
        else:
            lines.append(f"{i}. match={m.group(0)!r} span={span}")
    return "\n".join(lines)


@tool_registry.register(
    name="string_case_convert",
    description="Convert text between common cases: camel, snake, kebab, title, upper, lower.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Input text"},
            "to_case": {"type": "string", "description": "Target case: camel, snake, kebab, title, upper, lower"},
        },
        "required": ["text", "to_case"],
    },
    risk="low",
    category="dev",
)
async def string_case_convert(text: str, to_case: str) -> str:
    """在不同命名风格间转换。"""
    # 先把任意分隔符切分成词
    words = re.split(r"[\s_\-]+|(?<=[a-z])(?=[A-Z])", text.strip())
    words = [w for w in words if w]
    if not words:
        return ""
    to_case = (to_case or "").lower()
    if to_case == "snake":
        return "_".join(w.lower() for w in words)
    if to_case == "kebab":
        return "-".join(w.lower() for w in words)
    if to_case == "camel":
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])
    if to_case == "title":
        return " ".join(w.capitalize() for w in words)
    if to_case == "upper":
        return text.upper()
    if to_case == "lower":
        return text.lower()
    return f"Error: unknown case '{to_case}' (use camel/snake/kebab/title/upper/lower)"


@tool_registry.register(
    name="text_stats",
    description="Count characters, words, lines, and sentences in a text.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to analyze"}},
        "required": ["text"],
    },
    risk="low",
    category="dev",
)
async def text_stats(text: str) -> str:
    """统计字符/单词/行数/句子数。"""
    chars = len(text)
    words = len(text.split())
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    sentences = max(1, len(re.findall(r"[.!?]+", text)))
    return (f"characters: {chars}\nwords: {words}\nlines: {lines}\nsentences: ~{sentences}")


@tool_registry.register(
    name="csv_to_json",
    description="Parse CSV text into a JSON array of row objects (first row as header).",
    parameters={
        "type": "object",
        "properties": {
            "csv_text": {"type": "string", "description": "CSV text"},
            "delimiter": {"type": "string", "description": "Column delimiter (default ',')"},
        },
        "required": ["csv_text"],
    },
    risk="low",
    category="dev",
)
async def csv_to_json(csv_text: str, delimiter: str = ",") -> str:
    """CSV → JSON 数组（首行为表头）。"""
    import csv as _csv
    import io
    try:
        reader = _csv.DictReader(io.StringIO(csv_text), delimiter=delimiter or ",")
        rows = [dict(r) for r in reader]
        return _json.dumps(rows, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: {e}"


@tool_registry.register(
    name="number_base_convert",
    description="Convert a number between binary, decimal, hexadecimal, and octal.",
    parameters={
        "type": "object",
        "properties": {
            "value": {"type": "string", "description": "Number value as string, e.g. '255' or '0xff' or '0b1010'"},
            "from_base": {"type": "string", "description": "Source base: bin, dec, hex, oct (default auto-detect by prefix)"},
        },
        "required": ["value"],
    },
    risk="low",
    category="dev",
)
async def number_base_convert(value: str, from_base: str = "") -> str:
    """数值在 bin/dec/hex/oct 间转换。from_base 留空则按前缀自动识别。"""
    v = (value or "").strip().lower()
    try:
        if not from_base:
            if v.startswith("0x"):
                n = int(v, 16)
            elif v.startswith("0b"):
                n = int(v, 2)
            elif v.startswith("0o"):
                n = int(v, 8)
            else:
                n = int(v, 10)
        else:
            base = from_base.lower()
            n = int(v, {"bin": 2, "dec": 10, "hex": 16, "oct": 8}[base])
    except Exception as e:
        return f"Error: {e}"
    return f"dec: {n}\nhex: {hex(n)}\noct: {oct(n)}\nbin: {bin(n)}"


@tool_registry.register(
    name="slugify",
    description="Convert text into a URL-friendly slug (lowercase, hyphen-separated, ascii-only).",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to slugify"}},
        "required": ["text"],
    },
    risk="low",
    category="dev",
)
async def slugify(text: str) -> str:
    """文本 → URL slug。非 ASCII 字符做音译近似。"""
    import unicodedata
    # Unicode 音译为 ASCII 近似
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^\w\s-]", "", ascii_text).strip().lower()
    return re.sub(r"[\s_-]+", "-", ascii_text).strip("-")


# ────────────────────────── 高级工具 ──────────────────────────

@tool_registry.register(
    name="password_generate",
    description="Generate a random secure password with configurable length and character sets.",
    parameters={
        "type": "object",
        "properties": {
            "length": {"type": "integer", "description": "Password length (8-128, default 16)"},
            "symbols": {"type": "boolean", "description": "Include symbol characters (default true)"},
            "numbers": {"type": "boolean", "description": "Include digits (default true)"},
            "uppercase": {"type": "boolean", "description": "Include uppercase letters (default true)"},
        },
    },
    risk="low",
    category="dev",
)
async def password_generate(length: int = 16, symbols: bool = True, numbers: bool = True, uppercase: bool = True) -> str:
    """生成安全随机密码。使用 secrets 模块。"""
    import secrets as _secrets
    import string as _string
    length = max(8, min(int(length), 128))
    pools = [_string.ascii_lowercase]
    if uppercase:
        pools.append(_string.ascii_uppercase)
    if numbers:
        pools.append(_string.digits)
    if symbols:
        pools.append("!@#$%^&*()-_=+[]{};:,.?/")
    all_chars = "".join(pools)
    # 保证每个字符集至少出现一个
    pwd = [_secrets.choice(p) for p in pools]
    pwd += [_secrets.choice(all_chars) for _ in range(length - len(pools))]
    _secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)


@tool_registry.register(
    name="color_convert",
    description="Convert colors between hex (e.g. '#ff8800') and rgb 'r,g,b'.",
    parameters={
        "type": "object",
        "properties": {
            "value": {"type": "string", "description": "Color value, e.g. '#ff8800' or '255,136,0'"},
            "to_format": {"type": "string", "description": "Target format: 'hex' or 'rgb'"},
        },
        "required": ["value", "to_format"],
    },
    risk="low",
    category="dev",
)
async def color_convert(value: str, to_format: str) -> str:
    """hex ↔ rgb 互转。"""
    to_format = (to_format or "").lower()
    v = value.strip()
    if to_format == "hex":
        # 输入应为 r,g,b
        try:
            parts = [int(p) for p in re.split(r"[,\s]+", v) if p]
            if len(parts) != 3:
                return "Error: rgb input must be 'r,g,b'"
            return "#{:02x}{:02x}{:02x}".format(*parts)
        except Exception as e:
            return f"Error: {e}"
    if to_format == "rgb":
        m = re.fullmatch(r"#?([0-9a-fA-F]{6})", v)
        if not m:
            return "Error: hex input must be '#rrggbb' or 'rrggbb'"
        r = int(m.group(1)[0:2], 16)
        g = int(m.group(1)[2:4], 16)
        b = int(m.group(1)[4:6], 16)
        return f"{r},{g},{b}"
    return f"Error: unknown format '{to_format}' (use hex/rgb)"


@tool_registry.register(
    name="jwt_decode",
    description="Decode a JWT's header and payload (no signature verification). For inspection only.",
    parameters={
        "type": "object",
        "properties": {"token": {"type": "string", "description": "JWT token string"}},
        "required": ["token"],
    },
    risk="low",
    category="dev",
)
async def jwt_decode(token: str) -> str:
    """解码 JWT 的 header 与 payload（不验证签名）。"""
    parts = token.strip().split(".")
    if len(parts) < 2:
        return "Error: not a valid JWT (expected 3 segments)"
    def _b64url_decode(s: str) -> bytes:
        s += "=" * (-len(s) % 4)
        return _base64.urlsafe_b64decode(s.encode("ascii"))
    try:
        header = _json.loads(_b64url_decode(parts[0]))
        payload = _json.loads(_b64url_decode(parts[1]))
        return _json.dumps({"header": header, "payload": payload}, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"Error: failed to decode JWT — {e}"


@tool_registry.register(
    name="yaml_json_convert",
    description="Convert between YAML and JSON. direction: 'yaml_to_json' or 'json_to_yaml'.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Source text"},
            "direction": {"type": "string", "description": "'yaml_to_json' or 'json_to_yaml'"},
        },
        "required": ["text", "direction"],
    },
    risk="low",
    category="dev",
)
async def yaml_json_convert(text: str, direction: str) -> str:
    """YAML ↔ JSON 互转。依赖 pyyaml（未安装时返回错误）。"""
    try:
        import yaml  # type: ignore
    except Exception:
        return "Error: pyyaml not installed"
    direction = (direction or "").lower()
    try:
        if direction == "yaml_to_json":
            data = yaml.safe_load(text)
            return _json.dumps(data, ensure_ascii=False, indent=2)
        if direction == "json_to_yaml":
            data = _json.loads(text)
            return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        return f"Error: unknown direction '{direction}' (use yaml_to_json/json_to_yaml)"
    except Exception as e:
        return f"Error: {e}"
