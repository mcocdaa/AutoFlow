<template>
  <div class="af-page secrets-vault-page">
    <PageHeader
      :title="t('secrets.title')"
      :description="t('secrets.desc')"
      :icon="KeyOutlined"
    >
      <template #actions>
        <a-button type="primary" @click="openAddModal">
          <template #icon><PlusOutlined /></template>
          {{ t('secrets.addBtn') }}
        </a-button>
        <a-button :loading="loading" @click="loadSecrets">
          <template #icon><ReloadOutlined /></template>
          {{ t('common.refresh') }}
        </a-button>
      </template>
    </PageHeader>

    <!-- 顶部安全脱敏机制说明卡片 -->
    <div class="security-hero-card">
      <div class="security-hero-badge">
        <SafetyCertificateOutlined class="hero-badge-icon" />
        <span>{{ t('secrets.heroBadge') }}</span>
      </div>

      <div class="security-grid">
        <div class="security-col">
          <div class="col-header">
            <LockOutlined class="col-icon primary" />
            <h4 class="col-title">{{ t('secrets.col1Title') }}</h4>
          </div>
          <p class="col-desc">
            {{ t('secrets.col1Desc') }}
          </p>
        </div>

        <div class="security-col">
          <div class="col-header">
            <CodeOutlined class="col-icon info" />
            <h4 class="col-title">{{ t('secrets.col2Title') }}</h4>
          </div>
          <p class="col-desc">
            {{ t('secrets.col2DescPrefix') }}
            <a-tag class="code-tag" @click="copyToClipboard(SECRET_SYNTAX_EXAMPLE)">
              <span>{{ SECRET_SYNTAX_EXAMPLE }}</span>
              <CopyOutlined class="copy-tag-icon" />
            </a-tag>
            {{ t('secrets.col2DescSuffix') }}
          </p>
        </div>

        <div class="security-col">
          <div class="col-header">
            <EyeInvisibleOutlined class="col-icon warning" />
            <h4 class="col-title">{{ t('secrets.col3Title') }}</h4>
          </div>
          <p class="col-desc">
            {{ t('secrets.col3Desc') }}
          </p>
        </div>
      </div>
    </div>

    <!-- 凭据列表卡片 -->
    <a-card class="secrets-table-card" :body-style="{ padding: '20px' }">
      <div class="table-toolbar">
        <div class="toolbar-left">
          <h3 class="card-title">
            <SafetyCertificateOutlined class="title-icon" />
            {{ t('secrets.savedTitle') }}
            <a-tag color="blue" class="count-badge">{{ filteredSecrets.length }}</a-tag>
          </h3>
        </div>
        <div class="toolbar-right">
          <a-input-search
            v-model:value="searchKey"
            :placeholder="t('secrets.searchPlaceholder')"
            allow-clear
            style="width: 260px"
          />
        </div>
      </div>

      <a-table
        :columns="columns"
        :data-source="filteredSecrets"
        :row-key="(record: SecretItem) => record.key"
        :loading="loading"
        :pagination="{ pageSize: 8, showTotal: (total: number) => t('secrets.totalCount', { total }) }"
        class="secrets-table"
      >
        <!-- Key 列 -->
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'key'">
            <div class="key-cell">
              <KeyOutlined class="key-icon" />
              <span class="key-name">{{ record.key }}</span>
              <a-tooltip :title="t('secrets.copyMacroTip')">
                <a-button
                  type="text"
                  size="small"
                  class="quick-copy-btn"
                  @click="copyReference(record.key)"
                >
                  <CopyOutlined />
                </a-button>
              </a-tooltip>
            </div>
          </template>

          <!-- 脱敏值列 -->
          <template v-else-if="column.key === 'masked_value'">
            <div class="masked-cell">
              <span class="masked-tag">{{ record.masked_value }}</span>
              <span class="masked-tip">{{ t('secrets.maskedTip') }}</span>
            </div>
          </template>

          <!-- 加密状态列 -->
          <template v-else-if="column.key === 'status'">
            <div class="status-cell">
              <a-badge status="success" />
              <span class="status-text">{{ t('secrets.statusProtected') }}</span>
            </div>
          </template>

          <!-- 操作列 -->
          <template v-else-if="column.key === 'actions'">
            <div class="actions-cell">
              <a-button
                type="link"
                size="small"
                @click="copyReference(record.key)"
              >
                {{ t('secrets.copyRef') }}
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="openEditModal(record)"
              >
                {{ t('secrets.updateVal') }}
              </a-button>
              <a-popconfirm
                :title="t('secrets.deleteConfirmTitle', { key: record.key })"
                :description="t('secrets.deleteConfirmDesc')"
                :ok-text="t('secrets.confirmDelete')"
                :cancel-text="t('common.cancel')"
                ok-type="danger"
                @confirm="handleDelete(record.key)"
              >
                <a-button
                  type="link"
                  danger
                  size="small"
                  :loading="deletingKey === record.key"
                >
                  {{ t('common.delete') }}
                </a-button>
              </a-popconfirm>
            </div>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 添加 / 编辑凭据模态框 -->
    <a-modal
      v-model:open="modalVisible"
      :title="null"
      :footer="null"
      width="560px"
      centered
      wrap-class-name="secret-form-modal"
    >
      <div class="modal-header">
        <span class="modal-icon"><KeyOutlined /></span>
        <div>
          <h3 class="modal-title">{{ isEditing ? t('secrets.modal.editTitle') : t('secrets.modal.addTitle') }}</h3>
          <span class="modal-desc">
            {{ isEditing ? t('secrets.modal.editDesc', { key: formState.key }) : t('secrets.modal.addDesc') }}
          </span>
        </div>
      </div>

      <a-form
        ref="formRef"
        :model="formState"
        :rules="formRules"
        layout="vertical"
        class="secret-form"
      >
        <a-form-item :label="t('secrets.form.keyLabel')" name="key">
          <a-input
            v-model:value="formState.key"
            :disabled="isEditing"
            :placeholder="t('secrets.form.keyPlaceholder')"
            :maxlength="128"
          >
            <template #prefix><KeyOutlined class="input-prefix-icon" /></template>
          </a-input>
          <div class="input-help">
            {{ t('secrets.form.keyHelpPrefix') }}
            <code>{{ currentSecretRef }}</code>
            {{ t('secrets.form.keyHelpSuffix') }}
          </div>
        </a-form-item>

        <a-form-item :label="t('secrets.form.valLabel')" name="value">
          <a-input-password
            v-model:value="formState.value"
            :placeholder="t('secrets.form.valPlaceholder')"
            allow-clear
          >
            <template #prefix><LockOutlined class="input-prefix-icon" /></template>
          </a-input-password>
          <div class="input-help">
            {{ t('secrets.form.valHelp') }}
          </div>
        </a-form-item>

        <div class="form-security-alert">
          <SafetyCertificateOutlined class="alert-icon" />
          <span>{{ t('secrets.form.securityAlert') }}</span>
        </div>
      </a-form>

      <div class="modal-footer">
        <a-button @click="modalVisible = false">{{ t('common.cancel') }}</a-button>
        <a-button
          type="primary"
          :loading="saving"
          @click="handleSubmit"
        >
          {{ isEditing ? t('secrets.form.confirmUpdate') : t('secrets.form.encryptSave') }}
        </a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import type { FormInstance, Rule } from 'ant-design-vue/es/form'
