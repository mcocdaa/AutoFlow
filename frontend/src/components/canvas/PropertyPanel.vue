<template>
  <div class="property-panel">
    <div class="panel-header">
      <a-radio-group v-model:value="activeTab" size="small" button-style="solid" class="tab-group">
        <a-radio-button value="node">
          <span>⚙️ 步骤配置</span>
        </a-radio-button>
        <a-radio-button value="yaml">
          <span>📄 YAML 源码</span>
        </a-radio-button>
        <a-radio-button value="triggers">
          <span>⏰ 触发器</span>
        </a-radio-button>
      </a-radio-group>
    </div>

    <div class="panel-body">
      <!-- 1. 步骤配置 Tab -->
      <div v-show="activeTab === 'node'" class="tab-content">
        <div v-if="selectedStep" class="step-form">
          <div class="form-title">
            <span class="badge">{{ selectedIndex + 1 }}</span>
            <span class="step-id af-mono">{{ selectedStep.id }}</span>
            <a-button
              type="text"
              danger
              size="small"
              class="delete-step-btn"
              @click="emit('delete-step', selectedStep.id)"
            >
              删除步骤
            </a-button>
          </div>

          <a-form layout="vertical" size="small">
            <a-form-item label="步骤 ID (唯一标识)">
              <a-input
                :value="selectedStep.id"
                placeholder="例如: fetch_data"
                @change="onIdChange($event.target.value)"
              />
            </a-form-item>

            <a-form-item label="步骤名称 (可读说明)">
              <a-input
                v-model:value="selectedStep.name"
                placeholder="例如: 拉取知乎热榜数据"
                @change="emitUpdate"
              />
            </a-form-item>

            <a-divider style="margin: 12px 0">动作配置 (Action)</a-divider>

            <a-form-item label="动作类型 (Action Type)">
              <a-auto-complete
                v-model:value="selectedStep.action.type"
                :options="actionOptions"
                placeholder="例如: core.log 或 dummy.echo"
                @change="emitUpdate"
              />
            </a-form-item>

            <a-form-item label="参数 (JSON / 模板)">
              <a-textarea
                :value="actionParamsJson"
                :rows="4"
                placeholder='{"message": "hello"}'
                class="af-mono"
                @change="onParamsChange($event.target.value)"
              />
            </a-form-item>

            <a-divider style="margin: 12px 0">强断言校验 (Check)</a-divider>

            <div class="check-toggle-row">
              <a-switch
                :checked="Boolean(selectedStep.check)"
                @change="toggleCheck"
              />
              <span class="switch-label">启用步骤强断言 (永不盲信输出)</span>
            </div>

            <div v-if="selectedStep.check" class="check-box">
              <a-form-item label="断言类型 (Check Type)">
                <a-select
                  v-model:value="selectedStep.check.type"
                  placeholder="选择校验断言"
                  @change="emitUpdate"
                >
                  <a-select-option value="core.assert_truthy">core.assert_truthy (真值断言)</a-select-option>
                  <a-select-option value="core.assert_status">core.assert_status (状态码断言)</a-select-option>
                  <a-select-option value="core.assert_equals">core.assert_equals (相等断言)</a-select-option>
                </a-select>
              </a-form-item>

              <a-form-item label="断言参数 (JSON)">
                <a-textarea
                  :value="checkParamsJson"
                  :rows="3"
                  placeholder='{"value": true}'
                  class="af-mono"
                  @change="onCheckParamsChange($event.target.value)"
                />
              </a-form-item>
            </div>

            <a-collapse ghost style="margin-top: 12px">
              <a-collapse-panel key="advanced" header="高级控制 (条件/循环/重试/导出)">
                <a-form-item label="执行条件 (Condition 模板)">
                  <a-input
                    v-model:value="selectedStep.condition"
                    placeholder="例如: {{steps.prev.output.success}} == true"
                    @change="emitUpdate"
                  />
                </a-form-item>

                <a-form-item label="循环遍历路径 (For Each)">
                  <a-input
                    v-model:value="selectedStep.for_each"
                    placeholder="例如: {{steps.list.output.items}}"
                    @change="emitUpdate"
                  />
                </a-form-item>

                <a-form-item label="导出为变量 (Output Var)">
                  <a-input
                    v-model:value="selectedStep.output_var"
                    placeholder="例如: digest_result"
                    @change="emitUpdate"
                  />
                </a-form-item>

                <a-row :gutter="8">
                  <a-col :span="12">
                    <a-form-item label="重试次数">
                      <a-input-number
                        :value="selectedStep.retry?.attempts ?? 0"
                        :min="0"
                        :max="5"
                        style="width: 100%"
                        @change="onRetryAttemptsChange"
                      />
                    </a-form-item>
                  </a-col>
                  <a-col :span="12">
                    <a-form-item label="退避间隔(秒)">
                      <a-input-number
                        :value="selectedStep.retry?.backoff_seconds ?? 0"
                        :min="0"
                        :step="0.5"
                        style="width: 100%"
                        @change="onRetryBackoffChange"
                      />
                    </a-form-item>
                  </a-col>
                </a-row>
              </a-collapse-panel>
            </a-collapse>
          </a-form>
        </div>

        <div v-else class="empty-selection">
          <span class="empty-icon">👆</span>
          <p>在画布中点击选中任意步骤节点，即可在此编辑其属性与参数</p>
        </div>
      </div>

      <!-- 2. YAML 源码 Tab -->
      <div v-show="activeTab === 'yaml'" class="tab-content yaml-tab">
        <div class="yaml-toolbar">
          <span class="yaml-tip">双向实时无损同步</span>
          <a-button size="small" type="link" @click="emit('format-yaml')">格式化</a-button>
        </div>
        <CodeEditor
          :model-value="yamlText"
          :min-height="420"
          @update:model-value="emit('update-yaml', $event)"
        />
      </div>

      <!-- 3. 触发器配置 Tab -->
      <div v-show="activeTab === 'triggers'" class="tab-content triggers-tab">
        <div class="trigger-section">
          <div class="section-title">
            <span>⏰ 内置 Cron 定时引擎</span>
          </div>
          <p class="section-desc">基于 croniter 协程调度，无需外部 crontab</p>

          <a-form layout="vertical" size="small">
            <a-form-item label="常用快捷预设">
              <a-select
                v-model:value="selectedCronPreset"
                placeholder="选择定时周期预设"
                @change="applyCronPreset"
              >
                <a-select-option value="* * * * *">每分钟 (* * * * *)</a-select-option>
                <a-select-option value="*/5 * * * *">每 5 分钟 (*/5 * * * *)</a-select-option>
                <a-select-option value="0 * * * *">每小时整点 (0 * * * *)</a-select-option>
                <a-select-option value="0 0 * * *">每天凌晨 00:00 (0 0 * * *)</a-select-option>
                <a-select-option value="0 9 * * 1-5">工作日早 09:00 (0 9 * * 1-5)</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="Cron 表达式">
              <div style="display: flex; gap: 8px">
                <a-input
                  v-model:value="cronExpr"
                  placeholder="*/5 * * * *"
                  class="af-mono"
                  @change="emitCronChange"
                />
                <a-button size="small" @click="predictCron">预测</a-button>
              </div>
            </a-form-item>

            <div v-if="predictedTimes.length > 0" class="predict-box">
              <div class="predict-title">未来 5 次触发时间预测:</div>
              <div v-for="(t, idx) in predictedTimes" :key="idx" class="predict-time af-mono">
                {{ idx + 1 }}. {{ formatTime(t) }}
              </div>
            </div>
          </a-form>
        </div>

        <a-divider style="margin: 16px 0" />

        <div class="trigger-section">
          <div class="section-title">
            <span>🌐 Webhook 外部事件网关</span>
          </div>
          <p class="section-desc">支持外部监控告警、GitHub 等事件触发，支持 HMAC-SHA256 签名校验</p>

          <a-form layout="vertical" size="small">
            <a-form-item label="Webhook 路径">
              <a-input
                :value="webhookUrl"
                readonly
                class="af-mono"
              />
            </a-form-item>

            <a-form-item label="访问 Token / HMAC 密钥">
              <a-input-password
                v-model:value="webhookToken"
                placeholder="设置该流程专用 Webhook Token"
                @change="emitWebhookChange"
              />
            </a-form-item>

            <div class="curl-example">
              <span class="curl-title">测试 cURL 命令:</span>
              <pre class="curl-code af-mono">curl -X POST {{ webhookUrl }} \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "ALT-1001", "event": "service_down"}'</pre>
            </div>
          </a-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import axios from 'axios'
