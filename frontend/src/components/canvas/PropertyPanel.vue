<template>
  <div class="property-panel">
    <div class="panel-header">
      <a-radio-group v-model:value="activeTab" size="small" button-style="solid" class="tab-group">
        <a-radio-button value="node">
          <span>⚙️ {{ t('prop.tab.node') }}</span>
        </a-radio-button>
        <a-radio-button value="yaml">
          <span>📄 {{ t('prop.tab.yaml') }}</span>
        </a-radio-button>
        <a-radio-button value="triggers">
          <span>⏰ {{ t('prop.tab.triggers') }}</span>
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
              {{ t('prop.deleteStep') }}
            </a-button>
          </div>

          <a-form layout="vertical" size="small">
            <a-form-item :label="t('prop.stepIdLabel')">
              <a-input
                :value="draftStepId"
                :placeholder="t('prop.stepIdPlaceholder')"
                @change="onIdChange($event.target.value)"
                @blur="onIdBlur"
              />
            </a-form-item>

            <a-form-item :label="t('prop.stepNameLabel')">
              <a-input
                :value="displayStepName"
                :placeholder="t('prop.stepNamePlaceholder')"
                @change="onNameChange($event.target.value)"
              />
            </a-form-item>

            <a-divider style="margin: 12px 0">{{ t('prop.actionConfig') }}</a-divider>

            <a-form-item :label="t('prop.actionTypeLabel')">
              <a-auto-complete
                v-model:value="selectedStep.action.type"
                :options="actionOptions"
                :placeholder="t('prop.actionTypePlaceholder')"
                @change="emitUpdate"
              />
            </a-form-item>

            <a-form-item :label="t('prop.paramsLabel')">
              <a-textarea
                :value="actionParamsJson"
                :rows="4"
                placeholder='{"message": "hello"}'
                class="af-mono"
                @change="onParamsChange($event.target.value)"
              />
            </a-form-item>

            <a-divider style="margin: 12px 0">{{ t('prop.checkConfig') }}</a-divider>

            <div class="check-toggle-row">
              <a-switch
                :checked="Boolean(selectedStep.check)"
                @change="toggleCheck"
              />
              <span class="switch-label">{{ t('prop.enableCheck') }}</span>
            </div>

            <div v-if="selectedStep.check" class="check-box">
              <a-form-item :label="t('prop.checkTypeLabel')">
                <a-select
                  v-model:value="selectedStep.check.type"
                  :placeholder="t('prop.checkTypePlaceholder')"
                  @change="emitUpdate"
                >
                  <a-select-option value="core.assert_truthy">
                    core.assert_truthy ({{ locale === 'en' ? 'Truthy' : '真值断言' }})
                  </a-select-option>
                  <a-select-option value="core.assert_status">
                    core.assert_status ({{ locale === 'en' ? 'HTTP Status' : '状态码断言' }})
                  </a-select-option>
                  <a-select-option value="core.assert_equals">
                    core.assert_equals ({{ locale === 'en' ? 'Equals' : '相等断言' }})
                  </a-select-option>
                  <a-select-option value="text.contains">
                    text.contains ({{ locale === 'en' ? 'Text Contains' : '文本包含断言' }})
                  </a-select-option>
                  <a-select-option value="core.always_true">
                    core.always_true ({{ locale === 'en' ? 'Always True' : '恒真断言' }})
                  </a-select-option>
                </a-select>
              </a-form-item>

              <a-form-item :label="t('prop.checkParamsLabel')">
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
              <a-collapse-panel key="advanced" :header="t('prop.advancedHeader')">
                <a-form-item :label="t('prop.conditionLabel')">
                  <a-input
                    v-model:value="selectedStep.condition"
                    :placeholder="t('prop.conditionPlaceholder')"
                    @change="emitUpdate"
                  />
                </a-form-item>

                <a-form-item :label="t('prop.forEachLabel')">
                  <a-input
                    v-model:value="selectedStep.for_each"
                    :placeholder="t('prop.forEachPlaceholder')"
                    @change="emitUpdate"
                  />
                </a-form-item>

                <a-form-item :label="t('prop.outputVarLabel')">
                  <a-input
                    v-model:value="selectedStep.output_var"
                    :placeholder="t('prop.outputVarPlaceholder')"
                    @change="emitUpdate"
                  />
                </a-form-item>

                <a-row :gutter="8">
                  <a-col :span="12">
                    <a-form-item :label="t('prop.retryAttempts')">
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
                    <a-form-item :label="t('prop.retryBackoff')">
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
          <p>{{ t('prop.emptySelection') }}</p>
        </div>
      </div>

      <!-- 2. YAML 源码 Tab -->
      <div v-show="activeTab === 'yaml'" class="tab-content yaml-tab">
        <div class="yaml-toolbar">
          <span class="yaml-tip">{{ t('prop.yamlSyncTip') }}</span>
          <a-button size="small" type="link" @click="emit('format-yaml')">{{ t('prop.formatYaml') }}</a-button>
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
            <span>⏰ {{ t('prop.cronTitle') }}</span>
          </div>
          <p class="section-desc">{{ t('prop.cronDesc') }}</p>

          <a-form layout="vertical" size="small">
            <a-form-item :label="t('prop.cronPresetLabel')">
              <a-select
                v-model:value="selectedCronPreset"
                :placeholder="t('prop.cronPresetPlaceholder')"
                @change="applyCronPreset"
              >
                <a-select-option value="* * * * *">{{ t('prop.cronPreset.everyMin') }}</a-select-option>
                <a-select-option value="*/5 * * * *">{{ t('prop.cronPreset.every5Min') }}</a-select-option>
                <a-select-option value="0 * * * *">{{ t('prop.cronPreset.hourly') }}</a-select-option>
                <a-select-option value="0 0 * * *">{{ t('prop.cronPreset.daily') }}</a-select-option>
                <a-select-option value="0 9 * * 1-5">{{ t('prop.cronPreset.weekdays') }}</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item :label="t('prop.cronExprLabel')">
              <div style="display: flex; gap: 8px">
                <a-input
                  v-model:value="cronExpr"
                  placeholder="*/5 * * * *"
                  class="af-mono"
                  @change="emitCronChange"
                />
                <a-button size="small" @click="predictCron">{{ t('prop.predictBtn') }}</a-button>
              </div>
            </a-form-item>

            <div v-if="predictedTimes.length > 0" class="predict-box">
              <div class="predict-title">{{ t('prop.predictTitle') }}</div>
              <div v-for="(timeStr, idx) in predictedTimes" :key="idx" class="predict-time af-mono">
                {{ idx + 1 }}. {{ formatTime(timeStr) }}
              </div>
            </div>
          </a-form>
        </div>

        <a-divider style="margin: 16px 0" />

        <div class="trigger-section">
          <div class="section-title">
            <span>🌐 {{ t('prop.webhookTitle') }}</span>
          </div>
          <p class="section-desc">{{ t('prop.webhookDesc') }}</p>

          <a-form layout="vertical" size="small">
            <a-form-item :label="t('prop.webhookFlowLabel')">
              <a-input
                :value="flowName || 'my_flow'"
                readonly
                class="af-mono"
              />
            </a-form-item>

            <a-form-item :label="t('prop.webhookTokenLabel')">
              <a-input-password
                v-model:value="webhookToken"
                :placeholder="t('prop.webhookTokenPlaceholder')"
                @change="emitWebhookChange"
              />
            </a-form-item>

            <div class="curl-example">
              <span class="curl-title">{{ t('prop.webhookSecurityTitle') }}</span>
              <p class="curl-code">{{ t('prop.webhookSecurityDesc') }}</p>
            </div>
          </a-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import apiClient from '../../api'
