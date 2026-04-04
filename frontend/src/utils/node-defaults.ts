import type { InputPort, OutputPort } from "../types/dag-workflow";

const ERR_PORT: OutputPort = { id: "error", name: "Error", type: "any" };

/** Returns the default `config` object for a node type. */
export function getDefaultConfig(type: string): Record<string, unknown> {
  if (type === "core.log") return { action_type: "core.log" };
  return {};
}

/** Returns the backend-canonical default ports for each node type. */
export function getDefaultPorts(type: string): {
  inputs: InputPort[];
  outputs: OutputPort[];
  error_port: OutputPort | undefined;
} {
  switch (type) {
    case "start":
      return {
        inputs: [],
        outputs: [{ id: "output", name: "Output", type: "any" }],
        error_port: undefined,
      };

    case "end":
      return {
        inputs: [{ id: "input", name: "Input", type: "any", required: true }],
        outputs: [],
        error_port: undefined,
      };

    case "if":
      return {
        inputs: [{ id: "input", name: "Input", type: "any", required: true }],
        outputs: [
          { id: "true", name: "True", type: "any", condition: null },
          { id: "false", name: "False", type: "any" },
        ],
        error_port: ERR_PORT,
      };

    case "switch":
      return {
        inputs: [{ id: "input", name: "Input", type: "any", required: true }],
        outputs: [{ id: "default", name: "Default", type: "any" }],
        error_port: ERR_PORT,
      };

    case "for":
      return {
        inputs: [{ id: "items", name: "Items", type: "array", required: true }],
        outputs: [{ id: "results", name: "Results", type: "array" }],
        error_port: ERR_PORT,
      };

    case "while":
      return {
        inputs: [
          { id: "initial", name: "Initial", type: "any", required: true },
          { id: "condition", name: "Condition", type: "any", required: true },
        ],
        outputs: [{ id: "result", name: "Result", type: "any" }],
        error_port: ERR_PORT,
      };

    case "merge":
      return {
        inputs: [
          { id: "input1", name: "Input 1", type: "any", required: true },
          { id: "input2", name: "Input 2", type: "any", required: false },
        ],
        outputs: [{ id: "output", name: "Output", type: "any" }],
        error_port: ERR_PORT,
      };

    case "split":
      return {
        inputs: [{ id: "input", name: "Input", type: "any", required: true }],
        outputs: [
          { id: "output1", name: "Output 1", type: "any" },
          { id: "output2", name: "Output 2", type: "any" },
        ],
        error_port: ERR_PORT,
      };

    case "input":
      return {
        inputs: [],
        outputs: [{ id: "output", name: "Output", type: "any" }],
        error_port: undefined,
      };

    case "group":
    case "subflow":
      return { inputs: [], outputs: [], error_port: ERR_PORT };

    default:
      // action, pass, retry, core.log, and any plugin action type
      return {
        inputs: [{ id: "input", name: "Input", type: "any", required: true }],
        outputs: [{ id: "output", name: "Output", type: "any" }],
        error_port: ERR_PORT,
      };
  }
}
