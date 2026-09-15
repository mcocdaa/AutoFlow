# @file /tools/test/feature-checks/run-checks.py
# @brief Flow 引擎功能 API 回归：逐个执行 docs/examples/engine/*.flow.yaml 并断言
# @create 2026-09-10
#
# 用法:
#   python3 run-checks.py [base_url]
#   AUTOFLOW_BASE_URL=http://localhost:3001 python3 run-checks.py
#
# 环境变量:
#   AUTOFLOW_BASE_URL     被测 API 地址（也可用第一个参数覆盖）
#   AUTOFLOW_HEALTH_URL   flow 11 内部请求的地址，默认与 base_url 相同
#                         （对容器场景可设为容器内地址，如 http://localhost:3000）
#   AUTOFLOW_MARKER_DIR   标记文件目录，flow 05/07/08 与脚本共用，默认 /tmp
#                         （对容器场景可挂载共享目录后指定）
#
# 前置条件: 后端已通过 scripts/start.sh 启动。
# 仅使用标准库,可在任意 Python 3.12+ 环境运行。

from __future__ import annotations

import hashlib
import http.client
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
FLOWS = REPO_ROOT / "docs" / "examples" / "engine"
BASE_URL = os.getenv("AUTOFLOW_BASE_URL", "http://localhost:3001")
HEALTH_URL = os.getenv("AUTOFLOW_HEALTH_URL", "")
MARKER_DIR = Path(os.getenv("AUTOFLOW_MARKER_DIR", "/tmp"))

RETRY_MARKER = MARKER_DIR / "autoflow_retry_marker"
HOOK_SUCCESS = MARKER_DIR / "autoflow_hook_success.txt"
HOOK_FAILURE = MARKER_DIR / "autoflow_hook_failure.txt"

results: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    results.append((name, bool(cond), str(detail)))


def request(method: str, path: str, payload: dict | None = None) -> tuple[int, bytes]:
    """返回 (status, raw_body);HTTP 错误也返回响应体而不抛出"""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def api_json(method: str, path: str, payload: dict | None = None) -> tuple[int, Any]:
    status, raw = request(method, path, payload)
    try:
        return status, json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return status, {}


def execute(flow_file: str, *, input=None, vars=None) -> dict:
    yaml_text = (FLOWS / flow_file).read_text(encoding="utf-8")
    status, run = api_json(
        "POST",
        "/api/v1/runs/execute",
        {"flow_yaml": yaml_text, "input": input, "vars": vars or {}},
    )
    if status != 200:
        raise RuntimeError(f"execute {flow_file} -> HTTP {status}: {run}")
    return run


def step(run: dict, sid: str) -> dict:
    return next(s for s in run["steps"] if s["step_id"] == sid)


def _run(name: str, fn) -> None:
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        check(f"{name} 执行异常", False, repr(e))


def check_basic_actions() -> None:
    run = execute("01_basic_actions.flow.yaml")
    check("01 run=success", run["status"] == "success", run["status"])
    check("01 core.log", step(run, "log")["action_output"]["message"] == "hello")
    check("01 core.sleep", step(run, "nap")["action_output"]["slept_seconds"] == 0.1)
    check("01 dummy.echo", step(run, "echo")["action_output"]["message"] == "chain-ok")


def check_templates() -> None:
    run = execute(
        "02_templates.flow.yaml", input={"name": "Ada"}, vars={"city": "Paris"}
    )
    check("02 run=success", run["status"] == "success", run["status"])
    check("02 input 全量替换", step(run, "greet")["action_output"]["message"] == "Ada")
    check(
        "02 vars 属性链",
        step(run, "report")["action_output"]["message"] == "Ada from Paris",
        step(run, "report")["action_output"]["message"],
    )
    check(
        "02 steps 属性链",
        step(run, "report2")["action_output"]["message"] == "step1 said Ada",
        step(run, "report2")["action_output"]["message"],
    )


def check_condition() -> None:
    run = execute("03_condition.flow.yaml", vars={"mode": "enabled"})
    statuses = {s["step_id"]: s["status"] for s in run["steps"]}
    check("03 run=success", run["status"] == "success", run["status"])
    check(
        "03 条件状态",
        statuses == {"always": "success", "skipped": "skipped", "var_cond": "success"},
        str(statuses),
    )


