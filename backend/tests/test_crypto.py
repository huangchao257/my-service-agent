"""静态加密单测 — 验证 encrypt/decrypt 的启用与降级路径。"""
import os
import pytest

from app.core import crypto


def test_disabled_when_no_key(monkeypatch):
    """未配置 ENCRYPTION_KEY 时退化为明文。"""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    crypto._FERNET = None
    crypto._INITIALIZED = False
    assert crypto.is_encryption_enabled() is False
    assert crypto.encrypt("sk-secret") == "sk-secret"
    assert crypto.decrypt("sk-secret") == "sk-secret"


def test_empty_values_passthrough(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)
    crypto._FERNET = None
    crypto._INITIALIZED = False
    assert crypto.encrypt("") == ""
    assert crypto.decrypt("") == ""


def test_round_trip_when_enabled(monkeypatch):
    """配置合法 Fernet 密钥时加解密往返一致，且密文以 gAAAAA 开头。"""
    cryptography = pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("ENCRYPTION_KEY", key)
    crypto._FERNET = None
    crypto._INITIALIZED = False

    assert crypto.is_encryption_enabled() is True
    cipher = crypto.encrypt("sk-secret-1234567890")
    assert cipher != "sk-secret-1234567890"
    assert cipher.startswith("gAAAAA")
    assert crypto.decrypt(cipher) == "sk-secret-1234567890"
    # 明文（历史数据）原样返回
    assert crypto.decrypt("legacy-plaintext-key") == "legacy-plaintext-key"


def test_decrypt_with_wrong_key_returns_original(monkeypatch):
    """密钥轮换后解密失败时返回原值，不抛异常。"""
    pytest.importorskip("cryptography")
    from cryptography.fernet import Fernet
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto._FERNET = None
    crypto._INITIALIZED = False
    cipher = crypto.encrypt("secret")
    # 换一把密钥
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    crypto._FERNET = None
    crypto._INITIALIZED = False
    # 解密失败，返回原密文（不抛异常）
    result = crypto.decrypt(cipher)
    assert result == cipher
