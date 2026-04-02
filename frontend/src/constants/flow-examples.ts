export const FLOW_EXAMPLES = {
  echo: `version: "1"
name: "echo-demo"
steps:
  - id: "s1"
    action:
      type: "dummy.echo"
      params:
        message: "Hello from Frontend"
    check:
      type: "text.contains"
      params:
        needle: "Frontend"`,
  desktop: `version: "1"
name: "desktop-demo"
steps:
  - id: "move-mouse"
    action:
      type: "desktop.click"
      params:
        x: 100
        y: 100
        clicks: 1
  - id: "screenshot"
    action:
      type: "desktop.screenshot"
      params:
        name: "demo-shot"`,
  zhihu: `version: "1"
name: "zhihu-digest"
steps:
  - id: "fetch"
    action:
      type: "zhihu.fetch_answer"
      params:
        url: "https://www.zhihu.com/question/784489052/answer/1946200783080125276"
  - id: "summarize"
    action:
      type: "ai.deepseek_summarize"
      params:
        system_prompt: "Summarize this answer"`,
};

export const DEFAULT_FLOW_YAML = `version: "1"
name: "demo-flow"
steps:
  - id: "hello"
    action:
      type: "core.log"
      params:
        message: "Hello AutoFlow!"
`;