def check_foreach() -> None:
    run = execute("04_foreach.flow.yaml", input={"items": ["a", "b", "c"]})
    it = step(run, "loop")["iterations"]
    check("04 run=success", run["status"] == "success", run["status"])
    check("04 iterations=3", it is not None and len(it) == 3)
    check(
        "04 迭代输出",
        [x["output"]["message"] for x in it] == ["a", "b", "c"],
        str([x["output"]["message"] for x in it]),
    )


def check_retry() -> None:
    RETRY_MARKER.unlink(missing_ok=True)
    run = execute("05_retry.flow.yaml", vars={"marker_dir": str(MARKER_DIR)})
    out = step(run, "flaky")["action_output"]
    check("05 run=success(重试后)", run["status"] == "success", run["status"])
    check("05 第二次尝试成功", out["stdout"].strip() == "recovered", out["stdout"])
    check("05 exit_code=0", out["exit_code"] == 0)


def check_check_failure() -> None:
    run = execute("06_check_failure.flow.yaml")
    check("06 run=failed", run["status"] == "failed", run["status"])
    check("06 仅执行首个步骤", len(run["steps"]) == 1, str(len(run["steps"])))
    err = step(run, "logged")["error"] or ""
    check("06 错误含 check failed", "check failed: text.contains" in err, err)


def check_hooks_success() -> None:
    HOOK_SUCCESS.unlink(missing_ok=True)
    run = execute("07_hooks_success.flow.yaml", vars={"marker_dir": str(MARKER_DIR)})
    check("07 run=success", run["status"] == "success", run["status"])
    ok = HOOK_SUCCESS.exists() and HOOK_SUCCESS.read_text().strip() == "hook-success"
    check(
        "07 on_success 副作用",
        ok,
        HOOK_SUCCESS.read_text() if ok else "marker missing",
    )
    hooks = run.get("hook_results", [])
    check(
        "07 hook_results 记录",
        [h["action_type"] for h in hooks] == ["openclaw.exec", "core.log"]
        and all(h["hook"] == "on_success" and h["status"] == "success" for h in hooks),
        str([(h.get("action_type"), h.get("status")) for h in hooks]),
    )


def check_hooks_failure() -> None:
    HOOK_FAILURE.unlink(missing_ok=True)
    run = execute("08_hooks_failure.flow.yaml", vars={"marker_dir": str(MARKER_DIR)})
    check("08 run=failed", run["status"] == "failed", run["status"])
    ok = HOOK_FAILURE.exists() and HOOK_FAILURE.read_text().strip() == "hook-failure"
    check(
        "08 on_failure 副作用",
        ok,
        HOOK_FAILURE.read_text() if ok else "marker missing",
    )
    hooks = run.get("hook_results", [])
    check(
        "08 hook_results 记录",
        [h["action_type"] for h in hooks] == ["openclaw.exec", "core.log"]
        and all(h["hook"] == "on_failure" and h["status"] == "success" for h in hooks),
        str([(h.get("action_type"), h.get("status")) for h in hooks]),
    )


def check_large_output() -> None:
    run = execute("09_large_output.flow.yaml")
    out = step(run, "big")["action_output"]
    check("09 run=success", run["status"] == "success", run["status"])
    check("09 外置为 artifact 索引", isinstance(out, dict) and "__artifact__" in out)
    art = out.get("__artifact__", {})
    status, raw = request(
        "GET", f"/api/v1/runs/{run['run_id']}/artifacts/{art.get('path', '')}"
    )
    check("09 artifact 可下载", status == 200, str(status))
    check(
        "09 大小一致", len(raw) == art.get("size"), f"{len(raw)} vs {art.get('size')}"
    )
    check("09 sha256 一致", hashlib.sha256(raw).hexdigest() == art.get("sha256"))
    data = json.loads(raw)
    check("09 内容完整(70000 A)", data.get("stdout", "").count("A") == 70000)

    # Runs / Artifacts API
    status, runs = api_json("GET", "/api/v1/runs")
    ids = [x["run_id"] for x in runs] if isinstance(runs, list) else []
    check("09 GET /runs 含该 run", status == 200 and run["run_id"] in ids, str(status))
    status, _ = api_json("GET", f"/api/v1/runs/{run['run_id']}")
    check("09 GET /runs/{id}", status == 200, str(status))
    status, run_json = api_json(
        "GET", f"/api/v1/runs/{run['run_id']}/artifacts/run.json"
    )
    check(
        "09 run.json 可下载",
        status == 200 and run_json.get("flow_name") == run["flow_name"],
    )

    # 路径穿越防护（raw path，绕过客户端归一化）
    parsed = urllib.parse.urlparse(BASE_URL)
    conn = http.client.HTTPConnection(
        parsed.hostname or "localhost", parsed.port or 80, timeout=10
    )
    conn.request(
        "GET", f"/api/v1/runs/{run['run_id']}/artifacts/../../../../etc/passwd"
    )
    trav = conn.getresponse()
    check("09 路径穿越被拒绝", trav.status in (403, 404), str(trav.status))
    conn.close()

    # 删除
    status, _ = api_json("DELETE", f"/api/v1/runs/{run['run_id']}")
    check("09 DELETE=204", status == 204, str(status))
    status, _ = api_json("GET", f"/api/v1/runs/{run['run_id']}")
    check("09 删除后 GET=404", status == 404, str(status))