import CodeEditor from '../shared/CodeEditor.vue'
import type { StepSpec } from '../../types/flow'

const props = defineProps<{
  selectedStep: StepSpec | null
  selectedIndex: number
  yamlText: string
  flowName: string
  cronValue?: string
  webhookTokenValue?: string
}>()

const emit = defineEmits<{
  (e: 'update-step', step: StepSpec): void
  (e: 'update-id', oldId: string, newId: string): void
  (e: 'delete-step', stepId: string): void
  (e: 'update-yaml', text: string): void
  (e: 'format-yaml'): void
  (e: 'cron-change', expr: string): void
  (e: 'webhook-change', token: string): void
}>()

const activeTab = ref<'node' | 'yaml' | 'triggers'>('node')
const actionOptions = [
  { value: 'core.log' },
  { value: 'dummy.echo' },
  { value: 'http.request' },
  { value: 'shell.exec' },
  { value: 'ai.deepseek' },
  { value: 'zhihu.fetch_hot' },
  { value: 'openclaw.crawl' },
  { value: 'desktop.click' },
  { value: 'desktop.screenshot' },
]

// 步骤参数序列化与编辑
const actionParamsJson = computed(() => {
  if (!props.selectedStep?.action?.params) return '{}'
  try {
    return JSON.stringify(props.selectedStep.action.params, null, 2)
  } catch {
    return '{}'
  }
})

