# AutoFlow - AI Coding Agent Instructions

## Project Overview

**AutoFlow** is a multi-platform RPA (Robotic Process Automation) framework enabling cross-platform automation through visual recording and orchestration. It supports desktop (Windows/macOS) and mobile (Android/iOS) with WYSIWYG editing.

**Architecture**: Monorepo with layered design: **Backend (FastAPI/Python) + Desktop Client (Electron/Vue3) + Mobile (UniApp) + Plugin System**

---

## Core Architecture

### Service Boundaries

1. **Backend (`backend/`)** - Python FastAPI
   - Core execution engine with multi-mode support (foreground/background execution)
   - Task lifecycle management (CRUD, scheduling, state transitions)
   - Logging/telemetry (InfluxDB) and result handling
   - Device adapters for cross-platform execution (Windows/macOS/Android/iOS)
   - Plugin system integration

2. **Desktop Frontend (`frontend/`)** - Electron + Vue3 + TypeScript
   - Main UI for task creation, visual editing, and monitoring
   - Vue3 with Element Plus (UI components)
   - Pinia for state management
   - Communicates with backend via REST API (default: `http://localhost:8000`)

3. **Mobile (`mobile/`)** - UniApp (Vue-based)
   - Mobile automation client
   - Shares execution logic with desktop via backend APIs

4. **Plugins (`plugins/`)** - Extensible Python modules
   - Action plugins (OCR, PDF, custom logic)
   - Device plugins (new platform support)
   - Function plugins (third-party integrations)

### Data Flow

```
User Records Action (Desktop/Mobile) → Visual Editor (Frontend)
    ↓
Task Definition + Execution Flow (Backend)
    ↓
Execution Engine (Multi-endpoint support)
    ↓
Device Adapters (Platform-specific: mouse/keyboard/touch)
    ↓
Result Validation + Logging (InfluxDB/SQLite)
    ↓
Notification + Audit (Enterprise Webhooks)
```

### Key Design Decisions

- **Multi-mode Execution**: Foreground mode (user-visible, exclusive) vs. Background mode (headless, non-intrusive) configured per task
- **Unified Execution Interface**: `execute(task_id, params)` abstracts multi-platform complexity
- **Sandbox Isolation**: Each task runs in isolated sandbox; failures don't cascade
- **Event-driven Architecture**: State transitions trigger notifications/logs via central event bus

---

## Development Workflow

### Local Setup

```bash
# Start dependencies (Docker required)
docker-compose up -d  # MySQL, Redis, InfluxDB, MinIO

# Backend
cd backend && pip install -e . && uvicorn app.main:app --reload
# Runs on http://localhost:8000 with auto-reload

# Frontend
cd frontend && npm install && npm run dev
# Launches Vite dev server + Electron app

# Testing
cd backend && pytest  # Uses pytest-asyncio for async tests
```

### Key Commands

- **Backend tests**: `pytest tests/` (handles async with `pytest-asyncio`)
- **Type checking**: `mypy app/` (strict mode enabled in `pyproject.toml`)
- **Code formatting**: `black app/` + `isort app/`
- **Build desktop**: `npm run build` (produces Electron packaged app via electron-builder)

### Configuration

- Backend: `.env` file (see `.env.example`), loaded via Pydantic Settings in [backend/app/core/config.py](backend/app/core/config.py)
- Database: MySQL (default: localhost:3306, user: autoflow)
- Redis: Default localhost:6379 (used for task queue via Celery)
- Dev container: `.devcontainer/devcontainer.json` for VS Code Remote Containers

---

## Code Patterns & Conventions

### Backend (Python/FastAPI)

1. **API Structure**: `/api/v1/*` routes, versioned for stability
2. **Async-first**: All I/O operations use async (FastAPI → asyncio)
3. **Configuration**: Centralized in [backend/app/core/config.py](backend/app/core/config.py) using Pydantic BaseSettings
4. **Models**: Pydantic v2 for request/response validation; SQLAlchemy 2.0 for ORM
5. **Logging**: `loguru` for structured logging (DEBUG/INFO/WARN/ERROR/FATAL levels)
6. **Error Handling**: Return standardized error responses with `detail` and status codes

Example FastAPI pattern:
```python
@app.post("/tasks", status_code=201)
async def create_task(task: TaskCreate) -> Task:
    # Validation via Pydantic, returns Task model
    return db.create(task)
```

