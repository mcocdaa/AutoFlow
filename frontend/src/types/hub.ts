export interface HubFlowSummary {
  id: string
  name: string
  title: string
  category: string
  author: string
  version: string
  installs: number
  rating: number
  description: string
  tags: string[]
}

export interface HubFlowDetail extends HubFlowSummary {
  yaml: string
}

export interface InstallHubFlowRequest {
  flow_id: string
  overwrite?: boolean
}

export interface InstallHubFlowResponse {
  status: string
  flow_name: string
  path: string
}

export interface FetchHubFlowsParams {
  category?: string
  query?: string
}
