# @file /backend/tests/test_mcp_flows.py
# @brief 测试 MCP Flow 目录扫描与名称解析
# @create 2026-09-18

from __future__ import annotations

from pathlib import Path

import pytest
from app.mcp.flows import resolve_flow, scan_flows

VALID_FLOW = """\
version: "1"
name: alpha
description: demo flow
steps:
  - id: s1
    action:
      type: dummy.echo
      params:
        message: hi
"""


def _write(flows_dir: Path, name: str, text: str) -> None:
    (flows_dir / name).write_text(text, encoding="utf-8")


def test_scan_flows_reports_valid_and_invalid(tmp_path: Path) -> None:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()
    _write(flows_dir, "a.flow.yaml", VALID_FLOW)
    _write(flows_dir, "b.yaml", "steps: [")
    _write(flows_dir, "note.txt", "ignore me")

    entries = scan_flows(flows_dir)

    assert [e["file"] for e in entries] == ["a.flow.yaml", "b.yaml"]
    valid = entries[0]
    assert valid == {
        "file": "a.flow.yaml",
        "name": "alpha",
        "description": "demo flow",
        "steps": 1,
    }
    assert "error" in entries[1]


def test_scan_flows_missing_dir_is_empty(tmp_path: Path) -> None:
    assert scan_flows(tmp_path / "missing") == []


def test_resolve_flow_by_stem_and_name(tmp_path: Path) -> None:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()
    _write(flows_dir, "a.flow.yaml", VALID_FLOW)

    stem_name, stem_text = resolve_flow(flows_dir, "a.flow")
    short_name, short_text = resolve_flow(flows_dir, "a")
    name, text = resolve_flow(flows_dir, "alpha")

    assert stem_name == "alpha"
    assert short_name == "alpha"
    assert name == "alpha"
    assert stem_text == short_text == text == VALID_FLOW


def test_resolve_flow_missing_lists_available(tmp_path: Path) -> None:
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()
    _write(flows_dir, "a.flow.yaml", VALID_FLOW)

    with pytest.raises(ValueError) as excinfo:
        resolve_flow(flows_dir, "missing")

    assert "alpha" in str(excinfo.value)
