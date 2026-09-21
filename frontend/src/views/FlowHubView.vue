<template>
  <div class="af-page flow-hub-page">
    <PageHeader
      title="Flow Hub 流程市场"
      description="精选生产级自动化流程模板，支持一键安装、画布可视化加载与外部 Agent (Claude Code / Cursor / OpenClaw) MCP 协同"
      :icon="ShopOutlined"
    >
      <template #actions>
        <a-button type="primary" ghost @click="agentGuideVisible = true">
          <template #icon><ApiOutlined /></template>
          Agent 接入指南
        </a-button>
        <a-button :loading="loading" @click="loadFlows">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </template>
    </PageHeader>

    <!-- 顶部市场统计与特性卡片 -->
    <div class="hub-hero-banner">
      <div class="hero-content">
        <div class="hero-pill">
          <RocketOutlined class="hero-pill-icon" />
          <span>AutoFlow Ecosystem v1.1 Curated Marketplace</span>
        </div>
        <h2 class="hero-title">高可靠确定性工作流集市</h2>
        <p class="hero-desc">
          所有模板均内置 Check 断言校验与自动重试策略。支持本地直接执行，或作为复合 MCP Tool 供 LLM Agent 单次调度。
        </p>
      </div>
      <div class="hero-stats">
        <div class="stat-card">
          <div class="stat-value">{{ flows.length }}+</div>
          <div class="stat-label">精选流程模板</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ totalInstalls.toLocaleString() }}+</div>
          <div class="stat-label">社区累计部署</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">100%</div>
          <div class="stat-label">Check 校验覆盖</div>
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
            v-for="cat in CATEGORY_OPTIONS"
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
          placeholder="搜索流程标题、名称、说明或标签..."
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
              <span>{{ flow.installs.toLocaleString() }} 安装</span>
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
              查看 YAML
            </a-button>
            <a-button
              size="small"
              class="action-btn"
              :loading="installingFlowId === flow.id"
              @click="handleInstall(flow)"
            >
              <template #icon><DownloadOutlined /></template>
              一键安装
            </a-button>
            <a-button
              type="primary"
              size="small"
              class="action-btn primary-action"
              :loading="loadingCanvasId === flow.id"
              @click="handleOpenInCanvas(flow)"
            >
              <template #icon><ApartmentOutlined /></template>
              在画布打开
            </a-button>
          </div>
        </a-card>
      </div>
    </div>

    <!-- 空结果状态 -->
    <a-card v-else class="empty-state-card">
      <a-empty
        description="未找到符合条件的流程模板"
        :image="emptyImage"
      >
        <template #extra>
          <a-button @click="resetFilters">重置筛选条件</a-button>
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
            <span class="modal-subtitle">源码预览: {{ activeFlow?.name }}.flow.yaml</span>
          </div>
        </div>
        <div class="modal-header-actions">
          <a-button size="small" @click="copyActiveYaml">
            <template #icon><CopyOutlined /></template>
            复制代码
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
        <a-button @click="yamlModalVisible = false">关闭</a-button>
        <div class="footer-right-actions">
          <a-button
            :loading="activeFlow ? installingFlowId === activeFlow.id : false"
            @click="activeFlow && handleInstall(activeFlow)"
          >
            <template #icon><DownloadOutlined /></template>
            一键安装
          </a-button>
          <a-button
            type="primary"
            :loading="activeFlow ? loadingCanvasId === activeFlow.id : false"
            @click="activeFlow && handleOpenInCanvas(activeFlow)"
          >
            <template #icon><ApartmentOutlined /></template>
            在编排画布中打开
          </a-button>
        </div>
      </div>
    </a-modal>

    <!-- Agent 接入指南弹窗 -->
    <a-modal
      v-model:open="agentGuideVisible"
      :title="null"
      :footer="null"
      width="860px"
      wrap-class-name="agent-guide-modal"
      centered
    >
      <div class="modal-custom-header">
        <div class="modal-title-row">
          <span class="modal-header-icon guide-icon"><ApiOutlined /></span>
          <div>
            <h3 class="modal-title">Agent 接入指南 (MCP 协议)</h3>
            <span class="modal-subtitle">
              外部 Agent (Claude Code / Cursor / OpenClaw) 通过单次 ToolCall 调度 AutoFlow 确定性流程
            </span>
          </div>
        </div>
      </div>

      <div class="guide-modal-content">
        <div class="guide-intro-banner">
          <div class="banner-badge">Streamable HTTP MCP</div>
          <p>
            AutoFlow 后端内置 Model Context Protocol (MCP) 服务，端点位于
            <code>http://127.0.0.1:8000/mcp</code>。外部 Agent 可自动发现并调用
            <code>search_flow_hub</code>, <code>get_flow</code>, <code>validate_flow</code>, <code>time_travel_run</code> 等增强工具。
          </p>
        </div>

        <a-tabs v-model:activeKey="activeAgentTab" type="card" class="guide-tabs">
          <!-- Claude Code -->
          <a-tab-pane key="claude" tab="Claude Code">
            <div class="guide-tab-panel">
              <div class="step-item">
                <div class="step-num">1</div>
                <div class="step-detail">
                  <div class="step-title">终端 CLI 一键添加 MCP Server</div>
                  <p class="step-desc">在任意项目终端运行以下命令，Claude Code 将自动注册 AutoFlow 工具：</p>
                  <div class="code-block-wrapper">
                    <pre><code>{{ CLAUDE_CLI_COMMAND }}</code></pre>
                    <a-button
                      size="small"
                      type="text"
                      class="copy-code-btn"
                      @click="copyToClipboard(CLAUDE_CLI_COMMAND)"
                    >
                      <CopyOutlined /> 复制
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="step-item">
                <div class="step-num">2</div>
                <div class="step-detail">
                  <div class="step-title">或通过配置文件注册 (~/.claude/config.json)</div>
                  <p class="step-desc">在 mcpServers 配置节添加 AutoFlow HTTP 端点：</p>
                  <div class="code-block-wrapper">
                    <pre><code>{{ CLAUDE_CONFIG_JSON }}</code></pre>
                    <a-button
                      size="small"
                      type="text"
                      class="copy-code-btn"
                      @click="copyToClipboard(CLAUDE_CONFIG_JSON)"
                    >
                      <CopyOutlined /> 复制
                    </a-button>
                  </div>
                </div>
              </div>
            </div>
          </a-tab-pane>

          <!-- Cursor -->
          <a-tab-pane key="cursor" tab="Cursor IDE">
            <div class="guide-tab-panel">
              <div class="step-item">
                <div class="step-num">1</div>
                <div class="step-detail">
                  <div class="step-title">项目级 MCP 配置 (.cursor/mcp.json)</div>
                  <p class="step-desc">在工作区根目录创建或编辑 <code>.cursor/mcp.json</code>：</p>
                  <div class="code-block-wrapper">
                    <pre><code>{{ CURSOR_CONFIG_JSON }}</code></pre>
                    <a-button
                      size="small"
                      type="text"
                      class="copy-code-btn"
                      @click="copyToClipboard(CURSOR_CONFIG_JSON)"
                    >
                      <CopyOutlined /> 复制
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="step-item">
                <div class="step-num">2</div>
                <div class="step-detail">
                  <div class="step-title">在 Cursor Composer 中使用</div>
                  <p class="step-desc">
                    配置完成后，Cursor 对话框将自动显示 AutoFlow 工具，可直接指示 Agent：“查询 Flow Hub 上的 SRE 流程并进行静态校验”。
                  </p>
                </div>
              </div>
            </div>
          </a-tab-pane>

          <!-- OpenClaw -->
          <a-tab-pane key="openclaw" tab="OpenClaw">
            <div class="guide-tab-panel">
              <div class="step-item">
                <div class="step-num">1</div>
                <div class="step-detail">
                  <div class="step-title">OpenClaw Gateway 插件配置文件</div>
                  <p class="step-desc">在 OpenClaw 智能体编排网络中将 AutoFlow 作为专用确定性执行器接入：</p>
                  <div class="code-block-wrapper">
                    <pre><code>{{ OPENCLAW_CONFIG_JSON }}</code></pre>
                    <a-button
                      size="small"
                      type="text"
                      class="copy-code-btn"
                      @click="copyToClipboard(OPENCLAW_CONFIG_JSON)"
                    >
                      <CopyOutlined /> 复制
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="step-item">
                <div class="step-num">2</div>
                <div class="step-detail">
                  <div class="step-title">多步流程确定性保障</div>
                  <p class="step-desc">
                    OpenClaw 负责规划与意图分解，复杂运维与数据流交由 AutoFlow 本地执行引擎与 Check 机制兜底，保障执行确定性。
                  </p>
                </div>
              </div>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>

      <div class="modal-custom-footer">
        <a-button type="primary" @click="agentGuideVisible = false">完成</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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
