from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.runtime.dag_models import BaseNode, InputPort, OutputPort


class IfNode(BaseNode):
    """条件节点 - 根据条件选择输出路径"""

    def __init__(
        self,
        id: str,
        name: str = "If",
        outputs: Optional[list[OutputPort]] = None,
        **kwargs,
    ):
        input_port = InputPort(
            id="input",
            name="Input",
            type="any",
            required=True,
        )

        super().__init__(
            id=id,
            name=name,
            type="if",
            inputs=[input_port],
            outputs=outputs or [],
            **kwargs,
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行条件节点，根据条件表达式选择输出"""
        input_data = inputs.get("input")
        outputs = {}

        default_port = None

        for port in self.outputs:
            if not port.condition:
                default_port = port
                continue

            try:
                if eval(port.condition, {}, {"input": input_data}):
                    outputs[port.id] = input_data
                    return outputs
            except Exception as e:
                raise ValueError(
                    f"Condition evaluation failed for port {port.id}: {str(e)}"
                )

        if default_port:
            outputs[default_port.id] = input_data

        return outputs


class SwitchNode(BaseNode):
    """开关节点 - 根据值匹配选择输出路径"""

    def __init__(
        self,
        id: str,
        name: str = "Switch",
        outputs: Optional[list[OutputPort]] = None,
        **kwargs,
    ):
        input_port = InputPort(
            id="input",
            name="Input",
            type="any",
            required=True,
        )

        super().__init__(
            id=id,
            name=name,
            type="switch",
            inputs=[input_port],
            outputs=outputs or [],
            **kwargs,
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行开关节点，根据值匹配选择输出"""
        input_data = inputs.get("input")
        outputs = {}

        default_port = None

        for port in self.outputs:
            if port.case is None:
                default_port = port
                continue

            if input_data == port.case:
                outputs[port.id] = input_data
                return outputs

        if default_port:
            outputs[default_port.id] = input_data

        return outputs


class ForNode(BaseNode):
    """循环节点 - 遍历列表执行"""

    def __init__(
        self,
        id: str,
        name: str = "For",
        **kwargs,
    ):
        input_port = InputPort(
            id="items",
            name="Items",
            type="array",
            required=True,
        )

        output_port = OutputPort(
            id="results",
            name="Results",
            type="array",
        )

        super().__init__(
            id=id,
            name=name,
            type="for",
            inputs=[input_port],
            outputs=[output_port],
            **kwargs,
        )

    def execute(
        self,
        inputs: Dict[str, Any],
        item_handler: Optional[Callable] = None,
        **handler_kwargs,
    ) -> Dict[str, Any]:
        """执行循环节点，遍历列表并处理每个元素"""
        items = inputs.get("items", [])
        results = []

        if not isinstance(items, list):
            raise ValueError("Input must be a list")

        if item_handler:
            for item in items:
                result = item_handler(item, **handler_kwargs)
                results.append(result)
        else:
            results = items

        return {"results": results}


class WhileNode(BaseNode):
    """While循环节点 - 条件满足时持续执行"""

    def __init__(
        self,
        id: str,
        name: str = "While",
        **kwargs,
    ):
        initial_port = InputPort(
            id="initial",
            name="Initial",
            type="any",
            required=True,
        )

        condition_port = InputPort(
            id="condition",
            name="Condition",
            type="any",
            required=True,
        )

        output_port = OutputPort(
            id="result",
            name="Result",
            type="any",
        )

        super().__init__(
            id=id,
            name=name,
            type="while",
            inputs=[initial_port, condition_port],
            outputs=[output_port],
            **kwargs,
        )

    def execute(
        self,
        inputs: Dict[str, Any],
        loop_handler: Optional[Callable] = None,
        max_iterations: int = 1000,
        **handler_kwargs,
    ) -> Dict[str, Any]:
        """执行While循环节点，条件满足时持续执行"""
        current = inputs.get("initial")
        condition_expr = inputs.get("condition")
        iteration = 0

        while iteration < max_iterations:
            try:
                if not eval(str(condition_expr), {}, {"current": current}):
                    break
            except Exception as e:
                raise ValueError(f"Condition evaluation failed: {str(e)}")

            if loop_handler:
                current = loop_handler(current, **handler_kwargs)

            iteration += 1

        return {"result": current}


class RetryNode(BaseNode):
    """重试节点 - 失败时自动重试"""

    def __init__(
        self,
        id: str,
        name: str = "Retry",
        **kwargs,
    ):
        config = kwargs.get("config", {})
        if "attempts" not in config:
            config["attempts"] = 0
        if "backoff_seconds" not in config:
            config["backoff_seconds"] = 0.0
        kwargs["config"] = config

        input_port = InputPort(
            id="input",
            name="Input",
            type="any",
            required=True,
        )

        output_port = OutputPort(
            id="output",
            name="Output",
            type="any",
        )

        super().__init__(
            id=id,
            name=name,
            type="retry",
            inputs=[input_port],
            outputs=[output_port],
            **kwargs,
        )

    @property
    def attempts(self) -> int:
        """获取最大重试次数"""
        return self.config.get("attempts", 0)

    @property
    def backoff_seconds(self) -> float:
        """获取退避时间（秒）"""
        return self.config.get("backoff_seconds", 0.0)

    def execute(
        self,
        inputs: Dict[str, Any],
        action_handler: Optional[Callable] = None,
        sleep_func: Optional[Callable] = None,
        **handler_kwargs,
    ) -> Dict[str, Any]:
        """执行重试节点，失败时自动重试"""
        input_data = inputs.get("input")
        max_attempts = self.attempts + 1
        last_error = None

        for attempt in range(max_attempts):
            try:
                if action_handler:
                    result = action_handler(input_data, **handler_kwargs)
                    return {"output": result}
                else:
                    return {"output": input_data}
            except Exception as e:
                last_error = e
                if attempt == max_attempts - 1:
                    raise
                if self.backoff_seconds > 0 and sleep_func:
                    wait_time = self.backoff_seconds * (2**attempt)
                    sleep_func(wait_time)

        if last_error:
            raise last_error

        return {"output": input_data}
