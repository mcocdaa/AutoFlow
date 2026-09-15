<template>
  <div class="af-page">
    <PageHeader
      title="插件管理"
      description="查看已加载的插件与可用的 Action / Check"
      :icon="AppstoreOutlined"
    >
      <template #actions>
        <a-button :loading="store.loading" @click="refresh">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button type="primary" @click="navigateToRunFlow">
          <template #icon><PlayCircleOutlined /></template>
          去运行流程
        </a-button>
      </template>
    </PageHeader>

    <a-alert v-if="error" :message="error" type="error" show-icon class="page-alert" />

    <StatsCard
      v-if="store.plugins.length > 0"
      :plugins="store.plugins"
      :actions="store.actions"
      :checks="store.checks"
    />

    <h3 class="af-section-title">已安装插件</h3>
    <a-row v-if="store.loading && store.plugins.length === 0" :gutter="[24, 24]">
      <a-col v-for="n in 3" :key="n" :xs="24" :sm="12" :lg="8">
        <a-card><a-skeleton active :paragraph="{ rows: 3 }" /></a-card>
      </a-col>
    </a-row>
    <a-row v-else-if="store.plugins.length > 0" :gutter="[24, 24]">
      <a-col
        v-for="plugin in store.plugins"
        :key="plugin.name"
        :xs="24"
        :sm="12"
        :lg="8"
      >
        <PluginCard :plugin="plugin" />
      </a-col>
    </a-row>
    <a-card v-else>
      <a-empty description="未加载任何插件" :image="emptyImage" />
    </a-card>

    <ErrorsSection v-if="store.errors.length > 0" :errors="store.errors" />

    <TagSection
      title="已注册 Action"
      :icon="ThunderboltOutlined"
      :items="store.actions"
      tag-color="blue"
      search-placeholder="搜索 Action"
      @copy="copyToClipboard"
    />

    <TagSection
      title="已注册 Check"
      :icon="CheckCircleOutlined"
      :items="store.checks"
      tag-color="orange"
      search-placeholder="搜索 Check"
      @copy="copyToClipboard"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Empty } from 'ant-design-vue'
import {
  AppstoreOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import { usePluginsStore } from '../stores/plugins'
import { useClipboard } from '../composables/useClipboard'
import PageHeader from '../components/shared/PageHeader.vue'
import StatsCard from '../components/plugins/StatsCard.vue'
import PluginCard from '../components/plugins/PluginCard.vue'
import ErrorsSection from '../components/plugins/ErrorsSection.vue'
import TagSection from '../components/shared/TagSection.vue'

const store = usePluginsStore()
const router = useRouter()
const { copyToClipboard } = useClipboard()

const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE
const error = computed(() => store.error)

const refresh = () => {
  store.fetchPlugins().catch(() => {})
}

const navigateToRunFlow = () => {
  router.push('/run')
}

onMounted(refresh)
</script>

<style scoped>
.page-alert {
  margin-bottom: 24px;
}
</style>
