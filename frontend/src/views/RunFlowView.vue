<template>
  <div class="run-view">
    <div class="page-header">
      <h2 class="page-title">
          <el-icon class="title-icon"><CaretRight /></el-icon>
          Run Flow
        </h2>
    </div>
    
    <el-row :gutter="24" class="main-content">
      <el-col :span="12" :xs="24" :sm="24" :md="12">
        <el-card class="yaml-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <h3 class="card-title">
                <el-icon class="card-icon"><Document /></el-icon>
                Flow YAML
              </h3>
              <el-select v-model="selectedExample" placeholder="Load Example" @change="loadExample" class="example-select">
                <el-option label="Minimal Echo" value="echo" />
                <el-option label="Desktop Checkin" value="desktop" />
                <el-option label="Zhihu Digest" value="zhihu" />
              </el-select>
            </div>
          </template>
          <el-input
            v-model="flowYaml"
            type="textarea"
            :rows="15"
            placeholder="Paste your flow YAML here..."
            class="yaml-input"
          />
          <div class="action-buttons">
            <el-checkbox v-model="dryRun" class="dry-run-checkbox">
              <el-icon><Cloudy /></el-icon>
              Dry Run
            </el-checkbox>
            <el-button type="primary" @click="handleRun" :loading="store.loading" class="execute-button">
              <el-icon><Right /></el-icon>
              Execute
            </el-button>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12" :xs="24" :sm="24" :md="12">
        <el-card class="result-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <h3 class="card-title">
                <el-icon class="card-icon"><DataAnalysis /></el-icon>
                Execution Result
              </h3>
              <el-tag v-if="currentRun" :type="statusType" class="status-tag">{{ currentRun.status }}</el-tag>
            </div>
          </template>
          
          <div v-if="store.error" class="error-section">
            <el-alert :title="store.error" type="error" show-icon />
          </div>

          <div v-if="currentRun" class="run-details">
            <div class="run-info">
              <div class="info-item">
                <el-icon class="info-icon"><User /></el-icon>
                <span class="info-label">Run ID:</span>
                <span class="info-value">{{ currentRun.run_id }}</span>
              </div>
              <div class="info-item">
                <el-icon class="info-icon"><Timer /></el-icon>
                <span class="info-label">Duration:</span>
                <span class="info-value">{{ currentRun.duration_ms }} ms</span>
              </div>
            </div>
            
            <div class="steps-section">
              <h4 class="steps-title">
                <el-icon><List /></el-icon>
                Steps
              </h4>
              <el-collapse class="steps-collapse">
                <el-collapse-item 
                  v-for="step in currentRun.steps" 
                  :key="step.step_id" 
                  :title="step.step_id + ' (' + step.status + ')'"
                  class="step-item"
                >
                  <div v-if="step.error" class="step-error">
                    <el-alert :title="step.error" type="error" :closable="false" />
                  </div>
                  <div class="step-output">
                    <pre class="output-pre">{{ JSON.stringify(step.action_output, null, 2) }}</pre>
                  </div>
                  <div v-if="step.check_passed !== null" class="step-check">
                    <span class="check-label">Check:</span>
                    <el-tag :type="step.check_passed ? 'success' : 'danger'" class="check-tag">
                      {{ step.check_passed ? 'Passed' : 'Failed' }}
                    </el-tag>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
          <div v-else class="empty-state">
            <el-empty
              description="No run executed yet"
              :image-size="120"
            >
              <template #description>
                <p class="empty-text">Create a flow YAML and click Execute to run</p>
              </template>
            </el-empty>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRunsStore } from '../stores/runs'
import { CaretRight, Document, DataAnalysis, Cloudy, Right, User, Timer, List } from '@element-plus/icons-vue'

const store = useRunsStore()
const selectedExample = ref('')
const flowYaml = ref(`version: "1"
name: "demo-flow"
steps:
  - id: "hello"
    action:
      type: "core.log"
      params:
        message: "Hello AutoFlow!"
`)
const dryRun = ref(false)

const examples = {
  echo: `version: "1"
name: "echo-demo"
steps:
  - id: "s1"
    action:
      type: "dummy.echo"
      params:
        message: "Hello from Frontend"
    check:
      type: "text.contains"
      params:
        needle: "Frontend"`,
  desktop: `version: "1"
name: "desktop-demo"
steps:
  - id: "move-mouse"
    action:
      type: "desktop.click"
      params:
        x: 100
        y: 100
        clicks: 1
  - id: "screenshot"
    action:
      type: "desktop.screenshot"
      params:
        name: "demo-shot"`,
  zhihu: `version: "1"
name: "zhihu-digest"
steps:
  - id: "fetch"
    action:
      type: "zhihu.fetch_answer"
      params:
        url: "https://www.zhihu.com/question/784489052/answer/1946200783080125276"
  - id: "summarize"
    action:
      type: "ai.deepseek_summarize"
      params:
        system_prompt: "Summarize this answer"
        # api_key: "env:DEEPSEEK_API_KEY" # loaded from backend env`
}

