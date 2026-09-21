import apiClient from './index'
import type {
  DeleteSecretResponse,
  SecretItem,
  SetSecretRequest,
  SetSecretResponse,
} from '../types/secrets'

export * from '../types/secrets'

/**
 * 列出保密柜中的所有凭据（已做掩码脱敏）
 */
export async function fetchSecrets(): Promise<SecretItem[]> {
  const { data } = await apiClient.get<SecretItem[]>('/secrets')
  return data
}

/**
 * 录入或更新凭据（明文安全提交至后端 AES-256-GCM 加密存储）
 */
export async function setSecret(
  key: string,
  value: string,
): Promise<SetSecretResponse> {
  const payload: SetSecretRequest = { key, value }
  const { data } = await apiClient.post<SetSecretResponse>('/secrets', payload)
  return data
}

/**
 * 从保密柜中安全删除凭据
 */
export async function deleteSecret(key: string): Promise<DeleteSecretResponse> {
  const { data } = await apiClient.delete<DeleteSecretResponse>(
    `/secrets/${encodeURIComponent(key)}`,
  )
  return data
}