import {
  fetchHubFlowDetail,
  fetchHubFlows,
  installHubFlow,
  type HubFlowDetail,
  type HubFlowSummary,
} from '../api/hub'

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

const agentGuideVisible = ref(false)
const activeAgentTab = ref('claude')

// 分类选项
const CATEGORY_OPTIONS = [
  { key: 'all', label: '全部', backendCategory: undefined },
  { key: 'sre', label: 'SRE 运维自愈', backendCategory: 'SRE / 运维自愈' },
  { key: 'digest', label: '智能采集研报', backendCategory: '自动化数据采集' },
  { key: 'agent', label: 'Agent 工具链', backendCategory: 'Agent 工具链' },
  { key: 'rpa', label: '桌面 RPA', backendCategory: '桌面 RPA' },
]

// 累计安装量计算
const totalInstalls = computed(() => {
  return flows.value.reduce((acc, curr) => acc + (curr.installs || 0), 0)
})

// 分类与关键词过滤后的列表
const filteredFlows = computed(() => {
  let result = flows.value

  // 分类匹配
  if (selectedCategoryKey.value !== 'all') {
    const matchedOption = CATEGORY_OPTIONS.find((c) => c.key === selectedCategoryKey.value)
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

  // 搜索关键词匹配
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    result = result.filter(
      (f) =>
        f.title.toLowerCase().includes(q) ||
        f.name.toLowerCase().includes(q) ||
        f.description.toLowerCase().includes(q) ||
        f.tags.some((t) => t.toLowerCase().includes(q)),
    )
  }

  return result
})

