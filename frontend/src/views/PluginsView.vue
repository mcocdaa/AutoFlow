<template>
  <div class="plugins-view">
    <div class="page-header">
      <div class="header-left">
        <AppstoreOutlined class="title-icon" />
        <h2 class="page-title">Installed Plugins</h2>
      </div>
      <div class="header-actions">
        <a-button @click="store.fetchPlugins" :loading="store.loading">
          <template #icon><ReloadOutlined /></template>
          Refresh
        </a-button>
        <a-button type="primary" @click="navigateToRunFlow">
          <template #icon><RightOutlined /></template>
          去创建流程
        </a-button>
      </div>
    </div>

    <a-alert
      v-if="error"
      :message="error"
      type="error"
      style="margin-bottom: 20px"
      show-icon
    />

    <StatsCard
      v-if="store.plugins.length > 0"
      :plugins="store.plugins"
      :actions="store.actions"
      :checks="store.checks"
    />

    <h3 class="section-title">Plugin List</h3>
    <a-row :gutter="24" class="plugins-grid">
      <a-col
        :xs="24"
        :sm="12"
        :md="8"
        :lg="8"
        :xl="8"
        v-for="plugin in store.plugins"
        :key="plugin.name"
      >
        <PluginCard
          :plugin="plugin"
          @configure="showPluginConfig"
          @disable="disablePlugin"
          @view-docs="viewPluginDocs"
        />
      </a-col>
    </a-row>

    <ErrorsSection
      v-if="store.errors && store.errors.length > 0"
      :errors="store.errors"
    />

    <ActionsSection :actions="store.actions" @copy="copyToClipboard" />

    <ChecksSection :checks="store.checks" @copy="copyToClipboard" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { usePluginsStore } from "../stores/plugins";
import {
  AppstoreOutlined,
  ReloadOutlined,
  RightOutlined,
} from "@ant-design/icons-vue";
import { useClipboard } from "../composables/useClipboard";
import StatsCard from "../components/plugins/StatsCard.vue";
import PluginCard from "../components/plugins/PluginCard.vue";
import ActionsSection from "../components/plugins/ActionsSection.vue";
import ChecksSection from "../components/plugins/ChecksSection.vue";
import ErrorsSection from "../components/plugins/ErrorsSection.vue";
import type { Plugin } from "../types/plugins";

const store = usePluginsStore();
const router = useRouter();
const { copyToClipboard } = useClipboard();

const error = computed(() => store.error);

const navigateToRunFlow = () => {
  router.push("/run");
};

const showPluginConfig = (plugin: Plugin) => {
  console.log("Show config for plugin:", plugin.name);
};

const disablePlugin = (plugin: Plugin) => {
  console.log("Disable plugin:", plugin.name);
};

const viewPluginDocs = (plugin: Plugin) => {
  console.log("View docs for plugin:", plugin.name);
};

onMounted(() => {
  store.fetchPlugins();
});
</script>

<style scoped>
.plugins-view {
  max-width: 1400px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-icon {
  font-size: 24px;
  color: var(--flow-color-primary);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--flow-text-title);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--flow-text-title);
  margin: 32px 0 16px 0;
}

.plugins-grid {
  margin-bottom: 24px;
}
</style>
