"""开发工具单测 — 验证 JSON / 时间戳 / 编码 等工具的核心逻辑。"""
import pytest

from app.tools.dev_tools import (
    json_format, json_validate, json_path,
    timestamp_to_date, date_to_timestamp, timestamp_now,
    uuid_generate, base64_encode, base64_decode, url_encode,
)


@pytest.mark.asyncio
async def test_json_format_pretty_and_minify():
    pretty = await json_format('{"a":1,"b":[2,3]}', indent=2)
    assert '"a": 1' in pretty
    assert "\n" in pretty
    mini = await json_format('{"a":1,"b":[2,3]}', indent=0)
    assert "\n" not in mini
    assert mini == '{"a":1,"b":[2,3]}'


@pytest.mark.asyncio
async def test_json_format_invalid():
    assert "Error" in await json_format("{bad}")


@pytest.mark.asyncio
async def test_json_validate_ok_and_bad():
    assert "valid" in await json_validate('{"x":1}')
    res = await json_validate('{"x": 1,}')
    assert "Error" in res and "line" in res


@pytest.mark.asyncio
async def test_json_path_extraction():
    data = '{"users":[{"name":"alice","tags":["a","b"]},{"name":"bob"}]}'
    assert await json_path(data, "users[0].name") == "alice"
    assert await json_path(data, "users[1].name") == "bob"
    assert await json_path(data, "users[0].tags[0]") == "a"
    assert "not found" in await json_path(data, "users[0].nope")


@pytest.mark.asyncio
async def test_timestamp_to_date_seconds_and_ms():
    # 1700000000 秒
    res = await timestamp_to_date(1700000000)
    assert "2023" in res
    # 同样的毫秒值应得到相同日期
    res_ms = await timestamp_to_date(1700000000000)
    assert res.split(" (")[0] == res_ms.split(" (")[0]
    # 时区偏移
    res_tz = await timestamp_to_date(1700000000, timezone_offset=8)
    assert "UTC+8" in res_tz


@pytest.mark.asyncio
async def test_date_to_timestamp_roundtrip():
    ts = await date_to_timestamp("2024-01-15 12:30:00")
    assert int(ts) > 0
    # 往返
    again = await timestamp_to_date(int(ts))
    assert "2024-01-15 12:30:00" in again
    assert "Error" in await date_to_timestamp("not a date")


@pytest.mark.asyncio
async def test_timestamp_now():
    res = await timestamp_now()
    assert "seconds:" in res and "milliseconds:" in res and "iso_utc:" in res


@pytest.mark.asyncio
async def test_uuid_generate_count():
    one = await uuid_generate()
    assert len(one) == 36  # 标准 UUID 长度
    multi = await uuid_generate(5)
    assert len(multi.split("\n")) == 5
    # 唯一性
    assert len(set(multi.split("\n"))) == 5


@pytest.mark.asyncio
async def test_base64_roundtrip():
    enc = await base64_encode("hello 世界")
    assert "hello 世界" == await base64_decode(enc)
    assert "Error" in await base64_decode("!!!notb64!!!")


@pytest.mark.asyncio
async def test_url_encode():
    assert await url_encode("a b/c?d=e") == "a%20b%2Fc%3Fd%3De"


import pytest

from app.tools.dev_tools import (
    url_decode, hash_text, regex_test, string_case_convert,
    text_stats, csv_to_json, number_base_convert, slugify,
)


@pytest.mark.asyncio
async def test_url_decode():
    assert await url_decode("a%20b%2Fc%3Fd%3De") == "a b/c?d=e"


@pytest.mark.asyncio
async def test_hash_text():
    sha = await hash_text("hello", algorithm="sha256")
    assert len(sha) == 64
    md5 = await hash_text("hello", algorithm="md5")
    assert md5 == "5d41402abc4b2a76b9719d911017c592"
    assert "Error" in await hash_text("x", algorithm="nope")


