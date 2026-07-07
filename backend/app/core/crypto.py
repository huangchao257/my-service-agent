"""API Key 静态加密 — 基于 Fernet 对称加密，密钥来自环境变量 ENCRYPTION_KEY。

设计：
- `cryptography` 为可选依赖；未安装或未配置 ENCRYPTION_KEY 时退化为明文存储
  （向后兼容已有数据），不阻断任何写读路径。
- 加密产物是 Fernet token（以 "gAAAAA" 开头）；decrypt 自动识别：
  是 token 则解密，否则按明文原样返回（兼容历史明文数据）。
- 密钥缺失时 encrypt 直接返回明文，与 decrypt 行为对称。

安全说明：本方案保护的是「静态数据落库时的密钥」——即使 DB 泄露，
没有 ENCRYPTION_KEY 也无法还原 api_key。运行期解密在内存中进行。
"""
import os

_FERNET = None
_INITIALIZED = False


def _get_fernet():
    """惰性初始化 Fernet 实例。返回 None 表示加密不可用（降级为明文）。"""
    global _FERNET, _INITIALIZED
    if _INITIALIZED:
        return _FERNET
    _INITIALIZED = True
    key = os.environ.get("ENCRYPTION_KEY")
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet  # type: ignore
        _FERNET = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        _FERNET = None
    return _FERNET


def is_encryption_enabled() -> bool:
    """是否启用了静态加密（库可用 + 密钥已配置）。"""
    return _get_fernet() is not None


def encrypt(plaintext: str) -> str:
    """加密明文。未启用加密时原样返回明文。"""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    if f is None:
        return plaintext
    try:
        return f.encrypt(plaintext.encode("utf-8")).decode("ascii")
    except Exception:
        return plaintext


def decrypt(value: str) -> str:
    """解密。识别 Fernet token；非 token（历史明文）原样返回。未启用加密时原样返回。"""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    # Fernet token 特征前缀，快速跳过明文
    if not value.startswith("gAAAAA"):
        return value
    try:
        return f.decrypt(value.encode("ascii")).decode("utf-8")
    except Exception:
        # 解密失败（密钥轮换/损坏）：返回原值，让上层照常走明文路径
        return value
