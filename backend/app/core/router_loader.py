# @file /app/core/router_loader.py
# @brief 自动路由加载器 - 非递归版 (分层负责)
# @create 2026-03-10
import importlib
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter


def include_routers_from_directory(
    parent_router: APIRouter,
    package_name: str,
    directory_path: Path,
    *,
    skip_modules: Optional[List[str]] = None,
    auto_tag: bool = False,
    auto_prefix: bool = False,
) -> None:
    """
    非递归：仅扫描当前目录下的文件和文件夹。
    遇到文件夹时，仅尝试导入该文件夹的 __init__.py 中的 router。
    """
    if skip_modules is None:
        skip_modules = []

    base_name = package_name.split(".")[-1]

    for path in directory_path.iterdir():
        # 1. 跳过自己
        if path.name == "__init__.py":
            continue

        module_name = None

        # 2. 识别模块 (文件 或 包目录)
        if path.is_file() and path.suffix == ".py":
            module_name = path.stem
        elif path.is_dir() and (path / "__init__.py").exists():
            module_name = path.name

        if not module_name or module_name in skip_modules:
            continue

        # 3. 动态导入
        try:
            module = importlib.import_module(f".{module_name}", package=package_name)

            # 4. 检查并挂载 router
            if hasattr(module, "router"):
                sub_router = getattr(module, "router")

                kwargs = {"prefix": f"/{base_name}"}
                if auto_tag:
                    kwargs["tags"] = [module_name]
                if auto_prefix:
                    kwargs["prefix"] += f"/{module_name}"

                parent_router.include_router(sub_router, **kwargs)
                print(
                    f"[RouterLoader] 已挂载: {package_name}.{module_name}, **{kwargs}"
                )

        except Exception as e:
            print(f"[RouterLoader] 挂载失败 {module_name}: {str(e)}")
