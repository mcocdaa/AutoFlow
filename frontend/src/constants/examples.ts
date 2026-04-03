import type {
  Example,
  ExampleCategory,
  ExampleDifficulty,
} from "../types/workflow";

const CUSTOM_EXAMPLES_STORAGE_KEY = "autoflow_custom_examples";
const MAX_CUSTOM_EXAMPLES = 100;

export const EXAMPLE_CATEGORIES: Record<
  ExampleCategory,
  { name: string; icon: string; color: string }
> = {
  tutorial: {
    name: "入门教程",
    icon: "📚",
    color: "#3B82F6",
  },
  browser: {
    name: "浏览器自动化",
    icon: "🌐",
    color: "#8B5CF6",
  },
  data: {
    name: "数据处理",
    icon: "📊",
    color: "#10B981",
  },
  api: {
    name: "API交互",
    icon: "🔌",
    color: "#F97316",
  },
  control: {
    name: "条件循环",
    icon: "🔄",
    color: "#F59E0B",
  },
  comprehensive: {
    name: "综合案例",
    icon: "🎯",
    color: "#EF4444",
  },
};

export const EXAMPLE_DIFFICULTIES: Record<
  ExampleDifficulty,
  { name: string; level: number }
> = {
  beginner: {
    name: "入门",
    level: 1,
  },
  intermediate: {
    name: "中级",
    level: 2,
  },
  advanced: {
    name: "高级",
    level: 3,
  },
};

