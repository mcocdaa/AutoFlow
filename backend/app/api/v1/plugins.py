# @file /backend/app/api/v1/plugins.py
# @brief 插件与可用 Action/Check 列表及动态组件目录 Catalog API
# @create 2026-02-21 00:00:00
# @update 2026-08-22 吸收原 app/plugin/models.py,删除 shim 包
# @update 2026-10-14 增加动态组件目录 Catalog 元数据返回 (/api/v1/plugins & /api/v1/plugins/catalog)

from __future__ import annotations

from typing import Any, Literal

from app.core.registry import PluginInfo, PluginLoadErrorInfo, Registry
from app.runtime import get_registry
from fastapi import APIRouter
from pydantic import BaseModel, Field


class PluginItem(BaseModel):
    name: str
    version: str

    @classmethod
    def from_info(cls, info: PluginInfo) -> PluginItem:
        """从 registry.PluginInfo 构造"""
        return cls(name=info.name, version=info.version)


class PluginErrorItem(BaseModel):
    plugin_id: str
    file_path: str
    error: str

    @classmethod
    def from_info(cls, info: PluginLoadErrorInfo) -> PluginErrorItem:
        """从 registry.PluginLoadErrorInfo 构造"""
        return cls(
            plugin_id=info.plugin_id,
            file_path=info.file_path,
            error=info.error,
        )


class PluginCatalogItem(BaseModel):
    type: str
    label: str
    desc: str
    icon: str
    category: str
    kind: Literal["action", "check"]
    defaultParams: dict[str, Any] = Field(default_factory=dict)


class PluginsResponse(BaseModel):
    plugins: list[PluginItem]
    actions: list[str]
    checks: list[str]
    errors: list[PluginErrorItem]
    catalog: list[PluginCatalogItem] = Field(default_factory=list)


KNOWN_CATALOG_METADATA: dict[str, dict[str, Any]] = {
    # Actions - 基础与调试
    "core.log": {
        "label": "输出日志",
        "desc": "在执行日志中记录调试信息",
        "icon": "📝",
        "category": "core",
        "defaultParams": {"message": "Processing flow step..."},
    },
    "core.sleep": {
        "label": "延时等待",
        "desc": "暂停流程执行指定秒数",
        "icon": "⏱️",
        "category": "core",
        "defaultParams": {"seconds": 1},
    },
    "dummy.echo": {
        "label": "数据回显",
        "desc": "原样回显输入数据或构造结构化结果",
        "icon": "📦",
        "category": "dummy",
        "defaultParams": {"message": "hello"},
    },
    "openclaw.http_request": {
        "label": "HTTP 请求",
        "desc": "向外部 REST API 发起 GET/POST 请求",
        "icon": "🌐",
        "category": "core",
        "defaultParams": {"url": "https://api.example.com", "method": "GET"},
    },
    "openclaw.exec": {
        "label": "命令执行",
        "desc": "执行本地 Bash 脚本或系统指令",
        "icon": "💻",
        "category": "core",
        "defaultParams": {"command": 'echo "hello from shell"'},
    },
    # Actions - AI 与智能抓取
    "ai.deepseek_summarize": {
        "label": "DeepSeek 推理",
        "desc": "调用 DeepSeek/LLM 进行摘要、分析或提取",
        "icon": "🧠",
        "category": "ai",
        "defaultParams": {"input": "请精炼以下要点: {{input}}", "dry_run": True},
    },
    "zhihu.fetch_answer": {
        "label": "知乎回答采集",
        "desc": "拉取知乎指定问题回答正文内容",
        "icon": "📑",
        "category": "scraper",
        "defaultParams": {
            "url": "https://www.zhihu.com/question/784489052/answer/1946200783080125276",
            "dry_run": True,
        },
    },
    "zhihu.post_answer_draft": {
        "label": "知乎草稿投递",
        "desc": "将整理好的 Markdown 内容自动投递至知乎回答草稿",
        "icon": "✍️",
        "category": "scraper",
        "defaultParams": {
            "question_url": "https://www.zhihu.com/question/784489052",
            "content_md": "{{input}}",
            "dry_run": True,
        },
    },
    "openclaw.knowflow_record": {
        "label": "KnowFlow 归档",
        "desc": "将流程结果沉淀至 KnowFlow 知识库",
        "icon": "🕷️",
        "category": "scraper",
        "defaultParams": {"name": "digest_report", "project_id": "default"},
    },
    # Actions - 桌面自动化 (RPA)
    "desktop.activate_window": {
        "label": "激活桌面窗口",
        "desc": "按窗口标题查找并激活前置目标应用窗口",
        "icon": "🪟",
        "category": "desktop",
        "defaultParams": {"title": "App", "dry_run": True},
    },
    "desktop.click": {
        "label": "模拟鼠标点击",
        "desc": "控制桌面鼠标在指定坐标点击",
        "icon": "🖱️",
        "category": "desktop",
        "defaultParams": {"x": 500, "y": 300, "dry_run": True},
    },
    "desktop.double_click": {
        "label": "模拟鼠标双击",
        "desc": "控制桌面鼠标在指定坐标双击",
        "icon": "🖱️",
        "category": "desktop",
        "defaultParams": {"x": 500, "y": 300, "dry_run": True},
    },
    "desktop.drag": {
        "label": "鼠标拖拽移动",
        "desc": "从起始坐标按住拖拽至目标坐标",
        "icon": "↔️",
        "category": "desktop",
        "defaultParams": {
            "from_x": 100,
            "from_y": 100,
            "to_x": 400,
            "to_y": 400,
            "dry_run": True,
        },
    },
    "desktop.type_text": {
        "label": "键盘文本输入",
        "desc": "模拟键盘向当前焦点窗口输入字符串",
        "icon": "⌨️",
        "category": "desktop",
        "defaultParams": {"text": "hello", "dry_run": True},
    },
    "desktop.hotkey": {
        "label": "组合快捷键",
        "desc": "发送 Ctrl/Alt/Shift 等系统组合快捷键",
        "icon": "🎹",
        "category": "desktop",
        "defaultParams": {"keys": ["ctrl", "s"], "dry_run": True},
    },
    "desktop.wait": {
        "label": "桌面等待",
        "desc": "在桌面自动化步骤之间等待指定时长",
        "icon": "⏳",
        "category": "desktop",
        "defaultParams": {"seconds": 1, "dry_run": True},
    },
    "desktop.screenshot": {
        "label": "屏幕截屏",
        "desc": "截取当前桌面屏幕保存为产物",
        "icon": "📸",
        "category": "desktop",
        "defaultParams": {"name": "screenshot.png", "dry_run": True},
    },
    # Checks - 强断言校验
    "core.assert_truthy": {
        "label": "真值断言",
        "desc": "强校验 Action 输出必须为真",
        "icon": "✅",
        "category": "check",
        "defaultParams": {"value": True},
    },
    "core.assert_status": {
        "label": "状态码断言",
        "desc": "校验 HTTP 请求状态码为 200/201",
        "icon": "🎯",
        "category": "check",
        "defaultParams": {"expected_status": 200},
    },
    "core.assert_equals": {
        "label": "相等断言",
        "desc": "强校验输出或字段等于期望值",
        "icon": "⚖️",
        "category": "check",
        "defaultParams": {"actual": "{{input}}", "expected": "ok"},
    },
    "text.contains": {
        "label": "文本包含断言",
        "desc": "校验输出文本包含指定关键字",
        "icon": "🔍",
        "category": "check",
        "defaultParams": {"needle": "ok"},
    },
    "core.always_true": {
        "label": "恒真断言",
        "desc": "始终通过的占位校验断言",
        "icon": "🟢",
        "category": "check",
        "defaultParams": {},
    },
    "openclaw.status_code_ok": {
        "label": "HTTP 状态码校验",
        "desc": "校验 OpenClaw HTTP 响应状态码等于期望值",
        "icon": "🌐",
        "category": "check",
        "defaultParams": {"expected": 200},
    },
    "openclaw.exit_code_zero": {
        "label": "零退出码校验",
        "desc": "校验命令执行退出码 exit_code == 0",
        "icon": "💻",
        "category": "check",
        "defaultParams": {},
    },
    "desktop.image_exists": {
        "label": "屏幕图像匹配校验",
        "desc": "检测屏幕上是否存在指定模板图像",
        "icon": "🖼️",
        "category": "check",
        "defaultParams": {"template_path": "template.png", "timeout_seconds": 1},
    },
    "desktop.window_title_contains": {
        "label": "窗口标题包含校验",
        "desc": "校验当前活动窗口标题包含指定文本",
        "icon": "🪟",
        "category": "check",
        "defaultParams": {"needle": "App"},
    },
}