import { message } from 'ant-design-vue'
import {
  CodeOutlined,
  CopyOutlined,
  EyeInvisibleOutlined,
  KeyOutlined,
  LockOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons-vue'
import PageHeader from '../components/shared/PageHeader.vue'
import { useClipboard } from '../composables/useClipboard'
import { useI18n } from '../i18n'
import {
  deleteSecret,
  fetchSecrets,
  setSecret,
  type SecretItem,
} from '../api/secrets'

const { locale, t } = useI18n()
const { copyToClipboard } = useClipboard()

// 数据与状态
const loading = ref(false)
const saving = ref(false)
const deletingKey = ref<string | null>(null)
const secrets = ref<SecretItem[]>([])
const searchKey = ref('')

// 模态框与表单
const modalVisible = ref(false)
const isEditing = ref(false)
const validationTriggered = ref(false)
const formRef = ref<FormInstance>()
const formState = reactive({
  key: '',
  value: '',
})

const SECRET_SYNTAX_EXAMPLE = '{{secrets.KEY}}'
const currentSecretRef = computed(() => `{{secrets.${formState.key || 'KEY'}}}`)

// 表单校验规则
const validateKey = async (_rule: Rule, value: string) => {
  if (!value) {
    return Promise.reject(new Error(t('secrets.validation.keyRequired')))
  }
  const keyRegex = /^[A-Za-z0-9_]{1,128}$/
  if (!keyRegex.test(value)) {
    return Promise.reject(new Error(t('secrets.validation.keyPattern')))
  }
  return Promise.resolve()
}

const formRules = computed<Record<string, Rule[]>>(() => ({
  key: [{ required: true, validator: validateKey, trigger: ['change', 'blur'] }],
  value: [{ required: true, message: t('secrets.validation.valRequired'), trigger: ['change', 'blur'] }],
}))

watch(locale, async () => {
  if (!modalVisible.value) return
  const hasDomError = Boolean(
    typeof document !== 'undefined' &&
      document.querySelector('.secret-form .ant-form-item-explain-error'),
  )
  if (!validationTriggered.value && !hasDomError) return
  await nextTick()
  try {
    await formRef.value?.validateFields()
  } catch {
    // 保持并刷新当前激活语言下的校验错误提示
  }
})

// 表格列定义
const columns = computed(() => [
  {
    title: t('secrets.col.key'),
    dataIndex: 'key',
    key: 'key',
    width: '30%',
  },
  {
    title: t('secrets.col.masked'),
    dataIndex: 'masked_value',
    key: 'masked_value',
    width: '26%',
  },
  {
    title: t('secrets.col.security'),
    key: 'status',
    width: '22%',
  },
  {
    title: t('secrets.col.actions'),
    key: 'actions',
    width: '22%',
    align: 'right' as const,
  },
])

// 过滤后的列表
const filteredSecrets = computed(() => {
  const q = searchKey.value.trim().toLowerCase()
  if (!q) return secrets.value
  return secrets.value.filter((item) => item.key.toLowerCase().includes(q))
})

// 加载凭据列表
const loadSecrets = async () => {
  loading.value = true
  try {
    const list = await fetchSecrets()
    secrets.value = list
  } catch (err: any) {
    message.error(err?.message || t('secrets.msg.loadFailed'))
  } finally {
    loading.value = false
  }
}

// 快速复制引用宏
const copyReference = (key: string) => {
  const refCode = `{{secrets.${key}}}`
  copyToClipboard(refCode)
}

// 打开新增弹窗
const openAddModal = () => {
  isEditing.value = false
  validationTriggered.value = false
  formState.key = ''
  formState.value = ''
  modalVisible.value = true
  formRef.value?.resetFields()
}

// 打开编辑弹窗
const openEditModal = (item: SecretItem) => {
  isEditing.value = true
  validationTriggered.value = false
  formState.key = item.key
  formState.value = ''
  modalVisible.value = true
  formRef.value?.resetFields()
}

// 提交表单保存
const handleSubmit = async () => {
  validationTriggered.value = true
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    await setSecret(formState.key, formState.value)
    message.success(t('secrets.msg.saved', { key: formState.key }))
    modalVisible.value = false
    await loadSecrets()
  } catch (err: any) {
    message.error(err?.message || t('secrets.msg.saveFailed'))
  } finally {
    saving.value = false
  }
}

