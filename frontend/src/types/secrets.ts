export interface SecretItem {
  key: string
  masked_value: string
}

export interface SetSecretRequest {
  key: string
  value: string
}

export interface SetSecretResponse {
  status: string
  key: string
}

export interface DeleteSecretResponse {
  status: string
  deleted: boolean
}
