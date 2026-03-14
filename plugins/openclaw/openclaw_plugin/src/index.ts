/**
 * AutoFlow OpenClaw Plugin
 * Registers 3 agent tools for AutoFlow workflow automation
 */

const DEFAULT_BASE_URL = "http://localhost:8000";

/**
 * HTTP request helper for AutoFlow API
 */
async function apiRequest(
  baseUrl: string,
  method: string,
  path: string,
  body?: object
): Promise<unknown> {
  const url = `${baseUrl}${path}`;
  const options: RequestInit = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  const response = await fetch(url, options);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`AutoFlow API error ${response.status}: ${errorText}`);
  }
  return response.json();
}

/**
 * Resolve baseUrl from plugin config
 */
function getBaseUrl(api: any): string {
  try {
    const cfg = api.getConfig?.() || {};
    return cfg.baseUrl || DEFAULT_BASE_URL;
  } catch {
    return DEFAULT_BASE_URL;
  }
}

/**
 * Plugin entry point - standard OpenClaw format
 */
export default function (api: any) {
  api.logger?.info?.("[autoflow] AutoFlow plugin loading...");

  // Tool 1: autoflow_run - Execute a Flow
  api.registerTool({
    name: "autoflow_run",
    description:
      "Execute an AutoFlow workflow by providing flow YAML definition. Returns the run result with execution details.",
    parameters: {
      type: "object",
      properties: {
        flowYaml: {
          type: "string",
          description: "Flow YAML definition (required)",
        },
        input: {
          type: "object",
          description: "Input data to pass to the flow (optional)",
        },
        vars: {
          type: "object",
          description: "Variables to inject into the flow context (optional)",
        },
      },
      required: ["flowYaml"],
    },
    async execute(_id: string, params: any) {
      const baseUrl = getBaseUrl(api);
      const { flowYaml, input, vars = {} } = params;

      const result = await apiRequest(baseUrl, "POST", "/api/v1/runs/execute", {
        flow_yaml: flowYaml,
        input,
        vars,
      });

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result),
          },
        ],
      };
    },
  });

  // Tool 2: autoflow_list - List run records
  api.registerTool({
    name: "autoflow_list",
    description:
      "List all workflow execution records. Returns a list of run results with their IDs, status, and timestamps.",
    parameters: {
      type: "object",
      properties: {},
    },
    async execute(_id: string, params: any) {
      const baseUrl = getBaseUrl(api);

      const result = await apiRequest(baseUrl, "GET", "/api/v1/runs");

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result),
          },
        ],
      };
    },
  });

  // Tool 3: autoflow_plugins - Query available plugins
  api.registerTool({
    name: "autoflow_plugins",
    description:
      "Query available AutoFlow plugins, actions, and checks. Returns registered plugins with their versions, available actions, and validation checks.",
    parameters: {
      type: "object",
      properties: {},
    },
    async execute(_id: string, params: any) {
      const baseUrl = getBaseUrl(api);

      const result = await apiRequest(baseUrl, "GET", "/api/v1/plugins");

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(result),
          },
        ],
      };
    },
  });

  api.logger?.info?.("[autoflow] AutoFlow plugin loaded: 3 tools registered");
}