def _build_catalog_item(
    type_name: str, kind: Literal["action", "check"]
) -> PluginCatalogItem:
    meta = KNOWN_CATALOG_METADATA.get(type_name)
    if meta is not None:
        return PluginCatalogItem(
            type=type_name,
            label=str(meta["label"]),
            desc=str(meta["desc"]),
            icon=str(meta["icon"]),
            category="check" if kind == "check" else str(meta["category"]),
            kind=kind,
            defaultParams=dict(meta.get("defaultParams") or {}),
        )

    prefix = type_name.split(".")[0] if "." in type_name else "core"
    short_name = type_name.split(".")[-1].replace("_", " ").title()
    if kind == "check":
        category = "check"
        icon = "🛡️"
        desc = f"动态注册校验断言: {type_name}"
    else:
        category_map = {
            "core": "core",
            "dummy": "dummy",
            "openclaw": "core",
            "ai": "ai",
            "zhihu": "scraper",
            "desktop": "desktop",
        }
        category = category_map.get(prefix, "core")
        icon = "🔌"
        desc = f"动态注册动作插件: {type_name}"

    return PluginCatalogItem(
        type=type_name,
        label=short_name,
        desc=desc,
        icon=icon,
        category=category,
        kind=kind,
        defaultParams={},
    )


def build_plugins_response(registry: Registry) -> PluginsResponse:
    plugins = [PluginItem.from_info(p) for p in registry.list_plugins()]
    errors = [PluginErrorItem.from_info(e) for e in registry.list_plugin_errors()]
    actions = registry.list_actions()
    checks = registry.list_checks()
    catalog: list[PluginCatalogItem] = [
        *(_build_catalog_item(a, "action") for a in actions),
        *(_build_catalog_item(c, "check") for c in checks),
    ]
    return PluginsResponse(
        plugins=plugins,
        actions=actions,
        checks=checks,
        errors=errors,
        catalog=catalog,
    )


router = APIRouter()


@router.get("/plugins", response_model=PluginsResponse)
def list_plugins() -> PluginsResponse:
    return build_plugins_response(get_registry())


@router.get("/plugins/catalog", response_model=PluginsResponse)
def get_plugin_catalog() -> PluginsResponse:
    return build_plugins_response(get_registry())
