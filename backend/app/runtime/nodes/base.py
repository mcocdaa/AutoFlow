from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from app.runtime.dag_models import BaseNode, InputPort, OutputPort


class StartNode(BaseNode):
    """起始节点 - 工作流执行的起点"""

    def __init__(
        self,
        id: str,
        name: str = "Start",
        outputs: Optional[List[OutputPort]] = None,
        **kwargs,
    ):
        super().__init__(
            id=id, name=name, type="start", inputs=[], outputs=outputs or [], **kwargs
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行起始节点，将输入传递到输出端口"""
        outputs = {}
        for port in self.outputs:
            if port.id in inputs:
                outputs[port.id] = inputs[port.id]
            elif port.default is not None:
                outputs[port.id] = port.default
        return outputs


class EndNode(BaseNode):
    """结束节点 - 工作流执行的终点"""

    def __init__(
        self,
        id: str,
        name: str = "End",
        inputs: Optional[List[InputPort]] = None,
        **kwargs,
    ):
        super().__init__(
            id=id, name=name, type="end", inputs=inputs or [], outputs=[], **kwargs
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行结束节点，直接返回输入"""
        return inputs


class ActionNode(BaseNode):
    """动作节点 - 执行注册的动作处理器"""

    def __init__(
        self,
        id: str,
        name: str,
        action_type: str,
        inputs: Optional[List[InputPort]] = None,
        outputs: Optional[List[OutputPort]] = None,
        **kwargs,
    ):
        config = kwargs.get("config", {})
        config["action_type"] = action_type
        kwargs["config"] = config

        super().__init__(
            id=id,
            name=name,
            type="action",
            inputs=inputs or [],
            outputs=outputs or [],
            **kwargs,
        )

    @property
    def action_type(self) -> str:
        """获取动作类型"""
        return self.config.get("action_type", "")

    def execute(
        self,
        inputs: Dict[str, Any],
        action_handler: Optional[Callable] = None,
        **handler_kwargs,
    ) -> Dict[str, Any]:
        """执行动作节点，调用动作处理器"""
        if action_handler is None:
            return {}

        result = action_handler(inputs, **handler_kwargs)

        outputs = {}
        if len(self.outputs) == 1:
            outputs[self.outputs[0].id] = result
        elif isinstance(result, dict):
            for port in self.outputs:
                if port.id in result:
                    outputs[port.id] = result[port.id]

        return outputs


class PassNode(BaseNode):
    """传递节点 - 直接传递数据，可选数据转换"""

    def __init__(
        self,
        id: str,
        name: str = "Pass",
        inputs: Optional[List[InputPort]] = None,
        outputs: Optional[List[OutputPort]] = None,
        **kwargs,
    ):
        super().__init__(
            id=id,
            name=name,
            type="pass",
            inputs=inputs or [],
            outputs=outputs or [],
            **kwargs,
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行传递节点，根据配置转换数据"""
        transform = self.config.get("transform")

        if transform and callable(transform):
            return transform(inputs)

        outputs = {}
        for output_port in self.outputs:
            if output_port.id in inputs:
                outputs[output_port.id] = inputs[output_port.id]
            else:
                for input_port in self.inputs:
                    if input_port.id in inputs:
                        outputs[output_port.id] = inputs[input_port.id]
                        break

        return outputs
