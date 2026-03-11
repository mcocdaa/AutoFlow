<template>
  <div class="plugins-view">
    <div class="page-header">
      <h2 class="page-title">
        <el-icon class="title-icon"><Grid /></el-icon>
        Installed Plugins
      </h2>
      <div class="header-actions">
        <el-button type="primary" @click="store.fetchPlugins" :loading="store.loading" class="refresh-button">
          <el-icon><Refresh /></el-icon>
          Refresh
        </el-button>
        <el-button type="success" class="create-flow-button" @click="navigateToRunFlow">
          <el-icon><Right /></el-icon>
          去创建流程
        </el-button>
      </div>
    </div>
    
    <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom: 20px" />

    <el-card class="stats-card" v-if="store.plugins.length > 0">
      <el-row :gutter="20" class="stats-row">
        <el-col :span="8" :xs="24" :sm="24" :md="8">
          <div class="stat-item">
            <el-icon class="stat-icon"><Collection /></el-icon>
            <div class="stat-number">{{ store.plugins.length }}</div>
            <div class="stat-label">Total Plugins</div>
          </div>
        </el-col>
        <el-col :span="8" :xs="24" :sm="24" :md="8">
          <div class="stat-item">
            <el-icon class="stat-icon"><Lightning /></el-icon>
            <div class="stat-number">{{ store.actions.length }}</div>
            <div class="stat-label">Actions</div>
          </div>
        </el-col>
        <el-col :span="8" :xs="24" :sm="24" :md="8">
          <div class="stat-item">
            <el-icon class="stat-icon"><Check /></el-icon>
            <div class="stat-number">{{ store.checks.length }}</div>
            <div class="stat-label">Checks</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <h3 class="section-title">Plugin List</h3>
    <el-row :gutter="24" class="plugins-grid">
      <el-col :span="8" :xs="24" :sm="12" :md="8" v-for="plugin in store.plugins" :key="plugin.name">
        <el-card class="plugin-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <div class="plugin-name">{{ plugin.name }}</div>
              <el-tag size="small" type="primary" class="version-tag">{{ plugin.version }}</el-tag>
            </div>
          </template>
          <div class="plugin-body">
            <div class="plugin-description">{{ getPluginDescription(plugin.name) }}</div>
            <div class="plugin-status">
              <el-icon class="status-icon"><Check /></el-icon>
              <span>Active</span>
            </div>
            <div class="plugin-actions">
              <el-button size="small" @click="showPluginConfig(plugin)">配置</el-button>
              <el-button size="small" type="warning" @click="disablePlugin(plugin)">禁用</el-button>
              <el-button size="small" type="info" @click="viewPluginDocs(plugin)">文档</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div v-if="store.errors && store.errors.length > 0" class="errors-section">
      <h3 class="section-title">
        <el-icon class="title-icon"><Warning /></el-icon>
        Load Errors
      </h3>
      <el-card shadow="hover">
        <el-table :data="store.errors" style="width: 100%">
          <el-table-column prop="plugin_id" label="Plugin ID" width="180" />
          <el-table-column prop="file_path" label="Path" />
          <el-table-column prop="error" label="Error" />
        </el-table>
      </el-card>
    </div>

    <div class="actions-section">
      <div class="section-header">
        <h3 class="section-title">
          <el-icon class="title-icon"><Sunny /></el-icon>
          Registered Actions
        </h3>
        <el-input
          v-model="actionsSearch"
          placeholder="搜索 Actions"
          clearable
          class="search-input"
          size="small"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <el-card shadow="hover" class="tags-card">
        <el-collapse>
          <el-collapse-item
            v-for="(actions, pluginName) in groupedActions"
            :key="pluginName"
            :title="pluginName"
          >
            <div class="action-tags-group">
              <el-tag
                v-for="action in actions"
                :key="action"
                class="action-tag"
                @click="copyToClipboard(action)"
              >
                {{ action }}
              </el-tag>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </div>

    <div class="checks-section">
      <div class="section-header">
        <h3 class="section-title">
          <el-icon class="title-icon"><SuccessFilled /></el-icon>
          Registered Checks
        </h3>
        <el-input
          v-model="checksSearch"
          placeholder="搜索 Checks"
          clearable
          class="search-input"
          size="small"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <el-card shadow="hover" class="tags-card">
        <el-collapse>
          <el-collapse-item
            v-for="(checks, pluginName) in groupedChecks"
            :key="pluginName"
            :title="pluginName"
          >
            <div class="action-tags-group">
              <el-tag
                v-for="check in checks"
                :key="check"
                type="warning"
                class="action-tag"
                @click="copyToClipboard(check)"
              >
                {{ check }}
              </el-tag>
            </div>
          </el-collapse-item>
        </el-collapse>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { usePluginsStore } from '../stores/plugins'
import { Grid, Refresh, Check, Warning, Sunny, SuccessFilled, Collection, Lightning, Search, Right } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const store = usePluginsStore()
const error = computed(() => store.error)

