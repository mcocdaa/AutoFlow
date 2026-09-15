# @file /backend/app/runtime/runner/runner.py
# @brief Flow 执行器门面(执行逻辑位于 app.runtime.session.RunSession)
# @create 2026-02-21 00:00:00
# @update 2026-03-15 拆分条件与模板解析到独立模块
# @update 2026-08-08 合并 for_each 与普通步骤双路径,修复 duration_ms / check_passed
# @update 2026-08-10 序列化函数收敛至 app.runtime.utils.serialization
# @update 2026-08-22 抽取 _invoke_action/_finalize_run,统一 hooks 与 step 调用及收尾
# @update 2026-09-15 执行逻辑下沉 RunSession,Runner 仅保留门面

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.registry import Registry
from app.runtime.models import FlowSpec, RunResult
from app.runtime.session import RunSession
from app.runtime.storage.store import RunStore


class Runner:
    """Flow 执行器门面:run_flow 等价于 RunSession 跑到底"""

    def __init__(self, registry: Registry, store: RunStore) -> None:
        self._registry = registry
        self._store = store

    @property
    def artifacts_dir(self) -> Path:
        return self._store.artifacts_dir

    def run_flow(
        self,
        flow: FlowSpec,
        *,
        input: Any = None,
        vars: dict[str, Any] | None = None,
        request: dict[str, Any] | None = None,
    ) -> RunResult:
        session = RunSession.start(
            self._registry,
            self._store,
            flow,
            input=input,
            vars=vars,
            request=request,
        )
        return session.run_to_completion()
