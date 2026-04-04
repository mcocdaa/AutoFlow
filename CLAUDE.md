# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Starting Services

**Backend and frontend must only be started via `scripts/start.sh`** — never run uvicorn or npm dev directly.

```bash
# First-time setup
cp .env.example .env
./scripts/init-secrets.sh

# Local development (Python + npm dev server)
./scripts/start.sh local full      # backend:3001  frontend:5181
./scripts/start.sh local backend
./scripts/start.sh local frontend

# Docker development
./scripts/start.sh dev full        # backend:3001  frontend:8001
./scripts/start.sh dev backend

# Stop
./scripts/stop.sh dev
```

## Architecture Overview

AutoFlow is a **visual DAG workflow automation platform** with three main components:

### Backend (`/backend`) — FastAPI + Python

- **`app/main.py`**: FastAPI app entry; initializes plugin manager, hook manager, database
- **`app/runtime/`**: DAG execution engine
  - `dag_models.py`: Core data structures (nodes, edges, ports, workflow graph)
  - `workflow_runner.py`: Orchestrates the scheduler + executor; defines `WaitingForInputError`
  - `scheduler.py`: Topological sort to determine node execution order
  - `executor.py`: Executes individual nodes — handles `start`, `end`, `pass`, `action`, `input`, `if`, `switch`, `for`, `while`, `merge`, `split`, `retry`
  - `data_router.py`: Passes outputs from one node's ports to the next node's inputs
  - `execution_state.py`: Runtime state (`ExecutionState`); tracks `available_inputs`, `waiting_node_id`
  - `models.py`: `RunStatus` enum — `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `PAUSED`
  - `nodes/`: Node implementations
    - `base.py`: `StartNode`, `EndNode`, `ActionNode`, `PassNode`
    - `control.py`: `IfNode`, `SwitchNode`, `ForNode`, `WhileNode`, `RetryNode`
    - `data.py`: `MergeNode`, `SplitNode`
    - `composite.py`: `GroupNode`, `SubflowNode`
    - `input.py`: `InputNode` — suspends execution, waits for external data injection
  - `store/run_store.py`: Persist and load run state (supports pause/resume across requests)
- **`app/core/`**: Managers for plugins, hooks, database, settings, and action registry
- **`app/api/v2/`**: REST routes (auto-loaded)
  - `POST /v2/workflows/{workflow_id}/runs` — trigger a run
  - `POST /v2/runs/{run_id}/nodes/{node_id}/input` — inject data into a paused InputNode
  - `POST /v2/runs/{run_id}/cancel|pause|resume`
  - `GET  /v2/runs/{run_id}`
  - `GET  /v2/workflows/{workflow_id}/runs`

### Frontend (`/frontend`) — Vue 3 + TypeScript + Electron

- DAG editor built with `@vue-flow/core` (drag-and-drop node canvas)
- Pinia stores: `dag-workflow.ts` (nodes/edges/undo), `execution.ts` (live logs/status), `workflow.ts`, `plugins.ts`, `runs.ts`
- Ships as an Electron desktop app
- **Key components** (`src/components/workflow/`):
  - `Toolbar.vue`: Top bar with "文件▼" (导入示例/导出YAML) and "保存▼" (保存/保存为示例) dropdowns, view switcher (可视化/YAML/分屏), execution controls
  - `NodeConfigPanel.vue`: Right-side Drawer; includes InputNode-specific config (mode, timeout)
  - `NodePalette.vue`: Left sidebar node library; categories include `io` (InputNode)
  - `nodes/GenericNode.vue`: Renders all node types; ports show hover labels
  - `WorkflowYamlEditor.vue`: CodeMirror 6 editor with custom dark theme (YAML keys → gold `#e5c07b`)
  - `ExampleSelectorModal.vue`: Dark-themed example picker
- **Key utilities** (`src/utils/`, `src/constants/`):
  - `node-defaults.ts`: `getDefaultPorts(type)` — canonical port definitions per node type
  - `node-templates.ts`: Visual metadata (icon, color, category) for all node types including `input`
  - `types/workflow.ts`: `NodeType` union (includes `"input"`), `NodeCategory` union (includes `"io"`)

### Plugins (`/plugins`)
Registered in `plugins/plugins.yaml`. Each plugin:
1. Implements hooks (e.g., `on_plugin_manager_init`) to register actions into the action registry
2. Actions are then callable by workflow nodes at execution time

## Key Architectural Patterns

### API Auto-Loading
New route modules placed in `app/api/v1/` or `app/api/v2/` are auto-discovered by `core/router_loader.py`. Each module exports `router = APIRouter()`. All routes are prefixed with `/api`.

### Plugin Hook System
Plugins register via `hook_manager`. Core lifecycle hooks: `plugin_manager_init_before/after` and `registry_register`. Plugins must not modify core code — extend via hooks only.

### DAG Execution Flow
```
POST /v2/workflows/{id}/runs
  → WorkflowRunner.run()
  → DAGScheduler (topological sort)
  → for each ready node: NodeExecutor._execute_node_logic()
      → action handler (from plugin/action registry)
      → InputNode raises WaitingForInputError → run serialized to DB as PAUSED
  → DataRouter distributes outputs to downstream node inputs
  → artifacts stored in /app/artifacts/{run_id}/

POST /v2/runs/{run_id}/nodes/{node_id}/input
  → load saved ExecutionState from DB
  → inject data into state.available_inputs["{node_id}.__ext__"]
  → WorkflowRunner.resume() → continue from paused node
```

### InputNode Suspend/Resume
- `InputNode.execute()` checks `inputs["__ext__"]`; if `None`, raises `WaitingForInputError(node_id)`
- `WorkflowRunner` catches this: saves `execution_state` to DB, sets `run.status = PAUSED`, records `waiting_node_id`
- Resume: load state, inject data, re-run scheduler from the waiting node

### Frontend Node Port Conventions
- `getDefaultPorts(type)` in `node-defaults.ts` defines the canonical port spec for each node type
- `InputNode`: zero input ports, one output port (`id: "output"`); no error port
- `StartNode`: zero inputs, one output; `EndNode`: one input, zero outputs
- Control nodes (`if`, `switch`): multiple named output ports; first port without `condition` is the default/false branch

### Infrastructure
- **MySQL 8.0**: workflow definitions and run history
- **Redis 7.0**: caching and task queues
- Docker Compose for dev, Docker Swarm for prod (see `docker/`)
- Secrets managed via `secrets/` files (generated by `init-secrets.sh`)

## Code Standards (`docs/rules/`)

- Use `logging` (via loguru), never `print`
- All public methods require type annotations and Google-style docstrings
- Use `Enum` for status/type values, named constants for magic numbers
- Catch specific exceptions, not bare `Exception`
- Keep files under 500 lines; split at 400+
- Import order: stdlib → third-party → local (enforced by isort with `profile = "black"`)
- Frontend: no `console.log` in production code; use `as const` for string literals used as typed unions
