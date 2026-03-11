# @file /backend/app/runtime/flow_loader.py
# @brief Flow YAML/文件加载与校验
# @create 2026-02-21 00:00:00

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.runtime.models import FlowSpec


class FlowLoadError(ValueError):
    pass


def load_flow_spec_from_mapping(data: dict[str, Any]) -> FlowSpec:
    try:
        return FlowSpec.model_validate(data)
    except Exception as e:
        raise FlowLoadError(str(e)) from e


def load_flow_spec_from_yaml_text(yaml_text: str) -> FlowSpec:
    try:
        loaded = yaml.safe_load(yaml_text)
    except Exception as e:
        raise FlowLoadError(f"invalid yaml: {e}") from e
    if not isinstance(loaded, dict):
        raise FlowLoadError("flow yaml must be a mapping")
    return load_flow_spec_from_mapping(loaded)


def load_flow_spec_from_file(file_path: str | Path) -> FlowSpec:
    p = Path(file_path)
    if not p.exists():
        raise FlowLoadError(f"flow file not found: {p}")
    return load_flow_spec_from_yaml_text(p.read_text(encoding="utf-8"))
