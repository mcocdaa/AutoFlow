export interface Plugin {
  name: string
  version: string
}

export interface PluginError {
  plugin_id: string
  file_path: string
  error: string
}

export interface PluginsResponse {
  plugins: Plugin[]
  actions: string[]
  checks: string[]
  errors: PluginError[]
}
