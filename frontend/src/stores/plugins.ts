import { defineStore } from "pinia";
import apiClient from "../api";

export const usePluginsStore = defineStore("plugins", {
  state: () => ({
    plugins: [] as any[],
    actions: [] as string[],
    checks: [] as string[],
    errors: [] as any[],
    loading: false,
    error: null as string | null,
  }),
  actions: {
    async fetchPlugins() {
      this.loading = true;
      this.error = null;
      try {
        const response = await apiClient.get("/plugins");
        this.plugins = response.data.plugins || [];
        this.actions = response.data.actions || [];
        this.checks = response.data.checks || [];
        this.errors = response.data.errors || [];
      } catch (error: any) {
        this.error = error.message;
        console.error("Failed to fetch plugins:", error);
      } finally {
        this.loading = false;
      }
    },
  },
});