### Frontend (Vue3/TypeScript)

1. **Component Structure**: SFC (Single File Components) with `<script setup>` syntax (Vue 3.3+)
2. **State Management**: Pinia stores for global state (no direct component mutations)
3. **Type Safety**: Full TypeScript; avoid `any` types
4. **HTTP Client**: Axios configured with API base URL and interceptors for auth
5. **UI Components**: Element Plus (predefined: Button, Container, Header, etc.)

Example Vue pattern:
```typescript
<script setup lang="ts">
import { useTaskStore } from '@/stores/tasks'
const tasks = useTaskStore()
const handleCreate = async (name: string) => {
  await tasks.create(name)  // Pinia action
}
</script>
```

### Electron (TypeScript)

1. **Process Model**: Main process handles window lifecycle; Renderer runs Vue app
2. **IPC Communication**: Use preload bridge for safe main ↔ renderer communication
3. **Dev Server URL**: Electron loads from Vite dev server in dev mode; packaged HTML in production
4. **Window Config**: Width 1200×800; `contextIsolation: false` (simplification; should use `true` + preload for security)

---

## Cross-Component Patterns

### Task Execution Flow

1. **Frontend**: User creates/edits task → POST `/api/v1/tasks/{id}/execute`
2. **Backend**:
   - Validates task exists and is enabled
   - Loads execution flow from DB
   - Dispatches to `ExecutionEngine.execute(task_id, mode='foreground'|'background')`
   - Stores execution result with status (success/failure/timeout)
3. **Device Adapter** (via ExecutionEngine):
   - Resolves platform → loads appropriate adapter (Windows/macOS/Android/iOS)
   - Executes atomic actions (click, input, wait) sequentially
4. **Logging**: Each action logs to InfluxDB; results indexed by `execution_id` + `task_id`

### Plugin Integration Points

- **Actions**: Custom actions registered in plugin's `actions.py` and exported in `__init__.py`
- **Device Support**: Implement device adapter interface; register in plugin config
- **Config Schema**: Use Pydantic model in plugin's `config.py` for validation

---

## Testing Strategy

### Backend (pytest)

```python
# Use pytest fixtures for async setup
@pytest.mark.asyncio
async def test_execute_task():
    result = await engine.execute(task_id=1)
    assert result.status == "success"
```

### Frontend (Vitest/Jest recommended but not yet integrated)

- Currently no test infrastructure; future: add Vitest config to `vite.config.ts`

---

## Key Dependencies & Versions

- **Python**: 3.10+ (strict type hints)
- **FastAPI**: ≥0.100.0 (async, auto-docs)
- **SQLAlchemy**: ≥2.0.0 (async support via `sqlalchemy.ext.asyncio`)
- **Celery**: ≥5.3.0 (background task queue; integrated with Redis)
- **Playwright**: ≥1.36.0 (browser automation on desktop)
- **pyautogui**: ≥0.9.54 (keyboard/mouse control)
- **Vue**: ^3.3.4 (Composition API default)
- **Electron**: ^26.1.0 (desktop shell)
- **Node.js**: 16+

---

## Important Caveats & TODOs

1. **Security**: Electron's `contextIsolation: false` should be `true` with proper preload bridge
2. **Mobile Integration**: `mobile/` structure exists but execution logic not yet cross-linked
3. **Plugin Loader**: Plugin registration mechanism not yet fully documented; inspect `backend/app/` for integration points
4. **Testing**: Frontend lacks test coverage; backend has framework but no tests written yet
5. **Monitoring**: InfluxDB/Redis integration points referenced but not fully implemented

---

## Useful File References

- **Task Definition Schema**: [backend/app/api](backend/app/api) (define routes and models here)
- **Execution Logic**: [backend/app/core/config.py](backend/app/core/config.py) → extend with execution engine
- **Frontend Components**: [frontend/src/App.vue](frontend/src/App.vue) (scaffold starting here)
- **Plugin Example**: [plugins/examples/hello_world.py](plugins/examples/hello_world.py)
- **Architecture**: [docs/architecture/README.md](docs/architecture/README.md) (comprehensive design)
- **Docker Services**: [docker-compose.yml](docker-compose.yml) (MySQL, Redis, InfluxDB, MinIO)