// 删除凭据
const handleDelete = async (key: string) => {
  deletingKey.value = key
  try {
    await deleteSecret(key)
    message.success(t('secrets.msg.deleted', { key }))
    await loadSecrets()
  } catch (err: any) {
    message.error(err?.message || t('secrets.msg.deleteFailed'))
  } finally {
    deletingKey.value = null
  }
}

onMounted(() => {
  loadSecrets()
})
</script>

<style scoped>
.secrets-vault-page {
  padding-bottom: 40px;
}

/* 顶部安全机制横幅 */
.security-hero-card {
  padding: 18px 22px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
  border-radius: var(--flow-border-radius-lg);
  color: #FFFFFF;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
}

.security-hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  margin-bottom: 14px;
  background: rgba(16, 185, 129, 0.2);
  border: 1px solid rgba(52, 211, 153, 0.35);
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 500;
  color: #6EE7B7;
}

.hero-badge-icon {
  font-size: 13px;
  color: #34D399;
}

.security-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.security-col {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
}

.col-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.col-icon {
  font-size: 16px;
}

.col-icon.primary {
  color: #60A5FA;
}

.col-icon.info {
  color: #38BDF8;
}

.col-icon.warning {
  color: #FBBF24;
}

.col-title {
  margin: 0;
  font-size: 14.5px;
  font-weight: 600;
  color: #F8FAFC;
}

