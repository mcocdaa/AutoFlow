import apiClient from './index'
import type { PluginCatalogResponse, PluginsResponse } from '../types/plugins'

export async function fetchPlugins(): Promise<PluginsResponse> {
  const { data } = await apiClient.get<PluginsResponse>('/plugins')
  return data
}

export async function getPluginCatalog(): Promise<PluginCatalogResponse> {
  const { data } = await apiClient.get<PluginCatalogResponse>('/plugins/catalog')
  return data
}
