import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'

export default defineConfig({
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
