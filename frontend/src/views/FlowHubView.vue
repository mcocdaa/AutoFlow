<template>
  <div class="af-page flow-hub-page">
    <PageHeader
      :title="t('hub.title')"
      :description="t('hub.desc')"
      :icon="ShopOutlined"
    >
      <template #actions>
        <a-button :loading="loading" @click="loadFlows">
          <template #icon><ReloadOutlined /></template>
          {{ t('common.refresh') }}
        </a-button>
      </template>
    </PageHeader>

    <!-- 顶部市场统计与特性卡片 -->
    <div class="hub-hero-banner">
      <div class="hero-content">
        <div class="hero-pill">
          <RocketOutlined class="hero-pill-icon" />
          <span>{{ t('hub.heroPill') }}</span>
        </div>
        <h2 class="hero-title">{{ t('hub.heroTitle') }}</h2>
        <p class="hero-desc">
          {{ t('hub.heroDesc') }}
        </p>
      </div>
      <div class="hero-stats">
        <div class="stat-card">
          <div class="stat-value">{{ flows.length }}+</div>
          <div class="stat-label">{{ t('hub.stat.templates') }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ totalInstalls.toLocaleString() }}+</div>
          <div class="stat-label">{{ t('hub.stat.installs') }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">100%</div>
          <div class="stat-label">{{ t('hub.stat.checkCoverage') }}</div>
        </div>
      </div>
    </div>

    <!-- 搜索与分类过滤区 -->
    <div class="hub-filter-bar">
      <div class="category-tabs">
        <a-radio-group
          v-model:value="selectedCategoryKey"
          button-style="solid"
          size="middle"
          @change="onCategoryChange"
        >
          <a-radio-button
            v-for="cat in categoryOptions"
            :key="cat.key"
            :value="cat.key"
          >
            {{ cat.label }}
          </a-radio-button>
        </a-radio-group>
      </div>

      <div class="search-box">
        <a-input-search
          v-model:value="searchQuery"
          :placeholder="t('hub.searchPlaceholder')"
          allow-clear
          size="middle"
          @search="onSearch"
          @pressEnter="onSearch"
        />
      </div>
    </div>

    <!-- 流程卡片网格 -->
    <div v-if="loading && flows.length === 0" class="cards-grid">
      <a-card v-for="n in 6" :key="n" class="flow-card skeleton-card">
        <a-skeleton active :paragraph="{ rows: 4 }" />
      </a-card>
    </div>

    <div v-else-if="filteredFlows.length > 0" class="cards-grid">
      <div
        v-for="flow in filteredFlows"
        :key="flow.id"
        class="flow-card-wrapper"
      >
        <a-card class="flow-card" hoverable :body-style="{ padding: '20px' }">
          <!-- 卡片头部：分类标签与评分 -->
          <div class="card-header">
            <a-tag :color="getCategoryColor(flow.category)" class="category-tag">
              <component :is="getCategoryIcon(flow.category)" style="margin-right: 4px;" />
              {{ flow.category }}
            </a-tag>
            <div class="rating-badge">
              <StarFilled class="star-icon" />
              <span class="rating-number">{{ flow.rating.toFixed(1) }}</span>
            </div>
          </div>

          <!-- 卡片主内容：标题、标识、描述 -->
          <div class="card-main">
            <h3 class="flow-title" :title="flow.title">{{ flow.title }}</h3>
            <div class="flow-name-row">
              <code class="flow-id-chip">{{ flow.name }}</code>
              <span class="flow-version">v{{ flow.version }}</span>
            </div>
            <p class="flow-description" :title="flow.description">
              {{ flow.description }}
            </p>
          </div>

          <!-- 标签展示 -->
          <div class="card-tags">
            <a-tag
              v-for="tag in flow.tags"
              :key="tag"
              class="meta-tag"
            >
              #{{ tag }}
            </a-tag>
          </div>

          <!-- 底部元信息：作者与安装量 -->
          <div class="card-meta-bar">
            <div class="author-info">
              <UserOutlined class="meta-icon" />
              <span>{{ flow.author }}</span>
            </div>
            <div class="installs-info">
              <DownloadOutlined class="meta-icon" />
              <span>{{ t('hub.installsCount', { count: flow.installs.toLocaleString() }) }}</span>
            </div>
          </div>

          <!-- 操作动作栏 -->
          <div class="card-actions">
            <a-button
              size="small"
              class="action-btn"
              @click="openYamlModal(flow)"
            >
              <template #icon><FileTextOutlined /></template>
              {{ t('hub.viewYaml') }}
            </a-button>
            <a-button
              size="small"
              class="action-btn"
              :loading="installingFlowId === flow.id"
              @click="handleInstall(flow)"
            >
              <template #icon><DownloadOutlined /></template>
              {{ t('hub.install') }}
            </a-button>
            <a-button
              type="primary"
              size="small"
              class="action-btn primary-action"
              :loading="loadingCanvasId === flow.id"
              @click="handleOpenInCanvas(flow)"
            >
              <template #icon><ApartmentOutlined /></template>
              {{ t('hub.openInCanvas') }}
            </a-button>
          </div>
        </a-card>
      </div>
    </div>

    <!-- 空结果状态 -->
    <a-card v-else class="empty-state-card">
      <a-empty
        :description="t('hub.emptyDesc')"
        :image="emptyImage"
      >
        <template #extra>
          <a-button @click="resetFilters">{{ t('hub.resetFilters') }}</a-button>
        </template>
      </a-empty>
    </a-card>

    <!-- YAML 源码预览弹窗 -->
    <a-modal
      v-model:open="yamlModalVisible"
      :title="null"
      :footer="null"
      width="820px"
      wrap-class-name="yaml-preview-modal"
      centered
    >
      <div class="modal-custom-header">
        <div class="modal-title-row">
          <span class="modal-header-icon"><FileTextOutlined /></span>
          <div>
            <h3 class="modal-title">{{ activeFlow?.title }}</h3>
            <span class="modal-subtitle">{{ t('hub.modal.yamlSubtitle', { name: activeFlow?.name ?? '' }) }}</span>
          </div>
        </div>
        <div class="modal-header-actions">
          <a-button size="small" @click="copyActiveYaml">
            <template #icon><CopyOutlined /></template>
            {{ t('hub.modal.copyCode') }}
          </a-button>
        </div>
      </div>

      <div class="yaml-modal-body">
        <CodeEditor
          :model-value="activeYamlContent"
          :min-height="400"
          language="yaml"
        />
      </div>

      <div class="modal-custom-footer">
        <a-button @click="yamlModalVisible = false">{{ t('common.close') }}</a-button>
        <div class="footer-right-actions">
          <a-button
            :loading="activeFlow ? installingFlowId === activeFlow.id : false"
            @click="activeFlow && handleInstall(activeFlow)"
          >
            <template #icon><DownloadOutlined /></template>
            {{ t('hub.install') }}
          </a-button>
          <a-button
            type="primary"
            :loading="activeFlow ? loadingCanvasId === activeFlow.id : false"
            @click="activeFlow && handleOpenInCanvas(activeFlow)"
          >
            <template #icon><ApartmentOutlined /></template>
            {{ t('hub.modal.openInCanvasFull') }}
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Empty, Modal, message } from 'ant-design-vue'
import {
  ApiOutlined,
  ApartmentOutlined,
  CopyOutlined,
  DownloadOutlined,
  FileTextOutlined,
  ReloadOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  ShopOutlined,
  StarFilled,
  SyncOutlined,
  UserOutlined,
} from '@ant-design/icons-vue'
import PageHeader from '../components/shared/PageHeader.vue'
import CodeEditor from '../components/shared/CodeEditor.vue'
import { useClipboard } from '../composables/useClipboard'
import { HUB_FLOW_I18N, localizeFlowYaml, useI18n } from '../i18n'
import {
  fetchHubFlowDetail,
  fetchHubFlows,
  installHubFlow,
  type HubFlowDetail,
  type HubFlowSummary,
} from '../api/hub'

