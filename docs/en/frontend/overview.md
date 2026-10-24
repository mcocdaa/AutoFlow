---
title: Frontend Overview
description: Visual VueFlow DAG canvas, Flow Hub marketplace, step debugger, and bilingual zh-CN/en-US frontend architecture
keywords: [frontend, Vue, VueFlow, debugger, i18n]
version: "2.1"
---

# Frontend Overview

The AutoFlow frontend is built with **Vue 3.5 + Vite + Ant Design Vue 4 + VueFlow + CodeMirror 6**. It provides seven core views—Visual DAG Canvas, Flow Hub Marketplace, Run Flow, Step Debugger, Run History, Secrets Vault, and Plugins—with full **`zh-CN` / `en-US` bilingual switching**.

## Routes & Capabilities

| Route | View | Key Capabilities |
|---|---|---|
| `/canvas` (`/` redirects here) | Visual Canvas (`FlowCanvasView`) | Three-pane studio powered by `@vue-flow/core`: Component Palette on the left (search & drag-and-drop), interactive DAG canvas in the center (live node status glow, `depends_on` edges, auto-layout, and Gantt `ExecutionTimeline`), and Property Panel on the right (step config, strong Check assertions, two-way live YAML sync, Cron schedule preview, and Webhook trigger gateway) |
| `/hub` | Flow Hub (`FlowHubView`) | Curated production workflow templates (SRE Auto-Remediation, AI Scraping & Digest, Quality Gate, Desktop RPA) with category filtering, keyword search, YAML preview, one-click install to `flows/`, and direct loading into the visual canvas |
| `/run` | Run Flow (`RunFlowView`) | CodeMirror 6 YAML editor, saved flow & preset loader, `input` / `vars` JSON parameters, `dry_run` mode, and `ResultsPanel` (steps, checks, `for_each` iterations, externalized artifacts, hooks, and time-travel forking) |
| `/debug` | Step Debugger (`DebugView`) | Interactive debug sessions with Step, Continue to Breakpoint, Run All, and Stop controls; inspect step outputs, Check assertions, iterations, and artifacts; local pre-execution breakpoints; session recovery via `?session=<id>` and historical run forking (`forked_from`) |
| `/runs` | Run History (`RunsView`) | Historical run list (status, start time, duration, step count), detail drawer, one-click replay, and deletion (with artifacts); fork debug sessions from any step or select 2 runs for side-by-side comparison (`RunDiffPanel`) |
| `/secrets` | Secrets Vault (`SecretsView`) | Local AES-256-GCM encrypted credential management (create, update, delete, search) with one-click `{{secrets.KEY}}` macro copy and full-pipeline log/artifact redaction preview |
| `/plugins` | Plugins (`PluginsView`) | Inspect loaded plugins, registered Actions & Checks (with search and click-to-copy), capability counters, and plugin load error diagnostics |

## Backend API Mapping

- `GET /api/v1/flows`, `POST /api/v1/flows`, `GET /api/v1/cron/predict`, `POST /api/v1/webhooks/{flow}/{token}` → Visual Canvas & Trigger configuration
- `GET /api/v1/hub/flows`, `GET /api/v1/hub/flows/{id}/yaml`, `POST /api/v1/hub/flows/{id}/install` → Flow Hub (`FlowHubView`)
- `POST /api/v1/runs/execute`, `GET /api/v1/runs`, `GET /api/v1/runs/{id}`, `DELETE /api/v1/runs/{id}`, `GET /api/v1/runs/{id}/artifacts/{path}`, `POST /api/v1/runs/{id}/replay`, `GET /api/v1/runs/{id}/diff/{other}` → Run Flow & Run History
- `POST /api/v1/debug/sessions`, `POST /api/v1/debug/sessions/fork`, and step/run/abort endpoints → Step Debugger & Time-Travel Forking
- `GET /api/v1/secrets`, `POST /api/v1/secrets`, `DELETE /api/v1/secrets/{key}` → Secrets Vault
- `GET /api/v1/plugins`, `GET /api/v1/plugins/catalog` → Plugins View & dynamic Palette catalog

## Bilingual i18n & UI Conventions

- **Bilingual (`zh-CN` / `en-US`)**: Persisted in `localStorage('autoflow_lang')`. Toggling the header language button (`[data-testid="lang-toggle"]`) dynamically switches all UI copy, component catalog metadata, preset/saved Flow YAML comments and step names, and the Ant Design Vue `ConfigProvider` locale.
- **Theme & Design Tokens**: Centralized in `src/theme/flow-design-theme.ts` and `src/theme/styles.css`. Shared components include `PageHeader`, `CodeEditor`, `FlowParamsEditor`, `ResultsPanel`, and `RunDiffPanel`.
- **Responsive Layout**: Designed for both `1440px` desktop and `1024px` split-screen viewports without horizontal overflow.
