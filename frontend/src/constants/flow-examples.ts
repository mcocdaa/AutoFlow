import basicActions from '../../../docs/examples/engine/01_basic_actions.flow.yaml?raw'
import templates from '../../../docs/examples/engine/02_templates.flow.yaml?raw'
import condition from '../../../docs/examples/engine/03_condition.flow.yaml?raw'
import foreach from '../../../docs/examples/engine/04_foreach.flow.yaml?raw'
import retry from '../../../docs/examples/engine/05_retry.flow.yaml?raw'
import largeOutput from '../../../docs/examples/engine/09_large_output.flow.yaml?raw'
import hooks from '../../../docs/examples/flow_with_hooks.yaml?raw'
import desktopCheckin from '../../../docs/examples/desktop_checkin.flow.yaml?raw'
import zhihuDigest from '../../../docs/examples/zhihu_digest.flow.yaml?raw'

export interface FlowExample {
  label: string
  yaml: string
  hint?: string
}

export const FLOW_EXAMPLES: Record<string, FlowExample> = {
  basic: {
    label: '基础 Action 串联',
    yaml: basicActions,
  },
  templates: {
    label: '模板 input / vars',
    yaml: templates,
    hint: '示例参数：input = {"name": "AutoFlow"}，vars = {"city": "上海"}',
  },
  condition: {
    label: '条件执行',
    yaml: condition,
    hint: '示例参数：vars = {"mode": "enabled"}',
  },
  foreach: {
    label: 'for_each 循环',
    yaml: foreach,
    hint: '示例参数：input = {"items": ["a", "b", "c"]}',
  },
  retry: {
    label: '失败重试',
    yaml: retry,
    hint: '示例参数：vars = {"marker_dir": "/tmp"}（容器内同样为 /tmp）',
  },
  largeOutput: {
    label: '大输出转产物',
    yaml: largeOutput,
    hint: '输出超过 64KB 时自动落盘为产物，可下载',
  },
  hooks: {
    label: 'Hooks（成功/失败）',
    yaml: hooks,
    hint: 'on_success 上报 KnowFlow，需要配置 KNOWFLOW_BASE_URL',
  },
  desktop: {
    label: '桌面签到（模拟）',
    yaml: desktopCheckin,
    hint: '建议勾选"模拟执行"',
  },
  zhihu: {
    label: '知乎摘要（模拟）',
    yaml: zhihuDigest,
    hint: '建议勾选"模拟执行"，真实抓取需要 ZHIHU_COOKIE',
  },
}

export const DEFAULT_FLOW_YAML = basicActions