const { locale, t } = useI18n()
const router = useRouter()
const { copyToClipboard } = useClipboard()

const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE

// 状态
const loading = ref(false)
const flows = ref<HubFlowSummary[]>([])
const selectedCategoryKey = ref('all')
const searchQuery = ref('')
const installingFlowId = ref<string | null>(null)
const loadingCanvasId = ref<string | null>(null)

// 模态框状态
const yamlModalVisible = ref(false)
const activeFlow = ref<HubFlowSummary | null>(null)
const activeYamlContent = ref('')

// 分类选项
const categoryOptions = computed(() => [
  { key: 'all', label: t('hub.cat.all'), backendCategory: undefined },
  { key: 'sre', label: t('hub.cat.sre'), backendCategory: 'SRE / 运维自愈' },
  { key: 'digest', label: t('hub.cat.digest'), backendCategory: '自动化数据采集' },
  { key: 'agent', label: t('hub.cat.agent'), backendCategory: '质量门禁' },
  { key: 'rpa', label: t('hub.cat.rpa'), backendCategory: '桌面 RPA' },
])

function localizeHubFlow(flow: HubFlowSummary): HubFlowSummary {
  if (locale.value === 'en' && HUB_FLOW_I18N[flow.id]?.en) {
    return {
      ...flow,
      ...HUB_FLOW_I18N[flow.id].en,
    }
  }
  const orig = flows.value.find((f) => f.id === flow.id)
  return orig ? { ...orig } : flow
}