const loadExample = (val: string) => {
  if (val && examples[val as keyof typeof examples]) {
    flowYaml.value = examples[val as keyof typeof examples]
  }
}

const currentRun = computed(() => store.currentRun)

const statusType = computed(() => {
  if (!currentRun.value) return 'info'
  if (currentRun.value.status === 'success') return 'success'
  if (currentRun.value.status === 'failed') return 'danger'
  return 'warning'
})

const handleRun = async () => {
  const vars = dryRun.value ? { dry_run: true } : {}
  await store.executeFlow(flowYaml.value, {}, vars)
}
</script>

<style scoped>
.run-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.page-header {
  margin-bottom: 30px;
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
  color: var(--primary-color);
}

.main-content {
  margin-bottom: 30px;
}

.yaml-card,
.result-card {
  transition: var(--transition);
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 24px;
}

.yaml-card:hover,
.result-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15) !important;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 24px;
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  flex-wrap: wrap;
  gap: 10px;
}

.card-title {
  display: flex;
  align-items: center;
  font-size: 1.1rem;
  font-weight: 600;
  color: #303133;
  margin: 0;
  flex: 1;
}

.card-icon {
  margin-right: 8px;
  color: var(--primary-color);
}

.example-select {
  width: 200px;
  min-width: 150px;
}

.yaml-input {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9rem;
  line-height: 1.5;
  background-color: #fafafa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 15px;
  min-height: 300px;
  resize: vertical;
}

.yaml-input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.action-buttons {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
  flex-wrap: wrap;
  gap: 10px;
}

.dry-run-checkbox {
  display: flex;
  align-items: center;
  font-size: 0.9rem;
}

.dry-run-checkbox .el-icon {
  margin-right: 5px;
}

.execute-button {
  display: flex;
  align-items: center;
  font-size: 1rem;
  padding: 10px 24px;
  min-height: 40px;
}

.status-tag {
  font-size: 0.85rem;
  padding: 4px 12px;
}

.error-section {
  margin-bottom: 20px;
}

.run-details {
  padding: 10px 0;
}

.run-info {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.info-icon {
  color: var(--primary-color);
  font-size: 1rem;
}

.info-label {
  font-weight: 500;
  color: #606266;
}

.info-value {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9rem;
  color: #303133;
  word-break: break-all;
}

.steps-section {
  margin-top: 20px;
}

.steps-title {
  display: flex;
  align-items: center;
  font-size: 1rem;
  font-weight: 600;
  color: #303133;
  margin-bottom: 15px;
}

.steps-title .el-icon {
  margin-right: 8px;
  color: var(--primary-color);
}

.steps-collapse {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.step-item {
  border-bottom: 1px solid #e9ecef;
}

.step-item:last-child {
  border-bottom: none;
}

.step-error {
  margin-bottom: 15px;
}

.step-output {
  margin: 15px 0;
}

.output-pre {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.85rem;
  line-height: 1.4;
  background-color: #fafafa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 15px;
  overflow: auto;
  max-height: 250px;
  margin: 0;
}

.step-check {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e9ecef;
  flex-wrap: wrap;
}

.check-label {
  font-weight: 500;
  color: #606266;
}

.check-tag {
  font-size: 0.85rem;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

.empty-text {
  color: #909399;
  font-size: 0.95rem;
}

/* 响应式样式 */
@media (max-width: 768px) {
  .run-view {
    padding: 0 10px;
  }
  
  .page-title {
    font-size: 1.5rem;
  }
  
  .card-header {
    padding: 12px 16px;
  }
  
  .card-title {
    font-size: 1rem;
  }
  
  .example-select {
    width: 100%;
  }
  
  .yaml-input {
    font-size: 0.85rem;
    padding: 12px;
    min-height: 250px;
  }
  
  .action-buttons {
    flex-direction: column;
    align-items: stretch;
  }
  
  .execute-button {
    width: 100%;
    justify-content: center;
  }
  
  .run-info {
    flex-direction: column;
    gap: 10px;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .output-pre {
    font-size: 0.8rem;
    padding: 12px;
    max-height: 200px;
  }
}

/* 触摸优化 */
@media (hover: none) and (pointer: coarse) {
  .execute-button {
    min-height: 44px;
  }
  
  .example-select {
    min-height: 44px;
  }
  
  .yaml-input {
    min-height: 300px;
  }
}
</style>
