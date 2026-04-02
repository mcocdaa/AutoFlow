from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.runtime.dag_models import BaseNode, InputPort, OutputPort


class MergeNode(BaseNode):
    """合并节点 - 将多个输入合并为一个输出"""

    def __init__(
        self,
        id: str,
        name: str = "Merge",
        inputs: Optional[List[InputPort]] = None,
        **kwargs,
    ):
        kwargs.pop("type", None)
        kwargs.pop("outputs", None)
        config = kwargs.get("config", {})
        if "strategy" not in config:
            config["strategy"] = "list_concat"
        kwargs["config"] = config

        output_port = OutputPort(
            id="output",
            name="Output",
            type="any",
        )

        super().__init__(
            id=id,
            name=name,
            type="merge",
            inputs=inputs or [],
            outputs=[output_port],
            **kwargs,
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行合并节点，根据策略合并输入"""
        strategy = self.config.get("strategy", "list_concat")
        custom_strategy = self.config.get("custom_strategy")

        result = None

        if strategy == "list_concat":
            result = []
            for port_id, value in inputs.items():
                if isinstance(value, list):
                    result.extend(value)
                else:
                    result.append(value)
        elif strategy == "object_merge":
            result = {}
            for port_id, value in inputs.items():
                if isinstance(value, dict):
                    result.update(value)
        elif strategy == "custom" and custom_strategy:
            try:
                result = eval(custom_strategy, {}, {"inputs": inputs})
            except Exception as e:
                raise ValueError(f"Custom merge strategy failed: {str(e)}")

        return {"output": result}


class SplitNode(BaseNode):
    """拆分节点 - 将一个输入拆分为多个输出"""

    def __init__(
        self,
        id: str,
        name: str = "Split",
        outputs: Optional[List[OutputPort]] = None,
        **kwargs,
    ):
        kwargs.pop("type", None)
        kwargs.pop("inputs", None)
        config = kwargs.get("config", {})
        if "strategy" not in config:
            config["strategy"] = "by_index"
        kwargs["config"] = config

        input_port = InputPort(
            id="input",
            name="Input",
            type="any",
            required=True,
        )

        super().__init__(
            id=id,
            name=name,
            type="split",
            inputs=[input_port],
            outputs=outputs or [],
            **kwargs,
        )

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行拆分节点，根据策略拆分输入"""
        strategy = self.config.get("strategy", "by_index")
        custom_strategy = self.config.get("custom_strategy")
        input_data = inputs.get("input")

        outputs = {}

        if strategy == "by_index":
            if isinstance(input_data, list):
                for port in self.outputs:
                    index = port.index
                    if isinstance(index, int) and 0 <= index < len(input_data):
                        outputs[port.id] = input_data[index]
        elif strategy == "by_field":
            if isinstance(input_data, dict):
                for port in self.outputs:
                    field = port.field
                    if field and field in input_data:
                        outputs[port.id] = input_data[field]
        elif strategy == "custom" and custom_strategy:
            try:
                result = eval(custom_strategy, {}, {"input": input_data})
                if isinstance(result, dict):
                    outputs = result
            except Exception as e:
                raise ValueError(f"Custom split strategy failed: {str(e)}")

        return outputs
