import { locale } from '../i18n'

export const PLUGIN_DESCRIPTIONS: Record<string, string> = {
  builtin: '内置通用 Action（日志、等待）与 Check（文本包含等）',
  dummy: '回显测试插件，用于验证最小流程',
  openclaw: 'OpenClaw 集成：HTTP 请求、命令执行与记录上报',
  'ai-deepseek': 'DeepSeek 文本总结',
  'zhihu-digest': '知乎回答抓取与摘要草稿',
  'desktop-checkin': '桌面自动化：窗口、点击、输入与截图',
}

export const PLUGIN_DESCRIPTIONS_EN: Record<string, string> = {
  builtin: 'Built-in core Actions (log, sleep) and Checks (truthy, equals, text contains)',
  dummy: 'Echo test plugin for verifying minimal deterministic workflows',
  openclaw: 'OpenClaw integration: HTTP requests, shell execution, and KnowFlow reporting',
  'ai-deepseek': 'DeepSeek LLM text summarization and insight extraction',
  'zhihu-digest': 'Q&A answer scraping and Markdown draft publishing',
  'desktop-checkin': 'Desktop RPA automation: window focus, mouse click, typing, and screenshot',
}

export function getPluginDescription(pluginName: string): string {
  if (locale.value === 'en') {
    return PLUGIN_DESCRIPTIONS_EN[pluginName] ?? PLUGIN_DESCRIPTIONS[pluginName] ?? ''
  }
  return PLUGIN_DESCRIPTIONS[pluginName] ?? ''
}
