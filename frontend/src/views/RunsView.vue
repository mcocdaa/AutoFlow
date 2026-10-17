<template>
  <div class="af-page">
    <PageHeader
      :title="t('runs.title')"
      :description="t('runs.desc')"
      :icon="HistoryOutlined"
    >
      <template #actions>
        <a-button :disabled="selectedRunIds.length !== 2" @click="openDiff">
          <template #icon><DiffOutlined /></template>
          {{ t('runs.compare') }}{{ selectedRunIds.length === 2 ? '' : t('runs.compareHint') }}
        </a-button>
        <a-button :loading="store.loading" @click="refresh">
          <template #icon><ReloadOutlined /></template>
          {{ t('common.refresh') }}
        </a-button>
      </template>
    </PageHeader>

    <a-alert v-if="store.error" :message="store.error" type="error" show-icon class="page-alert" />

    <a-card>
      <a-table
        v-if="store.runs.length > 0"
        :data-source="store.runs"
        :row-key="rowKey"
        :row-selection="rowSelection"
        :pagination="{ pageSize: 10, hideOnSinglePage: true }"
      >
        <a-table-column :title="t('runs.col.flow')" data-index="flow_name" />
        <a-table-column :title="t('runs.col.status')" width="96">
          <template #default="{ record }">
            <a-tag :color="runStatusMeta(record.status).color">
              {{ runStatusMeta(record.status).text }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column :title="t('runs.col.startedAt')" width="200">
          <template #default="{ record }">{{ formatTime(record.started_at) }}</template>
        </a-table-column>
        <a-table-column :title="t('runs.col.duration')" width="110">
          <template #default="{ record }">
            {{ record.duration_ms !== null ? record.duration_ms + ' ms' : '—' }}
          </template>
        </a-table-column>
        <a-table-column :title="t('runs.col.steps')" width="80">
          <template #default="{ record }">{{ record.steps.length }}</template>
        </a-table-column>
        <a-table-column :title="t('runs.col.actions')" width="150">
          <template #default="{ record }">
            <a-space :size="4">
              <a-button type="link" size="small" @click="openDetail(record.run_id)">
                {{ t('common.view') }}
              </a-button>
              <a-popconfirm
                :title="t('runs.deleteConfirm')"
                :ok-text="t('common.delete')"
                :cancel-text="t('common.cancel')"
                @confirm="remove(record.run_id)"
              >
                <a-button type="link" size="small" danger>{{ t('common.delete') }}</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </a-table>
      <a-skeleton v-else-if="store.loading" active :paragraph="{ rows: 4 }" />
      <a-empty v-else :description="t('runs.empty')" :image="emptyImage" />
    </a-card>

    <a-drawer v-model:open="detailOpen" :title="t('runs.detailTitle')" width="720">
      <template #extra>
        <a-button
          v-if="detailRun"
          :loading="replayLoading"
          @click="replay"
        >
          <template #icon><RedoOutlined /></template>
          {{ t('runs.replay') }}
        </a-button>
      </template>
      <a-spin :spinning="detailLoading">
        <ResultsPanel
          :run="detailRun"
          :error="detailError"
          :forkable="!!detailRun && detailRun.status !== 'running'"
          @fork="forkFromStep"
        />
      </a-spin>
    </a-drawer>

    <a-modal
      v-model:open="diffOpen"
      :title="t('runs.diffTitle')"
      width="860"
      :footer="null"
    >
      <a-spin :spinning="diffLoading">
        <RunDiffPanel :diff="diffData" />
      </a-spin>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Empty, message } from 'ant-design-vue'
import {
  DiffOutlined,
  HistoryOutlined,
  RedoOutlined,
  ReloadOutlined,
} from '@ant-design/icons-vue'
import { getErrorMessage } from '../api'
import { forkDebugSession } from '../api/debug'
import { fetchRun as apiFetchRun, fetchRunDiff, replayRun } from '../api/runs'
import { RUN_STATUS_META } from '../constants/run-status'
import { useI18n } from '../i18n'
import { useRunsStore } from '../stores/runs'
import PageHeader from '../components/shared/PageHeader.vue'
import ResultsPanel from '../components/run/ResultsPanel.vue'
import RunDiffPanel from '../components/run/RunDiffPanel.vue'
import type { RunDiff, RunResult, RunStatus } from '../types/runs'

