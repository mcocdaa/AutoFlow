from __future__ import annotations

from typing import Any, Dict

from app.runtime.dag_models import BaseNode, OutputPort, RetrySpec


class InputNode(BaseNode):
    """输入节点 - 暂停工作流并等待外部数据注入"""

    def __init__(
        self,
        id: str,
        name: str = "Input",
        **kwargs,
    ) -> None:
        kwargs.pop("type", None)
        kwargs.pop("inputs", None)
        kwargs.pop("outputs", None)
        kwargs.setdefault("retry", RetrySpec(attempts=0, backoff_seconds=0.0))
        kwargs.setdefault("config", {})
        kwargs.setdefault("metadata", {})
        super().__init__(
            id=id,
            name=name,
            type="input",
            inputs=[],
            outputs=[OutputPort(id="output", name="Output", type="any")],
            **kwargs,
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行输入节点：将注入的外部数据传递到 output 端口"""
        return {"output": inputs.get("__ext__")}
