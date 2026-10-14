import apiClient from './index'
import type { FlowRecord } from '../types/flow'
import type {
  PluginCatalogItem,
  PluginCatalogResponse,
  PluginsResponse,
} from '../types/plugins'

export type { FlowRecord, PluginCatalogItem, PluginCatalogResponse, PluginsResponse }

export async function listFlows(): Promise<FlowRecord[]> {
  const { data } = await apiClient.get<FlowRecord[]>('/flows')
  return data
}

export async function getFlow(slug: string): Promise<FlowRecord> {
  const { data } = await apiClient.get<FlowRecord>(
    `/flows/${encodeURIComponent(slug)}`,
  )
  return data
}

export async function saveFlow(
  slug: string,
  flowYaml: string,
): Promise<FlowRecord> {
  const { data } = await apiClient.put<FlowRecord>(
    `/flows/${encodeURIComponent(slug)}`,
    {
      slug,
      flow_yaml: flowYaml,
    },
  )
  return data
}

export async function deleteFlow(
  slug: string,
): Promise<{ status: string; slug: string }> {
  const { data } = await apiClient.delete<{ status: string; slug: string }>(
    `/flows/${encodeURIComponent(slug)}`,
  )
  return data
}

export async function getPluginCatalog(): Promise<PluginCatalogResponse> {
  const { data } = await apiClient.get<PluginCatalogResponse>('/plugins/catalog')
  return data
}

export default apiClient
