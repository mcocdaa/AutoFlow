# @file /backend/tests/test_output_externalizer.py
# @brief 大输出落盘与索引返回测试
# @create 2026-02-22 00:00:00

from __future__ import annotations

from pathlib import Path

from app.runtime.utils.output_externalizer import externalize_if_large


def test_externalize_if_large_writes_artifact(tmp_path: Path) -> None:
    big = "a" * (70 * 1024)
    out = externalize_if_large(big, artifacts_dir=tmp_path, file_stem="x", max_bytes=64 * 1024)
    assert isinstance(out, dict)
    assert "__artifact__" in out
    rel = out["__artifact__"]["path"]
    assert (tmp_path / rel).exists()