// 累计安装量计算
const totalInstalls = computed(() => {
  return flows.value.reduce((acc, curr) => acc + (curr.installs || 0), 0)
})

// 分类与关键词过滤后的列表
const filteredFlows = computed(() => {
  let result = flows.value

  // 分类匹配
  if (selectedCategoryKey.value !== 'all') {
    const matchedOption = categoryOptions.value.find((c) => c.key === selectedCategoryKey.value)
    if (matchedOption?.backendCategory) {
      const targetCat = matchedOption.backendCategory.toLowerCase()
      result = result.filter(
        (f) =>
          f.category.toLowerCase() === targetCat ||
          f.category.toLowerCase().includes(targetCat) ||
          targetCat.includes(f.category.toLowerCase()),
      )
    }
  }

  const localized = result.map(localizeHubFlow)

  // 搜索关键词匹配
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    return localized.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        f.name.toLowerCase().includes(q) ||
        f.description.toLowerCase().includes(q) ||
        f.tags.some((tag) => tag.toLowerCase().includes(q)),
    )
  }

  return localized
})

// 加载流程市场列表
const loadFlows = async () => {
  loading.value = true
  try {
    const list = await fetchHubFlows()
    flows.value = list
  } catch (err: any) {
    message.error(err?.message || t('hub.msg.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const onCategoryChange = () => {
  // 本地过滤即时响应
}

const onSearch = () => {
  // 本地过滤即时响应
}

const resetFilters = () => {
  selectedCategoryKey.value = 'all'
  searchQuery.value = ''
}

// 分类标签色彩与图标助手
const getCategoryColor = (category: string): string => {
  if (category.includes('SRE') || category.includes('运维')) return 'blue'
  if (category.includes('采集') || category.includes('研报') || category.includes('Scraping')) return 'purple'
  if (category.includes('质量') || category.includes('Quality') || category.includes('Agent')) return 'green'
  if (category.includes('RPA')) return 'orange'
  return 'default'
}

const getCategoryIcon = (category: string) => {
  if (category.includes('SRE') || category.includes('运维')) return SafetyCertificateOutlined
  if (category.includes('采集') || category.includes('研报') || category.includes('Scraping')) return SyncOutlined
  if (category.includes('质量') || category.includes('Quality') || category.includes('Agent')) return ApiOutlined
  if (category.includes('RPA')) return RocketOutlined
  return ShopOutlined
}

const localizeHubYaml = (rawYaml: string, flowId: string): string => {
  let out = localizeFlowYaml(rawYaml, locale.value)
  if (locale.value === 'en') {
    const metaEn = HUB_FLOW_I18N[flowId]?.en
    if (metaEn?.description) {
      out = out.replace(/^description:\s*.*$/m, `description: "${metaEn.description}"`)
    }
  }
  return out
}

watch(locale, (newLoc) => {
  message.destroy()
  if (activeFlow.value) {
    activeFlow.value = localizeHubFlow(activeFlow.value)
  }
  if (activeYamlContent.value && !activeYamlContent.value.startsWith('#')) {
    activeYamlContent.value = localizeFlowYaml(activeYamlContent.value, newLoc)
  }
})

// 打开 YAML 预览弹窗
const openYamlModal = async (flow: HubFlowSummary) => {
  activeFlow.value = flow
  activeYamlContent.value = t('hub.msg.fetchingYaml')
  yamlModalVisible.value = true

  try {
    const detail: HubFlowDetail = await fetchHubFlowDetail(flow.id)
    activeYamlContent.value = localizeHubYaml(detail.yaml, flow.id)
  } catch (err: any) {
    activeYamlContent.value = t('hub.msg.yamlErrorPrefix', {
      msg: err?.message || t('hub.msg.networkError'),
    })
    message.error(t('hub.msg.fetchYamlFailed'))
  }
}

const copyActiveYaml = () => {
  if (activeYamlContent.value) {
    copyToClipboard(activeYamlContent.value)
  }
}

// 一键安装流程
const handleInstall = async (flow: HubFlowSummary, overwrite = false) => {
  installingFlowId.value = flow.id
  try {
    await installHubFlow(flow.id, overwrite)
    message.success({
      content: t('hub.msg.installSuccess', { title: flow.title }),
      duration: 3,
    })
    if (yamlModalVisible.value) {
      yamlModalVisible.value = false
    }
  } catch (err: any) {
    const errorMsg = err?.message || ''
    // 冲突处理：文件已存在
    if (errorMsg.includes('already exists') || err?.response?.status === 409) {
      Modal.confirm({
        title: t('hub.msg.existsTitle'),
        content: t('hub.msg.existsContent', { title: flow.title }),
        okText: t('hub.msg.confirmOverwrite'),
        okType: 'danger',
        cancelText: t('common.cancel'),
        onOk: async () => {
          await handleInstall(flow, true)
        },
      })
    } else {
      message.error(errorMsg || t('hub.msg.installFailed'))
    }
  } finally {
    installingFlowId.value = null
  }
}

// 在编排画布中打开
const handleOpenInCanvas = async (flow: HubFlowSummary) => {
  loadingCanvasId.value = flow.id
  try {
    let yamlCode = ''
    if (activeFlow.value?.id === flow.id && activeYamlContent.value && !activeYamlContent.value.startsWith('#')) {
      yamlCode = activeYamlContent.value
    } else {
      const detail = await fetchHubFlowDetail(flow.id)
      yamlCode = localizeHubYaml(detail.yaml, flow.id)
    }

    // 存储至 sessionStorage 供画布生命周期读取
    sessionStorage.setItem('autoflow_canvas_yaml', yamlCode)
    message.success(t('hub.msg.loadedToCanvas', { title: flow.title }))

    if (yamlModalVisible.value) {
      yamlModalVisible.value = false
    }

    router.push({
      path: '/canvas',
      state: { flowYaml: yamlCode },
    })
  } catch (err: any) {
    message.error(err?.message || t('hub.msg.loadCanvasFailed'))
  } finally {
    loadingCanvasId.value = null
  }
}

onMounted(() => {
  loadFlows()
})
</script>

<style scoped>
.flow-hub-page {
  padding-bottom: 40px;
}

/* 顶部 Banner 区 */
.hub-hero-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  padding: 24px 32px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
  border-radius: var(--flow-border-radius-lg);
  color: #FFFFFF;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
}

.hero-content {
  max-width: 650px;
}

.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  margin-bottom: 12px;
  background: rgba(37, 99, 235, 0.25);
  border: 1px solid rgba(59, 130, 246, 0.4);
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  color: #93C5FD;
}

.hero-pill-icon {
  color: #60A5FA;
}

.hero-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  color: #F8FAFC;
  letter-spacing: -0.3px;
}

