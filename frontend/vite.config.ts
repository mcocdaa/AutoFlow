import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'

export default defineConfig({
  server: {
    port: 5180,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_URL || 'http://localhost:3003',
        changeOrigin: true,
        rewrite: (path) => path
      }
    }
  },
  plugins: (() => {
    const dockerWeb = process.env.DOCKER_WEB === 'true' || process.env.DOCKER_WEB === '1'
    if (dockerWeb) return [vue()]
    return [
      vue(),
      electron([
        {
          entry: 'electron/main.ts',
        },
      ]),
      renderer(),
    ]
  })(),
})
