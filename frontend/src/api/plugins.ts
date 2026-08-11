import apiClient from './index'
import type { PluginsResponse } from '../types/plugins'

export async function fetchPlugins(): Promise<PluginsResponse> {
  const { data } = await apiClient.get<PluginsResponse>('/plugins')
  return data
}