const { locale, t } = useI18n()
const store = useRunsStore()
const router = useRouter()

const emptyImage = Empty.PRESENTED_IMAGE_SIMPLE
const detailOpen = ref(false)
const detailLoading = ref(false)
const detailError = ref<string | null>(null)
const detailRun = ref<RunResult | null>(null)

const selectedRunIds = ref<string[]>([])
const rowSelection = computed(() => ({
  selectedRowKeys: selectedRunIds.value,
  onChange: (keys: (string | number)[]) => {
    selectedRunIds.value = keys.map(String)
  },
}))

const diffOpen = ref(false)
const diffLoading = ref(false)
const diffData = ref<RunDiff | null>(null)

const rowKey = (record: RunResult): string => record.run_id
const runStatusMeta = (status: RunStatus) => RUN_STATUS_META[status]

const formatTime = (value: string | null): string => {
  if (!value) return '—'
  return new Date(value).toLocaleString(locale.value === 'en' ? 'en-US' : 'zh-CN', { hour12: false })
}

const refresh = () => {
  store.fetchRuns().catch(() => {})
}

const openDetail = async (runId: string) => {
  detailOpen.value = true
  detailLoading.value = true
  detailError.value = null
  detailRun.value = null
  try {
    detailRun.value = await apiFetchRun(runId)
  } catch (err) {
    detailError.value = getErrorMessage(err)
  } finally {
    detailLoading.value = false
  }
}

const remove = async (runId: string) => {
  try {
    await store.removeRun(runId)
    selectedRunIds.value = selectedRunIds.value.filter((id) => id !== runId)
    message.success(t('runs.deletedMsg'))
  } catch (err) {
    message.error(getErrorMessage(err))
  }
}

const openDiff = async () => {
  if (selectedRunIds.value.length !== 2) return
  const selected = store.runs
    .filter((run) => selectedRunIds.value.includes(run.run_id))
    .sort((a, b) => a.started_at.localeCompare(b.started_at))
  if (selected.length !== 2) {
    message.warning(t('runs.notExistMsg'))
    return
  }
  diffOpen.value = true
  diffLoading.value = true
  diffData.value = null
  try {
    diffData.value = await fetchRunDiff(selected[0].run_id, selected[1].run_id)
  } catch (err) {
    message.error(getErrorMessage(err))
    diffOpen.value = false
  } finally {
    diffLoading.value = false
  }
}

const forkLoading = ref(false)

const forkFromStep = async (nextStepIndex: number) => {
  if (!detailRun.value || forkLoading.value) return
  forkLoading.value = true
  try {
    const snapshot = await forkDebugSession(detailRun.value.run_id, nextStepIndex)
    message.success(t('runs.forkCreatedMsg'))
    detailOpen.value = false
    router.push({ path: '/debug', query: { session: snapshot.session_id } })
  } catch (err) {
    const text = getErrorMessage(err)
    if (text.includes('no stored request')) {
      message.warning(t('runs.noStoredReqFork'))
    } else {
      message.error(text)
    }
  } finally {
    forkLoading.value = false
  }
}

const replayLoading = ref(false)

const replay = async () => {
  if (!detailRun.value) return
  replayLoading.value = true
  try {
    const newRun = await replayRun(detailRun.value.run_id)
    detailRun.value = newRun
    detailError.value = null
    message.success(t('runs.replayDoneMsg', { id: newRun.run_id.slice(0, 8) }))
    store.fetchRuns().catch(() => {})
  } catch (err) {
    const text = getErrorMessage(err)
    if (text.includes('no stored request')) {
      message.warning(t('runs.noStoredReqReplay'))
    } else {
      message.error(text)
    }
  } finally {
    replayLoading.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.page-alert {
  margin-bottom: 24px;
}
</style>