def check_plugins_dry_run() -> None:
    run = execute("10_plugins_dry_run.flow.yaml", vars={"dry_run": True})
    check("10 run=success", run["status"] == "success", run["status"])
    statuses = {s["step_id"]: s["status"] for s in run["steps"]}
    check(
        "10 六步全成功", all(v == "success" for v in statuses.values()), str(statuses)
    )
    check(
        "10 desktop.wait",
        step(run, "desktop_wait")["action_output"]
        == {"waited_seconds": 0.01, "dry_run": True},
    )
    t = step(run, "desktop_type")["action_output"]
    check(
        "10 desktop.type_text",
        t["typed"] is True and t["length"] == 3 and t["dry_run"] is True,
    )
    s = step(run, "desktop_shot")["action_output"]
    check("10 desktop.screenshot", s["saved"] is True and s["dry_run"] is True, str(s))
    d = step(run, "deepseek")["action_output"]
    check(
        "10 ai.deepseek_summarize",
        d["summary_path"].endswith(".md") and d["dry_run"] is True,
        str(d),
    )
    zf = step(run, "zhihu_fetch")["action_output"]
    check(
        "10 zhihu.fetch_answer",
        zf["answer_id"] == "456" and zf["dry_run"] is True,
        str(zf),
    )
    zp = step(run, "zhihu_post")["action_output"]
    check(
        "10 zhihu.post_answer_draft",
        zp["attempted"] is False and zp["dry_run"] is True,
        str(zp),
    )


def check_openclaw_local() -> None:
    run = execute("11_openclaw_local.flow.yaml", vars={"health_url": HEALTH_URL})
    check("11 run=success", run["status"] == "success", run["status"])
    h = step(run, "health")["action_output"]
    check(
        "11 http_request /health 200",
        h["status_code"] == 200 and h["body"] == {"status": "healthy"},
        str(h.get("body")),
    )
    e = step(run, "echo")["action_output"]
    check(
        "11 exec 输出",
        e["stdout"].strip() == "autoflow-openclaw-ok" and e["exit_code"] == 0,
        str(e),
    )
    k = step(run, "knowflow_missing")["action_output"]
    check(
        "11 knowflow 优雅报错",
        k.get("success") is False and k.get("error_type") == "network_error",
        str(k),
    )


DEBUG_FLOW = """
version: "1"
name: debug-session-check
steps:
  - id: first
    action:
      type: dummy.echo
      params:
        message: "step-one"
  - id: second
    action:
      type: dummy.echo
      params:
        message: "step-two"
"""