const onParamsChange = (val: string) => {
  if (!props.selectedStep) return
  try {
    props.selectedStep.action.params = JSON.parse(val)
    emitUpdate()
  } catch {
    // 允许用户暂未输入完整 JSON
  }
}

const onIdChange = (newId: string) => {
  if (!props.selectedStep) return
  const oldId = props.selectedStep.id
  props.selectedStep.id = newId
  emit('update-id', oldId, newId)
}

const toggleCheck = (checked: boolean | string | number) => {
  if (!props.selectedStep) return
  if (checked) {
    props.selectedStep.check = {
      type: 'core.assert_truthy',
      params: { value: true },
    }
  } else {
    delete props.selectedStep.check
  }
  emitUpdate()
}

const checkParamsJson = computed(() => {
  if (!props.selectedStep?.check?.params) return '{}'
  try {
    return JSON.stringify(props.selectedStep.check.params, null, 2)
  } catch {
    return '{}'
  }
})

const onCheckParamsChange = (val: string) => {
  if (!props.selectedStep?.check) return
  try {
    props.selectedStep.check.params = JSON.parse(val)
    emitUpdate()
  } catch {
    // ignore parse error during typing
  }
}

const onRetryAttemptsChange = (val: number | null) => {
  if (!props.selectedStep) return
  const attempts = val ?? 0
  if (attempts > 0) {
    props.selectedStep.retry = {
      attempts,
      backoff_seconds: props.selectedStep.retry?.backoff_seconds ?? 1.0,
    }
  } else if (props.selectedStep.retry) {
    props.selectedStep.retry.attempts = 0
  }
  emitUpdate()
}

const onRetryBackoffChange = (val: number | null) => {
  if (!props.selectedStep?.retry) return
  props.selectedStep.retry.backoff_seconds = val ?? 0
  emitUpdate()
}

const emitUpdate = () => {
  if (props.selectedStep) {
    emit('update-step', props.selectedStep)
  }
}

// ---------------- 触发器逻辑 ----------------
const cronExpr = ref(props.cronValue || '')
const selectedCronPreset = ref<string>()
const predictedTimes = ref<string[]>([])
const webhookToken = ref(props.webhookTokenValue || 'default-token')

watch(() => props.cronValue, (v) => {
  if (v) cronExpr.value = v
})

const applyCronPreset = (val: string) => {
  cronExpr.value = val
  emitCronChange()
  predictCron()
}

const emitCronChange = () => {
  emit('cron-change', cronExpr.value)
}

const emitWebhookChange = () => {
  emit('webhook-change', webhookToken.value)
}

const webhookUrl = computed(() => {
  const host = window.location.origin
  return `${host}/api/v1/webhooks/${props.flowName || 'my_flow'}/${webhookToken.value || 'token'}`
})

const predictCron = async () => {
  if (!cronExpr.value) return
  try {
    const res = await axios.post('/api/v1/cron/validate', {
      expression: cronExpr.value,
      count: 5,
    })
    if (res.data.valid) {
      predictedTimes.value = res.data.next_runs
    } else {
      predictedTimes.value = []
    }
  } catch {
    predictedTimes.value = []
  }
}

const formatTime = (iso: string) => {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.property-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
  border-left: 1px solid #e2e8f0;
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  background: #f8fafc;
}

.tab-group {
  width: 100%;
  display: flex;
}

.tab-group :deep(.ant-radio-button-wrapper) {
  flex: 1;
  text-align: center;
  font-size: 12px;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
}

.tab-content {
  padding: 16px;
}

.form-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f1f5f9;
}

.badge {
  width: 20px;
  height: 20px;
  background: #2563eb;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.step-id {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  flex: 1;
}

.delete-step-btn {
  font-size: 11px;
}

.check-toggle-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.switch-label {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}

.check-box {
  padding: 12px;
  background: #fdf2f8;
  border: 1px solid #fbcfe8;
  border-radius: 8px;
  margin-bottom: 12px;
}

.empty-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.empty-icon {
  font-size: 28px;
  margin-bottom: 12px;
}

.yaml-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.yaml-tip {
  font-size: 11px;
  color: #64748b;
}

.trigger-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.section-desc {
  font-size: 11px;
  color: #64748b;
  margin: 0;
}

.predict-box {
  margin-top: 10px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.predict-title {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
}

.predict-time {
  font-size: 11px;
  color: #2563eb;
  line-height: 1.5;
}

.curl-example {
  margin-top: 10px;
  padding: 10px;
  background: #f1f5f9;
  border-radius: 6px;
}

.curl-title {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
}

.curl-code {
  margin: 6px 0 0;
  font-size: 11px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-all;
  color: #0f172a;
}
</style>
