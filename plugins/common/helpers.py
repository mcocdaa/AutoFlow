# @file /plugins/common/helpers.py
# @brief 插件共享工具函数(从 desktop_checkin/zhihu_digest/ai_deepseek 去重而来)
# @create 2026-08-10

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.registry import ActionContext


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def is_truthy(v: Any) -> bool:
    """布尔化判定:None/False 为假;字符串按 {1,true,yes,y,on} 判定"""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def dry_run_enabled(ctx: ActionContext, params: dict[str, Any], env_var: str) -> bool:
    """统一 dry_run 判定:params.dry_run > ctx.vars.dry_run > 环境变量 env_var"""
    if is_truthy(params.get("dry_run")):
        return True
    if is_truthy(ctx.vars.get("dry_run")):
        return True
    return is_truthy(os.getenv(env_var))


def read_text(ctx: ActionContext, path: str, extra_roots: tuple[Path, ...] = ()) -> str:
    """安全路径读取(防穿越):仅允许 artifacts 目录、仓库根目录与 extra_roots 内"""
    p = Path(path)
    if not p.is_absolute():
        p = ctx.artifacts_dir / p
    p = p.resolve()
    allowed = {ctx.artifacts_dir.resolve(), _repo_root().resolve(), *extra_roots}
    if not any(p == base or base in p.parents for base in allowed):
        raise ValueError(f"path outside allowed directories: {path}")
    return p.read_text(encoding="utf-8")


def write_text(ctx: ActionContext, rel_path: str, text: str) -> str:
    """写入 artifacts 目录(自动创建父目录),返回相对路径"""
    out_path = ctx.artifacts_dir / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    return rel_path


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def safe_name(name: str, fallback: str) -> str:
    """文件名净化:取 basename 并将非法字符替换为下划线,空结果回退到 fallback"""
    n = Path(name).name
    n = re.sub(r"[^a-zA-Z0-9._-]+", "_", n)
    return n or fallback
