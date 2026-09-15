export const PLUGIN_DESCRIPTIONS: Record<string, string> = {
  builtin: '内置通用 Action（日志、等待）与 Check（文本包含等）',
  dummy: '回显测试插件，用于验证最小流程',
  openclaw: 'OpenClaw 集成：HTTP 请求、命令执行与记录上报',
  'ai-deepseek': 'DeepSeek 文本总结',
  'zhihu-digest': '知乎回答抓取与摘要草稿',
  'desktop-checkin': '桌面自动化：窗口、点击、输入与截图',
}

export function getPluginDescription(pluginName: string): string {
  return PLUGIN_DESCRIPTIONS[pluginName] ?? ''
}
