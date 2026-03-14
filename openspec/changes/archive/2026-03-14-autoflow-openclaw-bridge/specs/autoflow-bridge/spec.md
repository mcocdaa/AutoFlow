# Delta for AutoFlow Bridge

## ADDED Requirements

### Requirement: 执行 Flow
The system SHALL allow OpenClaw Agent to execute an AutoFlow flow through a simple bridge command.

#### Scenario: Execute flow from YAML
- GIVEN AutoFlow service is running
- WHEN Agent provides a flow YAML and optional input/vars
- THEN the bridge executes `POST /api/v1/runs/execute`
- AND returns run result in structured JSON

### Requirement: 查询运行记录
The system SHALL allow Agent to list and inspect AutoFlow runs.

#### Scenario: List runs
- GIVEN AutoFlow has historical runs
- WHEN Agent calls the bridge list command
- THEN the bridge returns recent runs with id, status, flow name and timestamps

#### Scenario: Get run detail
- GIVEN a run id exists
- WHEN Agent calls the bridge get command
- THEN the bridge returns the full run result

### Requirement: 发现可用插件能力
The system SHALL allow Agent to inspect available AutoFlow plugins, actions and checks.

#### Scenario: List plugins
- GIVEN AutoFlow has loaded plugins
- WHEN Agent calls the bridge plugins command
- THEN the bridge returns plugin names, actions and checks

### Requirement: 流程模板复用
The system SHALL provide reusable Flow templates for common complex workflows.

#### Scenario: Use a template flow
- GIVEN a common workflow such as project bootstrap or API smoke test
- WHEN Agent reads the usage guide
- THEN Agent can adapt a provided YAML template into an executable AutoFlow flow

### Requirement: 使用指导
The system SHALL document when to use AutoFlow instead of plain dialogue.

#### Scenario: Choose AutoFlow for a complex repeated workflow
- GIVEN a task has multiple deterministic steps
- WHEN Agent evaluates execution strategy
- THEN the guide recommends converting it into an AutoFlow flow instead of repeated chat turns
