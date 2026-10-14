# @file /backend/app/api/v1/flows.py
# @brief 服务端 Flow YAML 文件 CRUD 接口 (/api/v1/flows)
# @create 2026-10-14

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from app.core.setting_manager import setting_manager
from app.runtime.loaders import FlowLoadError, load_flow_spec_from_yaml_text
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flows", tags=["flows"])

SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
FLOW_SUFFIXES = {".yaml", ".yml"}


class FlowRecord(BaseModel):
    slug: str
    filename: str
    name: str
    version: str
    description: str | None = None
    steps_count: int
    webhook_enabled: bool = False
    updated_at: str
    flow_yaml: str


class SaveFlowRequest(BaseModel):
    slug: str | None = None
    flow_yaml: str = Field(..., min_length=1)


def _flows_dir() -> Path:
    return Path(setting_manager.FLOWS_DIR)


def validate_flow_slug(slug: str) -> str:
    """校验 slug 合法性，防止路径穿越攻击"""
    cleaned = slug.strip()
    if not cleaned or not SLUG_PATTERN.fullmatch(cleaned):
        raise ValueError(f"Invalid flow slug: {slug}")
    return cleaned


def _slug_from_path(path: Path) -> str:
    return path.stem.removesuffix(".flow")


def _ensure_within_flows_dir(flows_dir: Path, target: Path) -> Path:
    base = flows_dir.resolve()
    resolved = target.resolve()
    if not resolved.is_relative_to(base):
        raise ValueError(f"Path traversal denied: {target}")
    return resolved


def _build_flow_record(path: Path, text: str | None = None) -> FlowRecord:
    raw_yaml = text if text is not None else path.read_text(encoding="utf-8")
    flow = load_flow_spec_from_yaml_text(raw_yaml)
    stat = path.stat()
    updated_at = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()
    webhook_enabled = bool(flow.trigger and flow.trigger.webhook_enabled)
    return FlowRecord(
        slug=_slug_from_path(path),
        filename=path.name,
        name=flow.name,
        version=flow.version,
        description=flow.description,
        steps_count=len(flow.steps),
        webhook_enabled=webhook_enabled,
        updated_at=updated_at,
        flow_yaml=raw_yaml,
    )


def list_flow_records(flows_dir: Path) -> list[FlowRecord]:
    """扫描 flows/ 目录下所有合法的 YAML 流程文件"""
    if not flows_dir.is_dir():
        return []

    records_by_slug: dict[str, FlowRecord] = {}
    candidates = sorted(
        path
        for path in flows_dir.iterdir()
        if path.is_file() and path.suffix.lower() in FLOW_SUFFIXES
    )
    for path in candidates:
        slug = _slug_from_path(path)
        if not SLUG_PATTERN.fullmatch(slug):
            continue
        try:
            record = _build_flow_record(path)
        except (FlowLoadError, OSError, ValueError) as e:
            logger.warning("Skipping invalid flow file %s: %s", path.name, e)
            continue
        # 优先保留标准 {slug}.yaml 文件
        if slug not in records_by_slug or path.name == f"{slug}.yaml":
            records_by_slug[slug] = record

    return list(records_by_slug.values())


def _find_flow_file(flows_dir: Path, slug: str) -> Path | None:
    cleaned = validate_flow_slug(slug)
    if not flows_dir.is_dir():
        return None

    candidate_names = [
        f"{cleaned}.yaml",
        f"{cleaned}.flow.yaml",
        f"{cleaned}.yml",
        f"{cleaned}.flow.yml",
    ]
    for name in candidate_names:
        candidate = _ensure_within_flows_dir(flows_dir, flows_dir / name)
        if candidate.is_file():
            return candidate

    return None


def get_flow_record(flows_dir: Path, slug: str) -> FlowRecord:
    """读取指定 slug 的 FlowRecord"""
    path = _find_flow_file(flows_dir, slug)
    if path is None:
        raise FileNotFoundError(f"Flow not found: {slug}")
    return _build_flow_record(path)


def save_flow_record(
    flows_dir: Path,
    *,
    slug: str | None,
    flow_yaml: str,
) -> FlowRecord:
    """校验并保存 Flow YAML 到 flows/{slug}.yaml"""
    flow = load_flow_spec_from_yaml_text(flow_yaml)
    raw_slug = slug if (slug is not None and slug.strip()) else flow.name
    cleaned_slug = validate_flow_slug(raw_slug)

    flows_dir.mkdir(parents=True, exist_ok=True)
    target = _ensure_within_flows_dir(flows_dir, flows_dir / f"{cleaned_slug}.yaml")
    target.write_text(flow_yaml, encoding="utf-8")

    # 清理同名旧后缀文件，保持单一权威文件
    for alt_name in (
        f"{cleaned_slug}.flow.yaml",
        f"{cleaned_slug}.yml",
        f"{cleaned_slug}.flow.yml",
    ):
        alt_path = _ensure_within_flows_dir(flows_dir, flows_dir / alt_name)
        if alt_path != target and alt_path.is_file():
            try:
                alt_path.unlink()
            except OSError:
                pass

    return _build_flow_record(target, text=flow_yaml)


def delete_flow_record(flows_dir: Path, slug: str) -> None:
    """删除指定 slug 的 Flow 文件"""
    cleaned_slug = validate_flow_slug(slug)
    if not flows_dir.is_dir():
        raise FileNotFoundError(f"Flow not found: {cleaned_slug}")

    deleted = False
    for name in (
        f"{cleaned_slug}.yaml",
        f"{cleaned_slug}.flow.yaml",
        f"{cleaned_slug}.yml",
        f"{cleaned_slug}.flow.yml",
    ):
        candidate = _ensure_within_flows_dir(flows_dir, flows_dir / name)
        if candidate.is_file():
            candidate.unlink()
            deleted = True

    if not deleted:
        raise FileNotFoundError(f"Flow not found: {cleaned_slug}")


@router.get("", response_model=list[FlowRecord])
def list_flows() -> list[FlowRecord]:
    """扫描服务端 flows/ 目录并返回全部合法的 FlowRecord 列表"""
    return list_flow_records(_flows_dir())


@router.post("", response_model=FlowRecord)
def create_or_save_flow(req: SaveFlowRequest) -> FlowRecord:
    """校验并保存 Flow YAML 到服务端 flows/{slug}.yaml"""
    try:
        return save_flow_record(_flows_dir(), slug=req.slug, flow_yaml=req.flow_yaml)
    except (FlowLoadError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{slug:path}", response_model=FlowRecord)
def get_flow(slug: str) -> FlowRecord:
    """按 slug 获取服务端单个 FlowRecord"""
    try:
        return get_flow_record(_flows_dir(), slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except FlowLoadError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/{slug:path}", response_model=FlowRecord)
def put_flow(slug: str, req: SaveFlowRequest) -> FlowRecord:
    """按 slug 校验并写入服务端 flows/{slug}.yaml"""
    try:
        cleaned_slug = validate_flow_slug(slug)
        return save_flow_record(
            _flows_dir(), slug=cleaned_slug, flow_yaml=req.flow_yaml
        )
    except (FlowLoadError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/{slug:path}")
def delete_flow(slug: str) -> dict[str, str]:
    """删除服务端 flows/{slug}.yaml"""
    try:
        cleaned_slug = validate_flow_slug(slug)
        delete_flow_record(_flows_dir(), cleaned_slug)
        return {"status": "deleted", "slug": cleaned_slug}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
