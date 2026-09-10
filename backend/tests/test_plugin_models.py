# @file /backend/tests/test_plugin_models.py
# @brief PluginItem / PluginErrorItem from_info 工厂方法测试
# @create 2026-08-10
# @update 2026-08-22 模型内联至 api/v1/plugins.py,同步导入路径

from __future__ import annotations

from app.api.v1.plugins import PluginErrorItem, PluginItem
from app.core.registry import PluginInfo, PluginLoadErrorInfo


def test_plugin_item_from_info() -> None:
    item = PluginItem.from_info(PluginInfo(name="dummy", version="0.1.0"))
    assert item.name == "dummy"
    assert item.version == "0.1.0"


def test_plugin_error_item_from_info() -> None:
    info = PluginLoadErrorInfo(plugin_id="p1", file_path="/tmp/x.py", error="boom")
    item = PluginErrorItem.from_info(info)
    assert item.plugin_id == "p1"
    assert item.file_path == "/tmp/x.py"
    assert item.error == "boom"