@pytest.mark.asyncio
async def test_regex_test():
    res = await regex_test(r"(\w+)@(\w+)", "alice@a.com bob@b.org")
    assert "alice@a" in res and "bob@b" in res
    assert "no matches" in await regex_test(r"zzz", "abc")
    assert "invalid regex" in await regex_test("(unclosed", "abc")


@pytest.mark.asyncio
async def test_string_case_convert():
    assert await string_case_convert("hello world foo", "camel") == "helloWorldFoo"
    assert await string_case_convert("helloWorldFoo", "snake") == "hello_world_foo"
    assert await string_case_convert("hello_world", "kebab") == "hello-world"
    assert await string_case_convert("hello world", "title") == "Hello World"
    assert "Error" in await string_case_convert("x", "weird")


@pytest.mark.asyncio
async def test_text_stats():
    res = await text_stats("Hello world. This is a test!\nNew line.")
    assert "characters:" in res and "words: 8" in res and "lines: 2" in res


@pytest.mark.asyncio
async def test_csv_to_json():
    csv_text = "name,age\nalice,30\nbob,25"
    res = await csv_to_json(csv_text)
    import json
    data = json.loads(res)
    assert data == [{"name": "alice", "age": "30"}, {"name": "bob", "age": "25"}]


@pytest.mark.asyncio
async def test_number_base_convert():
    res = await number_base_convert("255")
    assert "dec: 255" in res and "hex: 0xff" in res and "bin: 0b11111111" in res
    res2 = await number_base_convert("0xff")
    assert "dec: 255" in res2
    assert "Error" in await number_base_convert("notnum")


@pytest.mark.asyncio
async def test_slugify():
    assert await slugify("Hello, World! 你好") == "hello-world"
    assert await slugify("  Foo  Bar  ") == "foo-bar"


from app.tools.dev_tools import password_generate, color_convert, jwt_decode, yaml_json_convert


@pytest.mark.asyncio
async def test_password_generate():
    pwd = await password_generate(length=20)
    assert len(pwd) == 20
    import string
    # 含小写（默认必选池）
    assert any(c in string.ascii_lowercase for c in pwd)
    # 不含符号时
    pwd_nosym = await password_generate(length=12, symbols=False)
    assert len(pwd_nosym) == 12
    assert not any(c in "!@#$%^&*()-_=+[]{};:,.?/" for c in pwd_nosym)


@pytest.mark.asyncio
async def test_color_convert():
    assert await color_convert("255,136,0", "hex") == "#ff8800"
    assert await color_convert("#ff8800", "rgb") == "255,136,0"
    assert "Error" in await color_convert("bad", "rgb")
    assert "Error" in await color_convert("#ff8800", "weird")


@pytest.mark.asyncio
async def test_jwt_decode():
    # eyJhbGciOiJub25lIn0.eyJzdWIiOiJhbGljZSJ9.  (header {alg:none}, payload {sub:alice}, empty sig)
    token = "eyJhbGciOiJub25lIn0.eyJzdWIiOiJhbGljZSJ9."
    res = await jwt_decode(token)
    import json
    data = json.loads(res)
    assert data["header"] == {"alg": "none"}
    assert data["payload"] == {"sub": "alice"}
    assert "Error" in await jwt_decode("not.a.jwt")


@pytest.mark.asyncio
async def test_yaml_json_convert():
    yaml_text = "name: alice\nage: 30\ntags:\n  - a\n  - b\n"
    res = await yaml_json_convert(yaml_text, "yaml_to_json")
    import json
    data = json.loads(res)
    assert data == {"name": "alice", "age": 30, "tags": ["a", "b"]}
    back = await yaml_json_convert(json.dumps({"x": 1, "y": [1, 2]}), "json_to_yaml")
    assert "x: 1" in back and "y:" in back
    assert "Error" in await yaml_json_convert("x", "weird")