// Search variables
const actionsSearch = ref('')
const checksSearch = ref('')

// Group actions by plugin
const groupedActions = computed(() => {
  const groups: Record<string, string[]> = {}
  store.actions.forEach(action => {
    const pluginName = action.split('.')[0]
    if (!groups[pluginName]) {
      groups[pluginName] = []
    }
    if (action.includes(actionsSearch.value)) {
      groups[pluginName].push(action)
    }
  })
  return groups
})

// Group checks by plugin
const groupedChecks = computed(() => {
  const groups: Record<string, string[]> = {}
  store.checks.forEach(check => {
    const pluginName = check.split('.')[0]
    if (!groups[pluginName]) {
      groups[pluginName] = []
    }
    if (check.includes(checksSearch.value)) {
      groups[pluginName].push(check)
    }
  })
  return groups
})

// Get plugin description
const getPluginDescription = (pluginName: string): string => {
  const descriptions: Record<string, string> = {
    'builtin': '核心基础功能集',
    'ai-deepseek': 'DeepSeek AI文本处理',
    'ai-openai': 'OpenAI模型集成',
    'http': 'HTTP网络请求功能',
    'file': '文件操作功能',
    'system': '系统操作功能'
  }
  return descriptions[pluginName] || '插件功能描述'
}

// Navigation
const navigateToRunFlow = () => {
  // Assuming router is available, replace with actual navigation
  console.log('Navigate to Run Flow page')
}

// Plugin actions
const showPluginConfig = (plugin: any) => {
  console.log('Show config for plugin:', plugin.name)
}

const disablePlugin = (plugin: any) => {
  console.log('Disable plugin:', plugin.name)
}

const viewPluginDocs = (plugin: any) => {
  console.log('View docs for plugin:', plugin.name)
}

// Copy to clipboard
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制到剪贴板')
}

onMounted(() => {
  store.fetchPlugins()
})
</script>

<style scoped>
.plugins-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  flex-wrap: wrap;
  gap: 10px;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.page-title {
  display: flex;
  align-items: center;
  font-size: 1.8rem;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.title-icon {
  margin-right: 10px;
  color: var(--primary-color, #667eea);
}

.refresh-button {
  display: flex;
  align-items: center;
}

.create-flow-button {
  display: flex;
  align-items: center;
}

.stats-card {
  margin-bottom: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stats-row {
  padding: 24px 0;
}

.stat-item {
  text-align: center;
  padding: 24px;
  transition: var(--transition, all 0.3s ease);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.1);
}

.stat-icon {
  font-size: 1.5rem;
  margin-bottom: 8px;
}

.stat-number {
  font-size: 2.2rem;
  font-weight: bold;
  margin-bottom: 5px;
  color: #ffffff;
}

.stat-label {
  font-size: 0.9rem;
  opacity: 0.9;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 1.3rem;
  font-weight: 600;
  color: #303133;
  margin: 30px 0 15px 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  flex-wrap: wrap;
  gap: 10px;
}

.search-input {
  width: 200px;
}

.plugins-grid {
  margin-bottom: 30px;
}

.plugin-card {
  transition: var(--transition, all 0.3s ease);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 24px;
}

.plugin-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15) !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 24px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.plugin-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: #303133;
}

.version-tag {
  font-size: 0.8rem;
}

.plugin-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plugin-description {
  font-size: 0.95rem;
  color: #606266;
  line-height: 1.4;
}

.plugin-status {
  display: flex;
  align-items: center;
  color: #67c23a;
  font-weight: 500;
}

.status-icon {
  margin-right: 8px;
  color: #67c23a;
}

.plugin-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.plugin-actions .el-button {
  min-width: 60px;
}

.errors-section {
  margin-top: 30px;
}

.actions-section,
.checks-section {
  margin-top: 30px;
}

.tags-card {
  padding: 24px;
  border-radius: 12px;
}

.action-tags-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 0;
}

.action-tag {
  margin-right: 10px;
  margin-bottom: 10px;
  font-size: 0.9rem;
  padding: 6px 12px;
  border-radius: 16px;
  transition: var(--transition, all 0.3s ease);
  cursor: pointer;
  min-height: 32px;
  display: inline-flex;
  align-items: center;
}

.action-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Responsive styles */
@media (max-width: 768px) {
  .plugins-view {
    padding: 10px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .search-input {
    width: 100%;
  }
  
  .plugin-actions {
    justify-content: space-between;
  }
  
  .plugin-actions .el-button {
    flex: 1;
    text-align: center;
  }
}

/* Touch optimization */
@media (hover: none) and (pointer: coarse) {
  .action-tag {
    min-height: 44px;
    min-width: 44px;
    padding: 10px 16px;
  }
  
  .plugin-actions .el-button {
    min-height: 44px;
  }
  
  .refresh-button,
  .create-flow-button {
    min-height: 44px;
  }
}
</style>
