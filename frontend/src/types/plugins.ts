export interface Plugin {
  name: string
  version: string
}

export interface PluginError {
  plugin_id: string
  file_path: string
  error: string
}

export interface PluginCatalogItem {
  type: string
  label: string
  desc: string
  icon: string
  category: string
  kind: 'action' | 'check'
  defaultParams?: Record<string, unknown>
}

export interface PluginsResponse {
  plugins: Plugin[]
  actions: string[]
  checks: string[]
  errors: PluginError[]
  catalog?: PluginCatalogItem[]
}

export type PluginCatalogResponse = PluginsResponse
