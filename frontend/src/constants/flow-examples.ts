import basicActions from '../../../docs/examples/engine/01_basic_actions.flow.yaml?raw'
import templates from '../../../docs/examples/engine/02_templates.flow.yaml?raw'
import condition from '../../../docs/examples/engine/03_condition.flow.yaml?raw'
import foreach from '../../../docs/examples/engine/04_foreach.flow.yaml?raw'
import retry from '../../../docs/examples/engine/05_retry.flow.yaml?raw'
import largeOutput from '../../../docs/examples/engine/09_large_output.flow.yaml?raw'
import hooks from '../../../docs/examples/flow_with_hooks.yaml?raw'
import desktopCheckin from '../../../docs/examples/desktop_checkin.flow.yaml?raw'
import zhihuDigest from '../../../docs/examples/zhihu_digest.flow.yaml?raw'
import { locale } from '../i18n'

export interface FlowExample {
  label: string
  labelEn: string
  yaml: string
  hint?: string
  hintEn?: string
}

export const FLOW_EXAMPLES: Record<string, FlowExample> = {
  basic: {
    label: '基础 Action 串联',
    labelEn: 'Basic Action Chain',
    yaml: basicActions,
  },
  templates: {
    label: '模板 input / vars',
    labelEn: 'Template input / vars',
    yaml: templates,
    hint: '示例参数：input = {"name": "AutoFlow"}，vars = {"city": "上海"}',
    hintEn: 'Example params: input = {"name": "AutoFlow"}, vars = {"city": "Shanghai"}',
  },
  condition: {
    label: '条件执行',
    labelEn: 'Conditional Step',
    yaml: condition,
    hint: '示例参数：vars = {"mode": "enabled"}',
    hintEn: 'Example params: vars = {"mode": "enabled"}',
  },
  foreach: {
    label: 'for_each 循环',
    labelEn: 'for_each Loop',
    yaml: foreach,
    hint: '示例参数：input = {"items": ["a", "b", "c"]}',
    hintEn: 'Example params: input = {"items": ["a", "b", "c"]}',
  },
  retry: {
    label: '失败重试',
    labelEn: 'Retry on Failure',
    yaml: retry,
    hint: '示例参数：vars = {"marker_dir": "/tmp"}（容器内同样为 /tmp）',
    hintEn: 'Example params: vars = {"marker_dir": "/tmp"}',
  },
  largeOutput: {
    label: '大输出转产物',
    labelEn: 'Large Output Artifact',
    yaml: largeOutput,
    hint: '输出超过 64KB 时自动落盘为产物，可下载',
    hintEn: 'Outputs exceeding 64KB are automatically saved as downloadable artifacts',
  },
  hooks: {
    label: 'Hooks（成功/失败）',
    labelEn: 'Hooks (on_success/on_failure)',
    yaml: hooks,
    hint: 'on_success 上报 KnowFlow，需要配置 KNOWFLOW_BASE_URL',
    hintEn: 'on_success reports to KnowFlow (requires KNOWFLOW_BASE_URL)',
  },
  desktop: {
    label: '桌面签到（模拟）',
    labelEn: 'Desktop Check-in (Dry Run)',
    yaml: desktopCheckin,
    hint: '建议勾选"模拟执行"',
    hintEn: 'Recommended to enable "Dry Run"',
  },
  zhihu: {
    label: '知乎摘要（模拟）',
    labelEn: 'Q&A Digest (Dry Run)',
    yaml: zhihuDigest,
    hint: '建议勾选"模拟执行"，真实抓取需要 ZHIHU_COOKIE',
    hintEn: 'Recommended to enable "Dry Run"; live scraping requires ZHIHU_COOKIE',
  },
}

export function getFlowExampleLabel(example: FlowExample): string {
  return locale.value === 'en' ? example.labelEn : example.label
}

export function getFlowExampleHint(example: FlowExample): string {
  if (locale.value === 'en') return example.hintEn ?? example.hint ?? ''
  return example.hint ?? ''
}

export const DEFAULT_FLOW_YAML_ZH = basicActions
export const DEFAULT_FLOW_YAML_EN = basicActions
  .replace(
    '# @brief 内置 Action 串联：core.log / core.sleep / dummy.echo + output_var',
    '# @brief Built-in Action Chain: core.log / core.sleep / dummy.echo + output_var',
  )
  .replace('name: 记录日志', 'name: Log Message')
  .replace('name: 短暂等待', 'name: Brief Delay')
  .replace('name: 回显并写入运行时变量', 'name: Echo & Save Runtime Var')

export function getDefaultFlowYaml(): string {
  return locale.value === 'en' ? DEFAULT_FLOW_YAML_EN : DEFAULT_FLOW_YAML_ZH
}

export const DEFAULT_FLOW_YAML = basicActions
