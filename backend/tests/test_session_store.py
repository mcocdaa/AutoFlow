# @file /backend/tests/test_session_store.py
# @brief 测试 SessionStore:落盘读写、删除、锁上下文、跨实例一致
# @create 2026-09-15

from __future__ import annotations

from pathlib import Path

import pytest
from app.runtime.storage.session_store import SessionStore


def test_save_and_get_across_instances(tmp_path: Path) -> None:
    SessionStore(tmp_path).save("s1", {"index": 1, "flow": {"name": "demo"}})

    state = SessionStore(tmp_path).get("s1")

    assert state["index"] == 1
    assert state["flow"]["name"] == "demo"


def test_get_missing_raises_key_error(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)

    assert store.exists("missing") is False
    with pytest.raises(KeyError):
        store.get("missing")


def test_delete_removes_session(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    store.save("s1", {"index": 0})

    store.delete("s1")

    assert store.exists("s1") is False


def test_locked_context_is_reentrant_across_calls(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)

    with store.locked("s1"):
        store.save("s1", {"index": 0})

    with store.locked("s1"):
        state = store.get("s1")

    assert state["index"] == 0


def test_lock_file_lives_in_sessions_dir(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)

    with store.locked("s1"):
        assert (tmp_path / "_sessions" / "s1.lock").exists()
