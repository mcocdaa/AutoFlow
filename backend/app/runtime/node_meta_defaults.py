"""内置节点元数据默认值 - 所有内置节点的端口/展示信息的唯一来源

此文件的定义与 executor.py 和 nodes/*.py 的实际执行逻辑保持一致。
前端通过 GET /v2/nodes 拉取这些数据，不再需要 node-defaults.ts / node-templates.ts 硬编码。
"""

from __future__ import annotations

from app.core.node_registry import NodeMeta, NodeRegistry, PortMeta

_ERR = PortMeta(id="error", name="Error", type="any")


def register_default_nodes(registry: NodeRegistry) -> None:
    """注册所有内置节点的元数据。在应用启动时调用，插件钩子之前执行。"""

    # ─── Core ────────────────────────────────────────────────────────────────

    registry.register(NodeMeta(
        type="start",
        label="开始",
        category="core",
        icon="▶",
        color="#10B981",
        inputs=[],  # StartNode 无输入端口
        outputs=[PortMeta(id="output", name="Output", type="any")],
        error_port=None,
        config_schema={},
    ))

    registry.register(NodeMeta(
        type="end",
        label="结束",
        category="core",
        icon="⏹",
        color="#6366F1",
        inputs=[PortMeta(id="input", name="Input", type="any", required=True)],
        outputs=[],
        error_port=None,
        config_schema={},
    ))

    registry.register(NodeMeta(
        type="pass",
        label="传递",
        category="core",
        icon="→",
        color="#94A3B8",
        inputs=[PortMeta(id="input", name="Input", type="any", required=True)],
        outputs=[PortMeta(id="output", name="Output", type="any")],
        error_port=None,
        config_schema={},
    ))

    registry.register(NodeMeta(
        type="action",
        label="动作",
        category="action",
        icon="⚡",
        color="#3B82F6",
        inputs=[PortMeta(id="input", name="Input", type="any", required=True)],
        outputs=[PortMeta(id="output", name="Output", type="any")],
        error_port=_ERR,
        config_schema={
            "type": "object",
            "properties": {
                "action_type": {
                    "type": "string",
                    "title": "动作类型",
                    "description": "后端注册的 action 类型标识符",
                },
            },
            "required": ["action_type"],
        },
    ))

    # ─── IO ──────────────────────────────────────────────────────────────────

    registry.register(NodeMeta(
        type="input",
        label="输入",
        category="io",
        icon="⌨",
        color="#F59E0B",
        inputs=[],  # InputNode 无输入端口，等待外部注入
        outputs=[PortMeta(id="output", name="Output", type="any")],
        error_port=None,
        config_schema={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "title": "输入模式",
                    "enum": ["api", "webhook", "form", "watch"],
                    "default": "api",
                },
                "timeout_seconds": {
                    "type": "number",
                    "title": "超时（秒）",
                    "default": 300,
                },
            },
        },
    ))

    # ─── Control ─────────────────────────────────────────────────────────────

    registry.register(NodeMeta(
        type="if",
        label="条件判断",
        category="control",
        icon="⑂",
        color="#F59E0B",
        inputs=[PortMeta(id="input", name="Input", type="any", required=True)],
        outputs=[
            PortMeta(id="true", name="True", type="any"),
            PortMeta(id="false", name="False", type="any"),
        ],
        error_port=_ERR,
        config_schema={
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "title": "条件表达式",
                    "description": "Python 表达式，使用 input 变量，结果为 True 走 true 端口",
                },
            },
        },
    ))

    registry.register(NodeMeta(
        type="switch",
        label="分支",
        category="control",
        icon="⊕",
        color="#8B5CF6",
        inputs=[PortMeta(id="input", name="Input", type="any", required=True)],
        outputs=[PortMeta(id="default", name="Default", type="any")],
        error_port=_ERR,
        config_schema={},
    ))

    registry.register(NodeMeta(
        type="for",
        label="循环",
        category="control",
        icon="↻",
        color="#06B6D4",
        inputs=[PortMeta(id="items", name="Items", type="array", required=True)],
        outputs=[PortMeta(id="results", name="Results", type="array")],
        error_port=_ERR,
        config_schema={},
    ))

    registry.register(NodeMeta(
        type="while",
        label="While 循环",
        category="control",
        icon="⟳",
        color="#06B6D4",
        inputs=[
            PortMeta(id="initial", name="Initial", type="any", required=True),
            PortMeta(id="condition", name="Condition", type="any", required=True),
        ],
        outputs=[PortMeta(id="result", name="Result", type="any")],
        error_port=_ERR,
        config_schema={},
    ))

    registry.register(NodeMeta(
        type="retry",
        label="重试",
        category="control",
        icon="↺",
        color="#F97316",
        inputs=[PortMeta(id="input", name="Input", type="any", required=True)],
        outputs=[PortMeta(id="output", name="Output", type="any")],
        error_port=_ERR,
        config_schema={
            "type": "object",
            "properties": {
                "attempts": {
                    "type": "number",
                    "title": "最大重试次数",
                    "default": 3,
                },
                "backoff_seconds": {
                    "type": "number",
                    "title": "退避时间（秒）",
                    "default": 1.0,
                },
            },
        },
    ))

    # ─── Data ────────────────────────────────────────────────────────────────

    registry.register(NodeMeta(
        type="merge",
        label="合并",
        category="data",
        icon="⇒",
        color="#10B981",
        inputs=[
            PortMeta(id="input1", name="Input 1", type="any", required=True),
            PortMeta(id="input2", name="Input 2", type="any"),
        ],
        outputs=[PortMeta(id="output", name="Output", type="any")],
        error_port=_ERR,
        config_schema={
            "type": "object",
            "properties": {
                "strategy": {
                    "type": "string",
                    "title": "合并策略",
                    "enum": ["list_concat", "object_merge", "custom"],
                    "default": "list_concat",
                },
            },
        },
    ))

    registry.register(NodeMeta(
        type="split",
        label="拆分",
        category="data",
        icon="⇐",
        color="#10B981",
        inputs=[PortMeta(id="input", name="Input", type="any", required=True)],
        outputs=[
            PortMeta(id="output1", name="Output 1", type="any"),
            PortMeta(id="output2", name="Output 2", type="any"),
        ],
        error_port=_ERR,
        config_schema={
            "type": "object",
            "properties": {
                "strategy": {
                    "type": "string",
                    "title": "拆分策略",
                    "enum": ["by_index", "by_field", "custom"],
                    "default": "by_index",
                },
            },
        },
    ))

    # ─── Composite ───────────────────────────────────────────────────────────

    registry.register(NodeMeta(
        type="group",
        label="分组",
        category="composite",
        icon="▣",
        color="#64748B",
        inputs=[],
        outputs=[],
        error_port=_ERR,
        config_schema={},
    ))

    registry.register(NodeMeta(
        type="subflow",
        label="子流程",
        category="composite",
        icon="⧉",
        color="#64748B",
        inputs=[],
        outputs=[],
        error_port=_ERR,
        config_schema={
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "title": "子工作流 ID",
                },
            },
        },
    ))