// 加载流程市场列表
const loadFlows = async () => {
  loading.value = true
  try {
    const list = await fetchHubFlows()
    flows.value = list
  } catch (err: any) {
    message.error(err?.message || '获取 Flow Hub 列表失败')
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
  if (category.includes('采集') || category.includes('研报')) return 'purple'
  if (category.includes('Agent')) return 'green'
  if (category.includes('RPA')) return 'orange'
  return 'default'
}

const getCategoryIcon = (category: string) => {
  if (category.includes('SRE') || category.includes('运维')) return SafetyCertificateOutlined
  if (category.includes('采集') || category.includes('研报')) return SyncOutlined
  if (category.includes('Agent')) return ApiOutlined
  if (category.includes('RPA')) return RocketOutlined
  return ShopOutlined
}

// 打开 YAML 预览弹窗
const openYamlModal = async (flow: HubFlowSummary) => {
  activeFlow.value = flow
  activeYamlContent.value = '正在拉取 YAML 源码...'
  yamlModalVisible.value = true

  try {
    const detail: HubFlowDetail = await fetchHubFlowDetail(flow.id)
    activeYamlContent.value = detail.yaml
  } catch (err: any) {
    activeYamlContent.value = '# 获取 YAML 失败: ' + (err?.message || '网络错误')
    message.error('获取流程 YAML 失败')
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
    const res = await installHubFlow(flow.id, overwrite)
    message.success({
      content: `流程 [${flow.title}] 安装成功！已存至 ${res.path}`,
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
        title: '流程文件已存在',
        content: `本地 flows/ 目录中已存在同名流程文件 "${flow.name}.flow.yaml"，是否确认覆盖安装？`,
        okText: '确认覆盖',
        okType: 'danger',
        cancelText: '取消',
        onOk: async () => {
          await handleInstall(flow, true)
        },
      })
    } else {
      message.error(errorMsg || '安装流程失败')
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
    if (activeFlow.value?.id === flow.id && activeYamlContent.value && !activeYamlContent.value.startsWith('# 获取 YAML 失败')) {
      yamlCode = activeYamlContent.value
    } else {
      const detail = await fetchHubFlowDetail(flow.id)
      yamlCode = detail.yaml
    }

    // 存储至 sessionStorage 供画布生命周期读取
    sessionStorage.setItem('autoflow_canvas_yaml', yamlCode)
    message.success(`已将 [${flow.title}] 加载至编排画布`)

    if (yamlModalVisible.value) {
      yamlModalVisible.value = false
    }

    router.push({
      path: '/canvas',
      state: { flowYaml: yamlCode },
    })
  } catch (err: any) {
    message.error(err?.message || '读取流程源码并载入画布失败')
  } finally {
    loadingCanvasId.value = null
  }
}

// Agent 配置文件代码常量
const CLAUDE_CLI_COMMAND = `claude mcp add autoflow http://127.0.0.1:8000/mcp`

const CLAUDE_CONFIG_JSON = `{
  "mcpServers": {
    "autoflow": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}`

const CURSOR_CONFIG_JSON = `{
  "mcpServers": {
    "autoflow": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}`

const OPENCLAW_CONFIG_JSON = `{
  "plugins": {
    "autoflow_mcp": {
      "type": "mcp-client",
      "server_url": "http://127.0.0.1:8000/mcp",
      "auto_discover_tools": true
    }
  }
}`

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
  gap: 24px;
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
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.search-box {
  width: 340px;
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
  padding: 0 4px;
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

.modal-header-icon.guide-icon {
  background: #ECFDF5;
  color: #10B981;
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

/* Agent Guide Modal */
.guide-intro-banner {
  padding: 14px 18px;
  margin-bottom: 18px;
  background: #F0FDF4;
  border: 1px solid #BBF7D0;
  border-radius: 8px;
}

.banner-badge {
  display: inline-block;
  padding: 2px 8px;
  margin-bottom: 6px;
  background: #15803D;
  color: #FFFFFF;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.guide-intro-banner p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #166534;
}

.guide-intro-banner code {
  padding: 2px 5px;
  background: #DCFCE7;
  border-radius: 4px;
  font-family: var(--flow-font-mono);
  font-weight: 600;
  color: #14532D;
}

.guide-tab-panel {
  padding-top: 12px;
}

.step-item {
  display: flex;
  gap: 14px;
  margin-bottom: 20px;
}

.step-num {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 24px;
  height: 24px;
  background: var(--flow-color-primary);
  color: #FFFFFF;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
}

.step-detail {
  flex: 1;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--flow-text-title);
  margin-bottom: 4px;
}

.step-desc {
  font-size: 12.5px;
  color: var(--flow-text-secondary);
  margin-bottom: 8px;
}

.code-block-wrapper {
  position: relative;
  background: #0F172A;
  border-radius: 8px;
  padding: 12px 16px;
  overflow: hidden;
}

.code-block-wrapper pre {
  margin: 0;
}

.code-block-wrapper code {
  font-family: var(--flow-font-mono);
  font-size: 12.5px;
  line-height: 1.55;
  color: #38BDF8;
}

.copy-code-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  color: #94A3B8;
  font-size: 12px;
  padding: 2px 8px;
}

.copy-code-btn:hover {
  color: #FFFFFF;
  background: rgba(255, 255, 255, 0.1);
}
</style>
