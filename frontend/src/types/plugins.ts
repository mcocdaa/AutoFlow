export interface Plugin {
  name: string
  version: string
  [key: string]: any
}

export interface PluginError {
  plugin_id: string
  file_path: string
  error: string
}

export interface PluginsState {
  plugins: Plugin[]
  actions: string[]
  checks: string[]
  errors: PluginError[]
  loading: boolean
  error: string | null
}