def check_debug_session() -> None:
    status, snap = api_json(
        "POST",
        "/api/v1/debug/sessions",
        {"flow_yaml": DEBUG_FLOW, "input": {}, "vars": {}},
    )
    check("13 创建会话", status == 200, str(status))
    sid = snap.get("session_id", "")
    check(
        "13 初始快照",
        snap.get("status") == "paused"
        and snap.get("index") == 0
        and snap.get("total_steps") == 2
        and snap.get("results") == [],
        str(snap)[:200],
    )

    status, snap = api_json("POST", f"/api/v1/debug/sessions/{sid}/step")
    check(
        "13 单步执行",
        status == 200
        and snap.get("index") == 1
        and [r["step_id"] for r in snap.get("results", [])] == ["first"],
        str(snap)[:200],
    )

    status, snap = api_json("POST", f"/api/v1/debug/sessions/{sid}/run")
    check(
        "13 运行到底",
        status == 200
        and snap.get("status") == "success"
        and snap.get("index") == 2
        and [r["step_id"] for r in snap.get("results", [])] == ["first", "second"],
        str(snap)[:200],
    )
    run_id = snap.get("run_id", "")
    check("13 调试运行进入历史", api_json("GET", f"/api/v1/runs/{run_id}")[0] == 200)

    status, got = api_json("GET", f"/api/v1/debug/sessions/{sid}")
    check(
        "13 快照可重取",
        status == 200 and got.get("status") == "success",
        str(status),
    )

    status, _ = api_json("DELETE", f"/api/v1/debug/sessions/{sid}")
    check("13 删除会话=204", status == 204, str(status))
    status, _ = api_json("GET", f"/api/v1/debug/sessions/{sid}")
    check("13 删除后 404", status == 404, str(status))
    check("13 已完成运行保留", api_json("GET", f"/api/v1/runs/{run_id}")[0] == 200)

    status, _ = api_json(
        "POST", "/api/v1/debug/sessions", {"flow_yaml": "- a\n- b", "vars": {}}
    )
    check("13 非法 flow=400", status == 400, str(status))


def check_replay() -> None:
    run = execute("01_basic_actions.flow.yaml")
    check("14 原始 run=success", run["status"] == "success", run["status"])

    status, replay = api_json("POST", f"/api/v1/runs/{run['run_id']}/replay")
    check("14 replay=200", status == 200, str(status))
    check(
        "14 生成新 run",
        replay.get("run_id") not in (None, run["run_id"]),
        str(replay.get("run_id")),
    )
    check(
        "14 回放结果一致",
        replay.get("status") == run["status"]
        and replay.get("flow_name") == run["flow_name"],
        f"{replay.get('status')} {replay.get('flow_name')}",
    )
    status, raw = request(
        "GET", f"/api/v1/runs/{replay['run_id']}/artifacts/request.json"
    )
    check("14 回放运行已存请求", status == 200 and b"flow_yaml" in raw, str(status))

    status, _ = api_json("POST", "/api/v1/runs/does-not-exist/replay")
    check("14 未知 run=404", status == 404, str(status))


def check_api_edges() -> None:
    status, body = api_json(
        "POST", "/api/v1/runs/execute", {"flow_yaml": "- a\n- b", "vars": {}}
    )
    check("12 非 mapping YAML=400", status == 400, str(status))

    status, body = api_json("POST", "/api/v1/runs/execute", {"vars": {}})
    check("12 缺 flow_yaml=422", status == 422, str(status))

    status, run = api_json(
        "POST",
        "/api/v1/runs/execute",
        {
            "flow_yaml": 'version: "1"\nname: bad-action\nsteps:\n'
            "  - id: s1\n    action:\n      type: not.exists\n",
            "vars": {},
        },
    )
    ok = status == 200 and run.get("status") == "failed"
    check("12 未知 action=run failed", ok, f"HTTP {status} status={run.get('status')}")

    status, body = api_json("GET", "/api/v1/runs/does-not-exist")
    check(
        "12 未知 run=404",
        status == 404 and body.get("detail") == "run not found",
        str(body),
    )


def main() -> int:
    global BASE_URL, HEALTH_URL
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    HEALTH_URL = HEALTH_URL or BASE_URL
    print(f"=== AutoFlow 引擎功能 API 回归 @ {BASE_URL} ===")

    try:
        request("GET", "/health")
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] 无法连接后端 {BASE_URL}/health: {e}")
        print("        请先执行 scripts/start.sh local backend")
        return 2

    _run("01", check_basic_actions)
    _run("02", check_templates)
    _run("03", check_condition)
    _run("04", check_foreach)
    _run("05", check_retry)
    _run("06", check_check_failure)
    _run("07", check_hooks_success)
    _run("08", check_hooks_failure)
    _run("09", check_large_output)
    _run("10", check_plugins_dry_run)
    _run("11", check_openclaw_local)
    _run("12", check_api_edges)
    _run("13", check_debug_session)
    _run("14", check_replay)

    print()
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        mark = "PASS" if ok else "FAIL"
        line = f"[{mark}] {name}"
        if not ok and detail:
            line += f"  <- {detail}"
        print(line)
    print()
    print(f"结果: {passed}/{len(results)} 通过")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
