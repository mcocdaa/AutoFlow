export const PLUGIN_DESCRIPTIONS: Record<string, string> = {
  builtin: "核心基础功能集",
  "ai-deepseek": "DeepSeek AI文本处理",
  "ai-openai": "OpenAI模型集成",
  http: "HTTP网络请求功能",
  file: "文件操作功能",
  system: "系统操作功能",
};

export function getPluginDescription(pluginName: string): string {
  return PLUGIN_DESCRIPTIONS[pluginName] || "插件功能描述";
}
