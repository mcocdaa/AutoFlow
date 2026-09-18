<template>
  <div class="af-page">
    <PageHeader
      title="运行历史"
      description="查看与删除历史运行，记录随 run.json 落盘保存"
      :icon="HistoryOutlined"
    >
      <template #actions>
        <a-button :disabled="selectedRunIds.length !== 2" @click="openDiff">
          <template #icon><DiffOutlined /></template>
          对比{{ selectedRunIds.length === 2 ? '' : '（选 2 条）' }}
        </a-button>
        <a-button :loading="store.loading" @click="refresh">
          <template #icon><ReloadOutlined /></template>
          刷新
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
        <a-table-column title="流程" data-index="flow_name" />
        <a-table-column title="状态" width="96">
          <template #default="{ record }">
            <a-tag :color="runStatusMeta(record.status).color">
              {{ runStatusMeta(record.status).text }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="开始时间" width="200">
          <template #default="{ record }">{{ formatTime(record.started_at) }}</template>
        </a-table-column>
        <a-table-column title="耗时" width="110">
          <template #default="{ record }">
            {{ record.duration_ms !== null ? record.duration_ms + ' ms' : '—' }}
          </template>
        </a-table-column>
        <a-table-column title="步骤" width="80">
          <template #default="{ record }">{{ record.steps.length }}</template>
        </a-table-column>
        <a-table-column title="操作" width="150">
          <template #default="{ record }">
            <a-space :size="4">
              <a-button type="link" size="small" @click="openDetail(record.run_id)">
                查看
              </a-button>
              <a-popconfirm
                title="删除该运行记录及其产物？"
                ok-text="删除"
                cancel-text="取消"
                @confirm="remove(record.run_id)"
              >
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </a-table-column>
      </a-table>
      <a-skeleton v-else-if="store.loading" active :paragraph="{ rows: 4 }" />
      <a-empty v-else description="暂无运行记录" :image="emptyImage" />
    </a-card>

    <a-drawer v-model:open="detailOpen" title="执行详情" width="720">
      <template #extra>
        <a-button
          v-if="detailRun"
          :loading="replayLoading"
          @click="replay"
        >
          <template #icon><RedoOutlined /></template>
          回放
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
      title="运行对比"
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
import { useRunsStore } from '../stores/runs'
import PageHeader from '../components/shared/PageHeader.vue'
import ResultsPanel from '../components/run/ResultsPanel.vue'
import RunDiffPanel from '../components/run/RunDiffPanel.vue'
import type { RunDiff, RunResult, RunStatus } from '../types/runs'

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
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
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
    message.success('已删除该运行记录')
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
    message.warning('所选运行已不存在，请刷新后重试')
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
    message.success('已创建分叉调试会话')
    detailOpen.value = false
    router.push({ path: '/debug', query: { session: snapshot.session_id } })
  } catch (err) {
    const text = getErrorMessage(err)
    if (text.includes('no stored request')) {
      message.warning('该运行没有保存请求（旧版本运行），无法分叉')
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
    message.success(`回放完成：${newRun.run_id.slice(0, 8)}`)
    store.fetchRuns().catch(() => {})
  } catch (err) {
    const text = getErrorMessage(err)
    if (text.includes('no stored request')) {
      message.warning('该运行没有保存请求（旧版本运行），无法回放')
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