.hero-desc {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.6;
  color: #94A3B8;
}

.hero-stats {
  display: flex;
  gap: 16px;
  flex: none;
}

.stat-card {
  min-width: 110px;
  padding: 12px 18px;
  text-align: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  backdrop-filter: blur(4px);
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #38BDF8;
  font-family: var(--flow-font-mono);
}

.stat-label {
  margin-top: 4px;
  font-size: 11.5px;
  color: #94A3B8;
}

/* 过滤栏 */
.hub-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  row-gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.category-tabs {
  flex-shrink: 0;
  white-space: nowrap;
}

.category-tabs :deep(.ant-radio-button-wrapper) {
  white-space: nowrap;
}

.search-box {
  width: 260px;
  flex: 0 1 280px;
}

/* 卡片网格 */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 20px;
}

.flow-card-wrapper {
  display: flex;
}

.flow-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  border-radius: var(--flow-border-radius-lg);
  border: 1px solid var(--flow-border-color);
  background: var(--flow-bg-card);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: var(--flow-shadow-light);
}

.flow-card:hover {
  border-color: #93C5FD;
  transform: translateY(-3px);
  box-shadow: 0 12px 24px -8px rgba(37, 99, 235, 0.12);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.category-tag {
  font-weight: 500;
  border-radius: 6px;
  padding: 2px 10px;
}

.rating-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  color: #D97706;
}

