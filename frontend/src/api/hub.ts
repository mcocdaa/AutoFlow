import apiClient from './index'
import type {
  HubFlowDetail,
  HubFlowSummary,
  InstallHubFlowRequest,
  InstallHubFlowResponse,
  FetchHubFlowsParams,
} from '../types/hub'

export * from '../types/hub'

/**
 * 获取 Flow Hub 市场流程列表
 */
export async function fetchHubFlows(
  params?: FetchHubFlowsParams,
): Promise<HubFlowSummary[]> {
  const { data } = await apiClient.get<HubFlowSummary[]>('/hub/flows', {
    params: {
      category: params?.category || undefined,
      query: params?.query || undefined,
    },
  })
  return data
}

/**
 * 获取特定 Flow 模板详情（包含完整 YAML 源码）
 */
export async function fetchHubFlowDetail(flowId: string): Promise<HubFlowDetail> {
  const { data } = await apiClient.get<HubFlowDetail>(
    `/hub/flows/${encodeURIComponent(flowId)}`,
  )
  return data
}

/**
 * 一键安装 Hub 流程模板到本地 flows/ 目录
 */
export async function installHubFlow(
  flowId: string,
  overwrite = false,
): Promise<InstallHubFlowResponse> {
  const payload: InstallHubFlowRequest = {
    flow_id: flowId,
    overwrite,
  }
  const { data } = await apiClient.post<InstallHubFlowResponse>(
    '/hub/install',
    payload,
  )
  return data
}
