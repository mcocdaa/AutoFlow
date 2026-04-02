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

export const OFFICIAL_EXAMPLES: Example[] = [
  {
    id: "hello-world",
    name: "Hello World",
    description: "最简单的工作流示例，学习如何使用日志节点",
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
    yamlContent: `version: "1"
name: "hello-world"
steps:
  - id: "hello"
    action:
      type: "core.log"
      params:
        message: "Hello World!"
`,
  },
  {
    id: "open-baidu",
    name: "打开百度并截图",
    description: "打开百度首页并保存截图",
    category: "browser",
    tags: ["浏览器", "截图", "导航"],
    difficulty: "beginner",
    author: "AutoFlow Team",
    createdAt: new Date("2024-01-05"),
    updatedAt: new Date("2024-01-05"),
    isOfficial: true,
    isFavorite: false,
    usageCount: 890,
    rating: 4.7,
    yamlContent: `version: "1"
name: "baidu-screenshot"
steps:
  - id: "navigate"
    action:
      type: "browser.navigate"
      params:
        url: "https://www.baidu.com"
  - id: "wait"
    action:
      type: "core.wait"
      params:
        duration: 2000
  - id: "screenshot"
    action:
      type: "browser.screenshot"
      params:
        name: "baidu-homepage"
`,
  },
  {
    id: "http-get-request",
    name: "HTTP GET请求",
    description: "发送HTTP GET请求并查看响应",
    category: "api",
    tags: ["API", "HTTP", "网络"],
    difficulty: "beginner",
    author: "AutoFlow Team",
    createdAt: new Date("2024-01-10"),
    updatedAt: new Date("2024-01-10"),
    isOfficial: true,
    isFavorite: false,
    usageCount: 650,
    rating: 4.6,
    yamlContent: `version: "1"
name: "http-request"
steps:
  - id: "request"
    action:
      type: "tool.http_request"
      params:
        method: "GET"
        url: "https://httpbin.org/get"
  - id: "log-response"
    action:
      type: "core.log"
      params:
        message: "{{steps.request.output}}"
`,
  },
  {
    id: "simple-condition",
    name: "简单条件判断",
    description: "学习如何使用条件节点进行分支判断",
    category: "control",
    tags: ["条件", "分支", "逻辑"],
    difficulty: "intermediate",
    author: "AutoFlow Team",
    createdAt: new Date("2024-01-15"),
    updatedAt: new Date("2024-01-15"),
    isOfficial: true,
    isFavorite: false,
    usageCount: 420,
    rating: 4.5,
    yamlContent: `version: "1"
name: "simple-condition"
steps:
  - id: "set-var"
    action:
      type: "core.set_var"
      params:
        name: "number"
        value: 10
  - id: "condition"
    action:
      type: "core.if"
      params:
        condition: "{{number}} > 5"
    on_success:
      - id: "greater"
        action:
          type: "core.log"
          params:
            message: "数字大于5"
    on_failure:
      - id: "less"
        action:
          type: "core.log"
          params:
            message: "数字小于等于5"
`,
  },
  {
    id: "weather-query",
    name: "天气预报查询",
    description: "查询天气并保存结果到文件",
    category: "comprehensive",
    tags: ["天气", "API", "文件", "综合"],
    difficulty: "advanced",
    author: "AutoFlow Team",
    createdAt: new Date("2024-01-20"),
    updatedAt: new Date("2024-01-20"),
    isOfficial: true,
    isFavorite: false,
    usageCount: 310,
    rating: 4.9,
    yamlContent: `version: "1"
name: "weather-query"
steps:
  - id: "set-city"
    action:
      type: "core.set_var"
      params:
        name: "city"
        value: "北京"
  - id: "fetch-weather"
    action:
      type: "tool.http_request"
      params:
        method: "GET"
        url: "https://wttr.in/{{city}}?format=j1"
  - id: "save-to-file"
    action:
      type: "tool.write_file"
      params:
        path: "./weather-result.json"
        content: "{{steps.fetch-weather.output}}"
  - id: "log-success"
    action:
      type: "core.log"
      params:
        message: "天气数据已保存！"
`,
  },
];