.star-icon {
  font-size: 11px;
  color: #F59E0B;
}

.card-main {
  flex: 1;
  margin-bottom: 14px;
}

.flow-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 650;
  line-height: 1.4;
  color: var(--flow-text-title);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.flow-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.flow-id-chip {
  padding: 2px 6px;
  background: #F1F5F9;
  border-radius: 4px;
  font-family: var(--flow-font-mono);
  font-size: 11px;
  color: #475569;
}

.flow-version {
  font-size: 11.5px;
  color: var(--flow-text-disabled);
}

.flow-description {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--flow-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 40px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
  min-height: 26px;
}

.meta-tag {
  margin: 0;
  padding: 0 7px;
  font-size: 11px;
  border-radius: 4px;
  background: #F8FAFC;
  border-color: #E2E8F0;
  color: #64748B;
}

.card-meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  margin-bottom: 16px;
  border-top: 1px solid var(--flow-border-color-soft);
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.author-info,
.installs-info {
  display: flex;
  align-items: center;
  gap: 5px;
}

.meta-icon {
  font-size: 12px;
  color: var(--flow-text-disabled);
}

.card-actions {
  display: grid;
  grid-template-columns: 1fr 1fr 1.25fr;
  gap: 8px;
}

.action-btn {
  font-size: 12px;
  border-radius: 6px;
  padding: 0 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

.primary-action {
  font-weight: 500;
}

/* 空状态卡片 */
.empty-state-card {
  padding: 60px 0;
  text-align: center;
  border-radius: var(--flow-border-radius-lg);
}

/* 模态框自定义头部与底部 */
.modal-custom-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--flow-border-color);
}

.modal-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  font-size: 18px;
  border-radius: 8px;
  background: var(--flow-color-primary-soft);
  color: var(--flow-color-primary);
}

.modal-title {
  margin: 0;
  font-size: 16px;
  font-weight: 650;
  color: var(--flow-text-title);
}

.modal-subtitle {
  font-size: 12px;
  color: var(--flow-text-secondary);
}

.modal-custom-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--flow-border-color);
}

.footer-right-actions {
  display: flex;
  gap: 10px;
}

/* YAML Modal Body */
.yaml-modal-body {
  border-radius: 8px;
  overflow: hidden;
}
</style>
