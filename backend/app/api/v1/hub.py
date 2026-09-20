# @file /backend/app/api/v1/hub.py
# @brief Flow 流程分发市场 (Flow Hub) 接口设计与内置精选模板
# @create 2026-09-20

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.setting_manager import setting_manager
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

CURATED_HUB_FLOWS = [
    {
        "id": "hub-sre-remediate",
        "name": "sre_auto_remediation",
        "title": "SRE 告警诊断与故障自愈闭环",
        "category": "SRE / 运维自愈",
        "author": "AutoFlow Team",
        "version": "1.0.0",
        "installs": 1280,
        "rating": 4.9,
        "description": "监控告警触发 ➔ 自动采集故障上下文日志 ➔ 执行修复 Action ➔ Check 确认自愈",
        "tags": ["sre", "devops", "self-healing", "monitoring"],
        "yaml": """version: "1"
name: sre_auto_remediation
description: "SRE 告警自愈: 诊断采集 -> 执行恢复 -> 验证 Check"
steps:
  - id: diagnose
    name: "收集系统负载与日志诊断"
    action:
      type: core.log
      params:
        message: "Diagnosing anomaly alert: {{input.alert_id}}"
  - id: execute_recovery
    name: "执行自愈脚本或容器重启"
    action:
      type: dummy.echo
      params:
        action_taken: "restarted service {{input.service_name}}"
    check:
      type: core.assert_truthy
      params:
        value: true
""",
    },
    {
        "id": "hub-zhihu-digest",
        "name": "zhihu_content_digest",
        "title": "知乎热榜采集与 LLM 智能研报",
        "category": "自动化数据采集",
        "author": "Community",
        "version": "1.2.0",
        "installs": 3450,
        "rating": 4.8,
        "description": "定时采集平台热门问答 ➔ DeepSeek/LLM 提炼关键观点 ➔ 微信/飞书多端分发",
        "tags": ["scraper", "zhihu", "ai-digest", "deepseek"],
        "yaml": """version: "1"
name: zhihu_content_digest
description: "定时采集知乎内容并生成 LLM 研报"
cron: "0 9 * * *"
steps:
  - id: fetch_hot
    name: "拉取知乎热榜"
    action:
      type: dummy.echo
      params:
        source: "zhihu_hot"
  - id: summarize
    name: "LLM 提炼精炼摘要"
    action:
      type: dummy.echo
      params:
        summary: "Daily digest generated successfully"
""",
    },
    {
        "id": "hub-agent-mcp-toolchain",
        "name": "agent_safe_pipeline",
        "title": "Agent 确定性校验工具链 (MCP 暴露)",
        "category": "Agent 工具链",
        "author": "Claude Code Contributor",
        "version": "1.0.1",
        "installs": 2100,
        "rating": 4.95,
        "description": "供 Claude Code / Cursor / Codex 等外部 Agent 通过单次 toolcall 调用的确定性多步流",
        "tags": ["mcp", "claude-code", "cursor", "codex", "safe-actions"],
        "yaml": """version: "1"
name: agent_safe_pipeline
description: "将易出错的多步骤外部调用封装为确定性带 Check 的复合 MCP 工具"
steps:
  - id: step_precheck
    name: "前置环境检查"
    action:
      type: core.log
      params:
        message: "Environment verified for task {{input.task}}"
  - id: step_apply
    name: "确定性操作执行"
    action:
      type: dummy.echo
      params:
        status: "applied"
    check:
      type: core.assert_truthy
      params:
        value: true
""",
    },
    {
        "id": "hub-desktop-rpa",
        "name": "desktop_rpa_sync",
        "title": "跨系统客户端与桌面 RPA 数据对齐",
        "category": "桌面 RPA",
        "author": "RPA Specialist",
        "version": "1.0.0",
        "installs": 980,
        "rating": 4.85,
        "description": "监控桌面客户端状态 ➔ 提取业务窗口数据 ➔ 执行格式校验 ➔ 自动对齐入库",
        "tags": ["rpa", "desktop", "sync", "automation"],
        "yaml": """version: "1"
name: desktop_rpa_sync
description: "跨系统桌面客户端数据捕获与自动对齐同步"
steps:
  - id: check_client
    name: "检查客户端运行状态"
    action:
      type: core.log
      params:
        message: "Verifying desktop client process status"
  - id: extract_and_align
    name: "数据捕获与校验对齐"
    action:
      type: dummy.echo
      params:
        result: "Extracted 120 records and verified integrity"
    check:
      type: core.assert_truthy
      params:
        value: true
""",
    },
]


class HubFlowSummary(BaseModel):
    id: str
    name: str
    title: str
    category: str
    author: str
    version: str
    installs: int
    rating: float
    description: str
    tags: list[str]


class HubFlowDetail(HubFlowSummary):
    yaml: str


class InstallHubFlowRequest(BaseModel):
    flow_id: str
    overwrite: bool = False


@router.get("/hub/flows", response_model=list[HubFlowSummary])
def list_hub_flows(
    category: str | None = None, query: str | None = None
) -> list[dict[str, Any]]:
    """浏览 Flow Hub 流程市场"""
    flows = CURATED_HUB_FLOWS
    if category:
        flows = [f for f in flows if f["category"] == category]
    if query:
        q = query.lower()
        flows = [
            f
            for f in flows
            if q in f["name"].lower()
            or q in f["title"].lower()
            or q in f["description"].lower()
            or any(q in t for t in f["tags"])
        ]
    return flows


@router.get("/hub/flows/{flow_id}", response_model=HubFlowDetail)
def get_hub_flow(flow_id: str) -> dict[str, Any]:
    """查看 Hub 流程详情与 YAML 源码"""
    for f in CURATED_HUB_FLOWS:
        if f["id"] == flow_id or f["name"] == flow_id:
            return f
    raise HTTPException(status_code=404, detail="Hub flow template not found")


@router.post("/hub/install", status_code=200)
def install_hub_flow(req: InstallHubFlowRequest) -> dict[str, Any]:
    """一键将 Hub 流程模板下载安装到本地 flows/ 目录"""
    flow_template = None
    for f in CURATED_HUB_FLOWS:
        if f["id"] == req.flow_id or f["name"] == req.flow_id:
            flow_template = f
            break

    if not flow_template:
        raise HTTPException(status_code=404, detail="Hub flow template not found")

    flows_dir = Path(setting_manager.FLOWS_DIR)
    flows_dir.mkdir(parents=True, exist_ok=True)
    target_file = flows_dir / f"{flow_template['name']}.flow.yaml"

    if target_file.exists() and not req.overwrite:
        raise HTTPException(
            status_code=409,
            detail=f"Flow file '{target_file.name}' already exists. Set overwrite=true to replace.",
        )

    target_file.write_text(flow_template["yaml"], encoding="utf-8")
    return {
        "status": "installed",
        "flow_name": flow_template["name"],
        "path": str(target_file),
    }