.col-desc {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #94A3B8;
}

.col-desc code {
  padding: 2px 5px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  font-family: var(--flow-font-mono);
  color: #38BDF8;
}

.code-tag {
  cursor: pointer;
  margin: 0 4px;
  font-family: var(--flow-font-mono);
  font-size: 12px;
  background: rgba(37, 99, 235, 0.3);
  border-color: rgba(96, 165, 250, 0.5);
  color: #BFDBFE;
  transition: all 0.2s ease;
}

.code-tag:hover {
  background: rgba(37, 99, 235, 0.5);
  color: #FFFFFF;
}

.copy-tag-icon {
  margin-left: 4px;
  font-size: 11px;
}

/* 凭据表格卡片 */
.secrets-table-card {
  border-radius: var(--flow-border-radius-lg);
  border: 1px solid var(--flow-border-color);
  background: var(--flow-bg-card);
  box-shadow: var(--flow-shadow-light);
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 16px;
  font-weight: 650;
  color: var(--flow-text-title);
}

.title-icon {
  color: var(--flow-color-primary);
}

.count-badge {
  border-radius: 9999px;
  padding: 0 8px;
  font-weight: 600;
}

.key-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.key-icon {
  color: #F59E0B;
  font-size: 14px;
}

.key-name {
  font-family: var(--flow-font-mono);
  font-weight: 600;
  font-size: 13.5px;
  color: var(--flow-text-title);
}

.quick-copy-btn {
  color: var(--flow-text-disabled);
  opacity: 0.6;
}

.quick-copy-btn:hover {
  opacity: 1;
  color: var(--flow-color-primary);
}

.masked-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.masked-tag {
  display: inline-block;
  padding: 3px 8px;
  background: #F1F5F9;
  border: 1px solid #CBD5E1;
  border-radius: 4px;
  font-family: var(--flow-font-mono);
  font-size: 12.5px;
  letter-spacing: 1px;
  color: #334155;
  width: fit-content;
}

.masked-tip {
  font-size: 11px;
  color: var(--flow-text-disabled);
  white-space: nowrap;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--flow-color-success);
  font-weight: 500;
  white-space: nowrap;
}

.status-text {
  color: #059669;
  white-space: nowrap;
}

.actions-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  white-space: nowrap;
}

/* 模态框自定义头部与底部 */
.modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 16px;
  margin-bottom: 20px;
  border-bottom: 1px solid var(--flow-border-color);
}

.modal-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: #FEF3C7;
  color: #D97706;
  border-radius: 10px;
  font-size: 20px;
}

.modal-title {
  margin: 0;
  font-size: 17px;
  font-weight: 650;
  color: var(--flow-text-title);
}

.modal-desc {
  font-size: 12.5px;
  color: var(--flow-text-secondary);
}

.input-prefix-icon {
  color: var(--flow-text-disabled);
}

.input-help {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--flow-text-secondary);
}

.input-help code {
  padding: 2px 4px;
  background: #F1F5F9;
  border-radius: 3px;
  font-family: var(--flow-font-mono);
  font-size: 11px;
  color: var(--flow-color-primary);
}

.form-security-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #ECFDF5;
  border: 1px solid #A7F3D0;
  border-radius: 6px;
  font-size: 12px;
  color: #065F46;
  margin-top: 12px;
}

.alert-icon {
  font-size: 14px;
  color: #10B981;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 20px;
  border-top: 1px solid var(--flow-border-color);
}
</style>