import { localizeStepName, useI18n } from '../../i18n'
import CodeEditor from '../shared/CodeEditor.vue'
import type { StepSpec } from '../../types/flow'

const { locale, t } = useI18n()

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
  { value: 'core.sleep' },
  { value: 'dummy.echo' },
  { value: 'openclaw.http_request' },
  { value: 'openclaw.exec' },
  { value: 'openclaw.knowflow_record' },
  { value: 'ai.deepseek_summarize' },
  { value: 'zhihu.fetch_answer' },
  { value: 'zhihu.post_answer_draft' },
  { value: 'desktop.activate_window' },
  { value: 'desktop.click' },
  { value: 'desktop.type_text' },
  { value: 'desktop.wait' },
  { value: 'desktop.screenshot' },
]

const displayStepName = computed(() => {
  return localizeStepName(props.selectedStep?.name, locale.value)
})

const onNameChange = (newName: string) => {
  if (!props.selectedStep) return
  props.selectedStep.name = newName
  emitUpdate()
}

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

const draftStepId = ref(props.selectedStep?.id ?? '')

watch(
  () => props.selectedStep?.id,
  (newVal) => {
    draftStepId.value = newVal ?? ''
  },
  { immediate: true },
)

const onIdChange = (newId: string) => {
  if (!props.selectedStep) return
  draftStepId.value = newId
  const trimmed = newId.trim()
  if (!trimmed) return
  const oldId = props.selectedStep.id
  if (trimmed === oldId) return
  emit('update-id', oldId, trimmed)
}

const onIdBlur = () => {
  if (!props.selectedStep) return
  draftStepId.value = props.selectedStep.id
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
const webhookToken = ref(props.webhookTokenValue || '')

watch(() => props.cronValue, (v) => {
  cronExpr.value = v || ''
})

watch(() => props.webhookTokenValue, (v) => {
  webhookToken.value = v || ''
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

const predictCron = async () => {
  if (!cronExpr.value) return
  try {
    const res = await apiClient.post('/cron/validate', {
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
  return new Date(iso).toLocaleString(locale.value === 'en' ? 'en-US' : 'zh-CN', { hour12: false })
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
  padding: 12px 12px;
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
  padding: 0 4px;
  white-space: nowrap;
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
  font-size: 11.5px;
  line-height: 1.5;
  word-break: break-word;
  color: #334155;
}
</style>
