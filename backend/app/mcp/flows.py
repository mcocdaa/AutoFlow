# @file /backend/app/mcp/flows.py
# @brief MCP Flow 目录扫描与名称解析
# @create 2026-09-18

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from app.runtime.loaders import FlowLoadError, load_flow_spec_from_yaml_text

FLOW_SUFFIXES = {".yaml", ".yml"}


def _flow_files(flows_dir: Path) -> list[Path]:
    """目录内 Flow 候选文件(非递归、排序稳定);目录不存在返回空"""
    if not flows_dir.is_dir():
        return []
    return sorted(
        path
        for path in flows_dir.iterdir()
        if path.is_file() and path.suffix.lower() in FLOW_SUFFIXES
    )


def scan_flows(flows_dir: Path) -> list[dict[str, Any]]:
    """扫描 Flow 文件:合法项含 name/description/steps,坏文件以 error 字段返回"""
    entries: list[dict[str, Any]] = []
    for path in _flow_files(flows_dir):
        try:
            text = path.read_text(encoding="utf-8")
            flow = load_flow_spec_from_yaml_text(text)
            data = yaml.safe_load(text)
        except (FlowLoadError, OSError, ValueError) as e:
            entries.append({"file": path.name, "error": str(e)})
            continue
        description = data.get("description") if isinstance(data, dict) else None
        entries.append(
            {
                "file": path.name,
                "name": flow.name,
                "description": description,
                "steps": len(flow.steps),
            }
        )
    return entries


def resolve_flow(flows_dir: Path, flow_name: str) -> tuple[str, str]:
    """按文件 stem(含去 .flow 后缀)或 Flow name 解析,返回 (flow.name, yaml_text)"""
    candidates: list[tuple[str, str, str]] = []
    for path in _flow_files(flows_dir):
        try:
            text = path.read_text(encoding="utf-8")
            flow = load_flow_spec_from_yaml_text(text)
        except (FlowLoadError, OSError, ValueError):
            continue
        candidates.append((path.stem, flow.name, text))
        if path.stem == flow_name:
            return flow.name, text
    for stem, name, text in candidates:
        if stem.removesuffix(".flow") == flow_name or name == flow_name:
            return name, text
    available = sorted(
        {stem for stem, _, _ in candidates} | {name for _, name, _ in candidates}
    )
    listing = ", ".join(available) if available else "无"
    raise ValueError(f"flow not found: {flow_name} (available: {listing})")
