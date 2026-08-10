import { contextBridge } from 'electron'

const apiBase = process.env.AUTOFLOW_API_URL || 'http://127.0.0.1:3001'

contextBridge.exposeInMainWorld('autoflow', { apiBase })
