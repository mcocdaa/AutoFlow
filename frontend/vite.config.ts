import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import electron from "vite-plugin-electron";
import renderer from "vite-plugin-electron-renderer";
import path from "path";

export default defineConfig(({ mode }) => {
  const envDir = path.resolve(__dirname, "..");
  const env = loadEnv(mode, envDir, "");

  const apiVersion = env.API_VERSION;
  const viteApiUrl = env.VITE_API_URL;
  const viteApiProxyUrl = env.VITE_API_PROXY_URL;
  const frontendDevPort = Number(env.FRONTEND_DEV_PORT);

  return {
    envDir,
    server: {
      port: frontendDevPort,
      proxy: {
        "/api": {
          target: viteApiProxyUrl || viteApiUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, `/${apiVersion}`),
        },
      },
    },
    plugins: (() => {
      const dockerWeb =
        env.DOCKER_WEB === "true" || env.DOCKER_WEB === "1";
      if (dockerWeb) return [vue()];
      return [
        vue(),
        electron([
          {
            entry: "src/electron/main.ts",
          },
        ]),
        renderer(),
      ];
    })(),
  };
});
