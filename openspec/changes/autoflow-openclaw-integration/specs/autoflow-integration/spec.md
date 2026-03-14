# Delta for AutoFlow OpenClaw Integration

## ADDED Requirements

### Requirement: Variable Template Resolution
The runner SHALL support variable templates in action params using {{steps.X.output}} and {{vars.X}} syntax.

#### Scenario: Step output reference
- GIVEN a flow with step A producing output and step B referencing it
- WHEN step B params contain {{steps.A.output}}
- THEN the runner resolves the template to step A's actual output before executing step B

### Requirement: OpenClaw Actions Plugin
AutoFlow SHALL provide an openclaw plugin registering actions for OpenClaw integration.

#### Scenario: Execute HTTP request action
- GIVEN the openclaw plugin is loaded
- WHEN a flow step uses openclaw.http_request action
- THEN the action makes an HTTP request and returns the response

### Requirement: OpenClaw Agent Tool
OpenClaw SHALL have a native autoflow plugin that registers autoflow_run as an agent tool.

#### Scenario: Agent executes a flow
- GIVEN the autoflow plugin is installed in OpenClaw
- WHEN Agent calls autoflow_run with flow YAML
- THEN the plugin sends the flow to AutoFlow API and returns the run result

### Requirement: Conditional Branching
The runner SHALL support conditional step execution via a condition field on StepSpec.

#### Scenario: Skip step when condition is false
- GIVEN a step has condition: "{{vars.should_run}} == true"
- WHEN vars.should_run is false
- THEN the step is skipped with status "skipped"

### Requirement: ForEach Loop
The runner SHALL support iterating over a list via a forEach field on StepSpec.

#### Scenario: Execute step for each item
- GIVEN a step has forEach: "{{vars.items}}" and vars.items is ["a","b","c"]
- WHEN the runner processes this step
- THEN the step executes 3 times with {{item}} bound to each value