export const customExamplesStorage = {
  getAll(): Example[] {
    try {
      const stored = localStorage.getItem(CUSTOM_EXAMPLES_STORAGE_KEY);
      if (!stored) return [];
      const parsed = JSON.parse(stored);
      return parsed.map((example: any) => ({
        ...example,
        createdAt: new Date(example.createdAt),
        updatedAt: new Date(example.updatedAt),
      }));
    } catch {
      return [];
    }
  },

  save(
    example: Omit<
      Example,
      | "id"
      | "createdAt"
      | "updatedAt"
      | "isOfficial"
      | "usageCount"
      | "rating"
      | "isFavorite"
    >,
  ): Example {
    const examples = this.getAll();
    const newExample: Example = {
      ...example,
      id: `custom-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      createdAt: new Date(),
      updatedAt: new Date(),
      isOfficial: false,
      isFavorite: false,
      usageCount: 0,
      rating: 5.0,
    };

    examples.unshift(newExample);

    if (examples.length > MAX_CUSTOM_EXAMPLES) {
      examples.splice(MAX_CUSTOM_EXAMPLES);
    }

    localStorage.setItem(CUSTOM_EXAMPLES_STORAGE_KEY, JSON.stringify(examples));
    return newExample;
  },

  update(
    id: string,
    updates: Partial<Omit<Example, "id" | "createdAt" | "isOfficial">>,
  ): Example | null {
    const examples = this.getAll();
    const index = examples.findIndex((e) => e.id === id);
    if (index === -1) return null;

    examples[index] = {
      ...examples[index],
      ...updates,
      updatedAt: new Date(),
    };

    localStorage.setItem(CUSTOM_EXAMPLES_STORAGE_KEY, JSON.stringify(examples));
    return examples[index];
  },

  delete(id: string): boolean {
    const examples = this.getAll();
    const initialLength = examples.length;
    const filtered = examples.filter((e) => e.id !== id);

    if (filtered.length === initialLength) return false;

    localStorage.setItem(CUSTOM_EXAMPLES_STORAGE_KEY, JSON.stringify(filtered));
    return true;
  },

  toggleFavorite(id: string): boolean {
    const examples = this.getAll();
    const index = examples.findIndex((e) => e.id === id);
    if (index === -1) return false;

    examples[index].isFavorite = !examples[index].isFavorite;
    examples[index].updatedAt = new Date();

    localStorage.setItem(CUSTOM_EXAMPLES_STORAGE_KEY, JSON.stringify(examples));
    return true;
  },
};

// ─────────────────────────────────────────────────────────────
//  Official examples — v2 DAG format, backend-compatible
// ─────────────────────────────────────────────────────────────

export const OFFICIAL_EXAMPLES: Example[] = [
  // ── Example 1: Hello World ──────────────────────────────────
  {
    id: "hello-world",
    name: "Hello World",
    description:
      "最简单的工作流：开始节点传递 'Hello World!' 到 Log 节点，Log 将输入打印到终端并向结束节点输出空消息。",
    category: "tutorial",
    tags: ["入门", "基础", "日志"],
    difficulty: "beginner",
    author: "AutoFlow Team",
    createdAt: new Date("2024-01-01"),
    updatedAt: new Date("2024-01-01"),
    isOfficial: true,
    isFavorite: false,
    usageCount: 1200,
    rating: 4.8,
    yamlContent: `version: "2.0"
name: "hello-world"
description: "Start -> Log -> End"
inputs: {}
nodes:
  start:
    id: "start"
    name: "开始"
    type: "start"
    config: {}
    metadata:
      x: 80
      y: 120
    inputs: []
    outputs:
      - id: "message"
        name: "Message"
        type: "string"
  log_hello:
    id: "log_hello"
    name: "Hello World"
    type: "action"
    config:
      action_type: "core.log"
      level: "info"
    metadata:
      x: 380
      y: 120
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
    error_port:
      id: "error"
      name: "Error"
      type: "any"
      required: false
  end:
    id: "end"
    name: "结束"
    type: "end"
    config: {}
    metadata:
      x: 680
      y: 120
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs: []
edges:
  - id: "e1"
    source: "start.message"
    target: "log_hello.input"
  - id: "e2"
    source: "log_hello.output"
    target: "end.input"
`,
  },
  // ── Example 2: If Condition ─────────────────────────────────
  {
    id: "if-condition",
    name: "If 条件判断",
    description:
      "开始节点输入一个数字，If 节点判断是否大于 100，分别走不同分支输出日志，最后汇入结束节点。",
    category: "control",
    tags: ["条件", "分支", "If", "入门"],
    difficulty: "beginner",
    author: "AutoFlow Team",
    createdAt: new Date("2024-01-02"),
    updatedAt: new Date("2024-01-02"),
    isOfficial: true,
    isFavorite: false,
    usageCount: 860,
    rating: 4.7,
    yamlContent: `version: "2.0"
name: "if-condition"
description: "Start -> If(>100) -> Log(大于100) / Log(小于等于100) -> End"
inputs: {}
nodes:
  start:
    id: "start"
    name: "开始"
    type: "start"
    config: {}
    metadata:
      x: 80
      y: 200
    inputs: []
    outputs:
      - id: "number"
        name: "Number"
        type: "number"
  check:
    id: "check"
    name: "判断 > 100"
    type: "if"
    config: {}
    metadata:
      x: 380
      y: 200
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs:
      - id: "true"
        name: "大于100"
        type: "any"
        condition: "input > 100"
      - id: "false"
        name: "小于等于100"
        type: "any"
  log_gt:
    id: "log_gt"
    name: "输出 大于100"
    type: "action"
    config:
      action_type: "core.log"
      level: "info"
    metadata:
      x: 680
      y: 80
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
    error_port:
      id: "error"
      name: "Error"
      type: "any"
      required: false
  log_lt:
    id: "log_lt"
    name: "输出 小于等于100"
    type: "action"
    config:
      action_type: "core.log"
      level: "info"
    metadata:
      x: 680
      y: 320
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs:
      - id: "output"
        name: "Output"
        type: "any"
    error_port:
      id: "error"
      name: "Error"
      type: "any"
      required: false
  end:
    id: "end"
    name: "结束"
    type: "end"
    config: {}
    metadata:
      x: 980
      y: 200
    inputs:
      - id: "input"
        name: "Input"
        type: "any"
        required: true
    outputs: []
edges:
  - id: "e1"
    source: "start.number"
    target: "check.input"
  - id: "e2"
    source: "check.true"
    target: "log_gt.input"
  - id: "e3"
    source: "check.false"
    target: "log_lt.input"
  - id: "e4"
    source: "log_gt.output"
    target: "end.input"
  - id: "e5"
    source: "log_lt.output"
    target: "end.input"
`,
  },
];
