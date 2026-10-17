<template>
  <a-config-provider :theme="FDS_THEME" :locale="locale === 'zh' ? zhCN : enUS">
    <a-layout class="app-shell">
      <a-layout-header class="app-header">
        <div class="header-logo" @click="goHome">
          <svg class="logo-mark" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">
            <defs>
              <linearGradient id="autoflow-logo-gradient" x1="0" y1="0" x2="32" y2="32">
                <stop offset="0%" stop-color="#2563EB" />
                <stop offset="100%" stop-color="#10B981" />
              </linearGradient>
            </defs>
            <rect x="0" y="0" width="32" height="32" rx="9" fill="url(#autoflow-logo-gradient)" />
            <circle cx="10.5" cy="16" r="3" fill="#FFFFFF" />
            <circle cx="21.5" cy="10" r="2.4" fill="#FFFFFF" fill-opacity="0.86" />
            <circle cx="21.5" cy="22" r="2.4" fill="#FFFFFF" fill-opacity="0.86" />
            <path d="M13.2 15 L18.4 11.2" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" />
            <path d="M13.2 17 L18.4 20.8" stroke="#FFFFFF" stroke-width="1.6" stroke-linecap="round" />
          </svg>
          <div class="logo-text">
            <span class="logo-title">AutoFlow</span>
            <span class="logo-subtitle">{{ t('app.subtitle') }}</span>
          </div>
        </div>
        <div class="header-actions">
          <button
            type="button"
            class="lang-toggle-btn"
            data-testid="lang-toggle-btn"
            @click="toggleLocale"
          >
            {{ locale === 'zh' ? '🌐 EN' : '🌐 中文' }}
          </button>
          <a-button type="primary" class="new-flow-btn" @click="navigateToRunFlow">
            <template #icon><PlusOutlined /></template>
            {{ t('app.newFlow') }}
          </a-button>
        </div>
      </a-layout-header>

      <a-layout class="app-body">
        <a-layout-sider
          v-model:collapsed="collapsed"
          class="app-sider"
          theme="light"
          :width="232"
          :collapsed-width="64"
          collapsible
          breakpoint="lg"
          :trigger="null"
        >
          <a-menu v-model:selectedKeys="selectedKeys" mode="inline" class="app-menu">
            <a-menu-item key="/canvas" @click="router.push('/canvas')">
              <template #icon><ApartmentOutlined /></template>
              <span>{{ t('nav.canvas') }}</span>
            </a-menu-item>
            <a-menu-item key="/hub" @click="router.push('/hub')">
              <template #icon><ShopOutlined /></template>
              <span>{{ t('nav.hub') }}</span>
            </a-menu-item>
            <a-menu-item key="/run" @click="router.push('/run')">
              <template #icon><PlayCircleOutlined /></template>
              <span>{{ t('nav.run') }}</span>
            </a-menu-item>
            <a-menu-item key="/debug" @click="router.push('/debug')">
              <template #icon><BugOutlined /></template>
              <span>{{ t('nav.debug') }}</span>
            </a-menu-item>
            <a-menu-item key="/runs" @click="router.push('/runs')">
              <template #icon><HistoryOutlined /></template>
              <span>{{ t('nav.runs') }}</span>
            </a-menu-item>
            <a-menu-item key="/plugins" @click="router.push('/plugins')">
              <template #icon><AppstoreOutlined /></template>
              <span>{{ t('nav.plugins') }}</span>
            </a-menu-item>
            <a-menu-item key="/secrets" @click="router.push('/secrets')">
              <template #icon><KeyOutlined /></template>
              <span>{{ t('nav.secrets') }}</span>
            </a-menu-item>
          </a-menu>
          <div class="sider-footer">
            <a-button type="text" class="collapse-trigger" @click="collapsed = !collapsed">
              <template #icon>
                <MenuUnfoldOutlined v-if="collapsed" />
                <MenuFoldOutlined v-else />
              </template>
            </a-button>
          </div>
        </a-layout-sider>

        <a-layout-content class="app-content">
          <router-view></router-view>
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-config-provider>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import enUS from 'ant-design-vue/es/locale/en_US'
import {
  ApartmentOutlined,
  AppstoreOutlined,
  BugOutlined,
  HistoryOutlined,
  KeyOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ShopOutlined,
} from '@ant-design/icons-vue'
import { FDS_THEME } from './theme/flow-design-theme'
import { useI18n } from './i18n'

const { locale, toggleLocale, t } = useI18n()
const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const selectedKeys = ref<string[]>([route.path])

watch(() => route.path, (path) => {
  selectedKeys.value = [path]
}, { immediate: true })

const goHome = () => {
  router.push('/canvas')
}

const navigateToRunFlow = () => {
  router.push('/canvas')
}
</script>

<style scoped>
.app-shell {
  height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--flow-header-height);
  padding: 0 24px;
  background: var(--flow-bg-card);
  border-bottom: 1px solid var(--flow-border-color);
}

.header-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.logo-mark {
  display: block;
  flex: none;
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}

.logo-title {
  font-size: 17px;
  font-weight: 650;
  letter-spacing: 0.2px;
  color: var(--flow-text-title);
}

.logo-subtitle {
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.lang-toggle-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 32px;
  padding: 0 12px;
  border-radius: 9999px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #1e293b;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  flex-shrink: 0;
  cursor: pointer;
  transition: all 0.2s ease;
}

.lang-toggle-btn:hover {
  border-color: #2563eb;
  background: #eff6ff;
  color: #2563eb;
}

.new-flow-btn {
  white-space: nowrap;
  flex-shrink: 0;
}

.app-body {
  min-height: 0;
}

.app-sider {
  position: relative;
  background: var(--flow-bg-sider);
  border-right: 1px solid var(--flow-border-color);
}

.app-menu {
  padding-top: 12px;
  border-inline-end: none !important;
}

.sider-footer {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  display: flex;
  justify-content: flex-end;
  padding: 12px;
  border-top: 1px solid var(--flow-border-color-soft);
}

.app-sider.ant-layout-sider-collapsed .sider-footer {
  justify-content: center;
}

.collapse-trigger {
  color: var(--flow-text-secondary);
}

.app-content {
  padding: 24px;
  overflow: auto;
  background: var(--flow-bg-page);
}
</style>
