# @file /backend/app/core/secrets_vault.py
# @brief AES-256-GCM 敏感凭据保密柜与全链路日志/产物正则脱敏
# @create 2026-09-20

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    import fcntl
except ImportError:  # pragma: no cover - 非 POSIX 平台降级为无锁
    fcntl = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# 预设高危敏感信息正则匹配模式
SENSITIVE_PATTERNS: list[re.Pattern] = [
    # 常见 API Key (OpenAI, DeepSeek, Claude, GitHub etc.)
    re.compile(r"\b(sk-[a-zA-Z0-9]{20,})\b"),
    re.compile(r"\b(ghp_[a-zA-Z0-9]{20,})\b"),
    re.compile(r"\b(gho_[a-zA-Z0-9]{20,})\b"),
    # Bearer Token
    re.compile(r"(?i)\bBearer\s+([a-zA-Z0-9\._\-]{20,})\b"),
    # 密码字段格式: password: "xyz" or password="xyz"
    re.compile(
        r"(?i)(password|secret|token|api_key|apikey)\s*[:=]\s*[\"']?([^\"'\s,;]{6,})[\"']?"
    ),
]


class SecretsVault:
    """AES-256-GCM 本地加密凭据保密柜"""

    def __init__(self, data_dir: Path, master_key: str | None = None) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._vault_file = self._data_dir / "vault.enc"
        self._vault_mtime: float | None = None
        self._aesgcm = AESGCM(self._resolve_key(master_key))
        self._cache: dict[str, str] = {}
        self._load_from_disk()

    @contextmanager
    def _file_lock(self) -> Iterator[None]:
        """跨进程文件锁，保护 .vault_key 生成与 vault.enc 读写"""
        lock_path = self._data_dir / ".vault.lock"
        handle = open(lock_path, "w", encoding="utf-8")
        try:
            if fcntl is not None:
                fcntl.flock(handle, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle, fcntl.LOCK_UN)
            handle.close()

    def _resolve_key(self, master_key: str | None) -> bytes:
        """解析或生成 256 位 (32 字节) 主密钥"""
        if master_key:
            return hashlib.sha256(master_key.encode("utf-8")).digest()

        key_file = self._data_dir / ".vault_key"
        with self._file_lock():
            if key_file.is_file():
                try:
                    key_bytes = key_file.read_bytes()
                    if len(key_bytes) == 32:
                        return key_bytes
                except OSError:
                    pass

            new_key = os.urandom(32)
            try:
                tmp_key = self._data_dir / ".vault_key.tmp"
                tmp_key.write_bytes(new_key)
                # 仅限所有者读写
                tmp_key.chmod(0o600)
                tmp_key.replace(key_file)
            except OSError as e:
                logger.warning("Could not persist vault key file: %s", e)
            return new_key

    def _get_vault_mtime(self) -> float | None:
        try:
            if self._vault_file.is_file():
                return self._vault_file.stat().st_mtime
        except OSError:
            pass
        return None

    def _load_from_disk(self) -> None:
        """从密文文件解密载入凭据"""
        if not self._vault_file.is_file():
            self._cache = {}
            self._vault_mtime = None
            return

        try:
            mtime = self._get_vault_mtime()
            raw = self._vault_file.read_bytes()
            if not raw:
                self._cache = {}
                self._vault_mtime = mtime
                return
            decrypted = self.decrypt_bytes(raw)
            self._cache = json.loads(decrypted.decode("utf-8"))
            self._vault_mtime = mtime
        except Exception as e:
            logger.warning("Failed to decrypt vault file: %s, initializing empty", e)
            self._cache = {}
            self._vault_mtime = None

    def _load_vault(self) -> None:
        """向后兼容别名"""
        self._load_from_disk()

    def _refresh_if_needed(self) -> None:
        """若跨进程更新了 vault.enc，自动重载"""
        current_mtime = self._get_vault_mtime()
        if current_mtime != self._vault_mtime:
            self._load_from_disk()

    def _persist(self) -> None:
        """将缓存中的凭据加密持久化"""
        plaintext = json.dumps(self._cache, ensure_ascii=False).encode("utf-8")
        ciphertext = self.encrypt_bytes(plaintext)
        tmp = self._vault_file.with_suffix(".tmp")
        tmp.write_bytes(ciphertext)
        tmp.replace(self._vault_file)
        self._vault_mtime = self._get_vault_mtime()

    def encrypt_bytes(self, data: bytes) -> bytes:
        """AES-256-GCM 加密: 12 字节 nonce + 密文 + tag"""
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_bytes(self, raw: bytes) -> bytes:
        """AES-256-GCM 解密"""
        if len(raw) < 12:
            raise ValueError("Invalid encrypted payload (too short)")
        nonce = raw[:12]
        ciphertext = raw[12:]
        return self._aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt(self, plaintext: str) -> str:
        """加密文本并返回 base64 字符串"""
        encrypted = self.encrypt_bytes(plaintext.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("ascii")

    def decrypt(self, ciphertext_b64: str) -> str:
        """解密 base64 字符串为明文"""
        raw = base64.urlsafe_b64decode(ciphertext_b64.encode("ascii"))
        return self.decrypt_bytes(raw).decode("utf-8")

    def set_secret(self, key: str, value: str) -> None:
        """存储敏感凭据"""
        with self._lock, self._file_lock():
            self._refresh_if_needed()
            self._cache[key] = value
            self._persist()

    def get_secret(self, key: str) -> str | None:
        """获取敏感凭据明文"""
        with self._lock:
            self._refresh_if_needed()
            return self._cache.get(key)

    def delete_secret(self, key: str) -> bool:
        """删除敏感凭据"""
        with self._lock, self._file_lock():
            self._refresh_if_needed()
            if key in self._cache:
                del self._cache[key]
                self._persist()
                return True
            return False

    def list_secrets(self) -> list[dict[str, str]]:
        """列出所有凭据（值脱敏）"""
        with self._lock:
            self._refresh_if_needed()
            result = []
            for k, v in self._cache.items():
                if len(v) <= 4:
                    masked = "****"
                else:
                    masked = f"{v[:2]}****{v[-2:]}"
                result.append({"key": k, "masked_value": masked})
            return result

    def get_all_secrets(self) -> dict[str, str]:
        """获取全部凭据字典（供运行时模板解析使用）"""
        with self._lock:
            self._refresh_if_needed()
            return dict(self._cache)

    def mask_text(self, text: str) -> str:
        """全链路脱敏：对文本应用预设特征正则与保密柜中的所有已知密钥"""
        if not text:
            return text

        result = text

        # 1. 保密柜内已知真实凭据脱敏 (长于 3 字符的全部掩码)
        with self._lock:
            self._refresh_if_needed()
            for val in self._cache.values():
                if val and len(val) >= 3 and val in result:
                    result = result.replace(val, "***REDACTED***")

        # 2. 正则特征脱敏
        for pat in SENSITIVE_PATTERNS:

            def _replace(m: re.Match) -> str:
                # 若捕获组存在，仅脱敏捕获组部分
                if m.lastindex and m.lastindex >= 1:
                    full = m.group(0)
                    secret = m.group(m.lastindex)
                    if len(secret) <= 6:
                        masked = "***REDACTED***"
                    else:
                        masked = f"{secret[:3]}****{secret[-3:]}"
                    return full.replace(secret, masked)
                return "***REDACTED***"

            result = pat.sub(_replace, result)

        return result

    def mask_data(self, data: Any) -> Any:
        """递归对结构化对象中所有字符串执行脱敏"""
        if isinstance(data, str):
            return self.mask_text(data)
        if isinstance(data, dict):
            return {k: self.mask_data(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.mask_data(item) for item in data]
        return data


_vault_instance: SecretsVault | None = None


def get_secrets_vault() -> SecretsVault:
    global _vault_instance
    if _vault_instance is None:
        from app.core.setting_manager import setting_manager
        from app.runtime import get_store

        data_dir = get_store().artifacts_dir / "vault"
        master_key = str(setting_manager.get("VAULT_SECRET_KEY") or "")
        _vault_instance = SecretsVault(data_dir, master_key=master_key or None)
    return _vault_instance
