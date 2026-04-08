<template>
  <AppLayout>
    <div class="page-shell">
      <div class="page-header">
        <div>
          <h2>执行日志</h2>
          <p>统一查看归档任务和数据闪回的执行结果与日志文件。</p>
        </div>
      </div>

      <el-card shadow="never" class="filter-card">
        <el-form :model="filters" inline class="filter-form">
          <el-form-item label="日志类型">
            <el-select v-model="filters.log_type" class="filter-control" placeholder="请选择日志类型">
              <el-option label="全部日志" value="all" />
              <el-option label="归档任务" value="archive" />
              <el-option label="数据闪回" value="flashback" />
            </el-select>
          </el-form-item>
          <el-form-item label="任务名称">
            <el-input
              v-model="filters.task_name"
              class="filter-control filter-control--wide"
              clearable
              placeholder="请输入任务名称"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="执行状态">
            <el-select v-model="filters.status" class="filter-control" placeholder="请选择执行状态" clearable>
              <el-option label="失败" :value="0" />
              <el-option label="成功" :value="1" />
              <el-option label="执行中" :value="2" />
            </el-select>
          </el-form-item>
          <el-form-item class="filter-actions">
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="handleReset">
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="table-card">
        <el-table :data="store.list" v-loading="store.loading" stripe class="log-table">
          <el-table-column label="日志类型" width="120">
            <template #default="{ row }">
              <el-tag size="small" effect="plain" class="log-type-tag">
                {{ getLogTypeText(row.log_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="task_name" label="任务名称" min-width="240">
            <template #default="{ row }">
              <el-button
                v-if="row.detail_path"
                link
                type="primary"
                class="task-link"
                :data-detail-path="row.detail_path"
                @click="navigateToDetail(row.detail_path)"
              >
                {{ row.task_name || '-' }}
              </el-button>
              <span v-else>{{ row.task_name || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="执行状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="start_time" label="开始时间" width="180" />
          <el-table-column prop="end_time" label="结束时间" width="180">
            <template #default="{ row }">
              {{ row.end_time || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="log_file" label="日志文件" min-width="220">
            <template #default="{ row }">
              <span class="mono-text">{{ row.log_file || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误信息" min-width="220">
            <template #default="{ row }">
              <el-tooltip v-if="row.error_message" :content="row.error_message" placement="top">
                <span class="error-message">{{ row.error_message }}</span>
              </el-tooltip>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                size="small"
                @click="handleViewLog(row)"
              >
                <el-icon><View /></el-icon>
                查看日志
              </el-button>
              <el-button
                v-if="canDownloadLog(row)"
                link
                type="primary"
                size="small"
                @click="handleDownload(row)"
              >
                <el-icon><Download /></el-icon>
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="store.page"
          v-model:page-size="store.perPage"
          :total="store.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          class="table-pagination"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </el-card>
    </div>

    <el-dialog
      v-model="logDialogVisible"
      title="执行日志"
      width="800px"
      destroy-on-close
    >
      <div class="log-viewer">
        <div class="log-header">
          <el-button type="primary" size="small" @click="refreshLogContent" :loading="refreshingLog">
            <el-icon><Refresh /></el-icon>
            刷新日志
          </el-button>
        </div>
        <div class="log-content">
          <pre v-if="logContent">{{ logContent }}</pre>
          <el-empty v-else description="暂无日志内容" />
        </div>
      </div>
    </el-dialog>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Download, Refresh, Search, View } from '@element-plus/icons-vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { getLogContent } from '@/api/executionLog'
import { useExecutionLogStore } from '@/stores/executionLog'
import type { ExecutionLog, ExecutionLogFilterType, ExecutionLogRouteType } from '@/types'

const store = useExecutionLogStore()
const router = useRouter()

const defaultFilters = {
  task_id: undefined as number | undefined,
  log_type: 'all' as ExecutionLogFilterType,
  task_name: '',
  status: undefined as number | undefined
}

const filters = ref({
  ...defaultFilters
})

const logDialogVisible = ref(false)
const currentLog = ref<ExecutionLog | null>(null)
const logContent = ref('')
const refreshingLog = ref(false)
let refreshInterval: number | null = null

onMounted(async () => {
  syncUnifiedFilters()
  await store.fetchList()
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

function getLogTypeText(logType?: ExecutionLogRouteType) {
  return logType === 'flashback' ? '数据闪回' : '归档任务'
}

function normalizeLogType(logType?: ExecutionLogRouteType) {
  return logType ?? 'archive'
}

function syncUnifiedFilters() {
  store.resetFilters()
  store.setFilters({
    ...filters.value,
    task_id: undefined
  })
}

function canDownloadLog(row: ExecutionLog) {
  return typeof row.id === 'number'
    && (normalizeLogType(row.log_type) === 'archive' || normalizeLogType(row.log_type) === 'flashback')
}

function getStatusType(status: number) {
  switch (status) {
    case 1:
      return 'success'
    case 2:
      return 'warning'
    default:
      return 'danger'
  }
}

function getStatusText(status: number) {
  switch (status) {
    case 1:
      return '成功'
    case 2:
      return '执行中'
    default:
      return '失败'
  }
}

function navigateToDetail(detailPath: string) {
  router.push(detailPath)
}

async function handleViewLog(row: ExecutionLog) {
  currentLog.value = row
  logDialogVisible.value = true
  await refreshLogContent()

  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (row.status === 2) {
    refreshInterval = window.setInterval(refreshLogContent, 3000)
  }
}

async function refreshLogContent() {
  const logId = currentLog.value?.id
  if (!logId) return

  refreshingLog.value = true
  try {
    const logType = normalizeLogType(currentLog.value?.log_type)
    const response = await getLogContent(logType, logId)
    if (response.success && response.data) {
      logContent.value = response.data.content || ''

      await store.fetchList()

      const updatedLog = store.list.find((log) => (
        log.id === logId && normalizeLogType(log.log_type) === logType
      ))
      if (updatedLog) {
        currentLog.value = updatedLog
      }
      if (updatedLog && updatedLog.status !== 2 && refreshInterval) {
        clearInterval(refreshInterval)
        refreshInterval = null
      }
    }
  } catch (error) {
    console.error('刷新日志失败:', error)
  } finally {
    refreshingLog.value = false
  }
}

function handleSearch() {
  syncUnifiedFilters()
  store.fetchList()
}

function handleReset() {
  filters.value = {
    ...defaultFilters
  }
  syncUnifiedFilters()
  store.fetchList()
}

async function handleDownload(row: ExecutionLog) {
  if (!row.id) return
  await store.downloadLog(row.log_type ?? 'archive', row.id)
}

function handlePageChange(page: number) {
  store.goToPage(page)
}

function handleSizeChange(size: number) {
  store.setPageSize(size)
}
</script>

<style scoped>
.page-shell {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-header h2 {
  margin: 0;
  color: #1e3a5f;
  font-size: 22px;
}

.page-header p {
  margin: 6px 0 0;
  color: #5f7084;
  font-size: 13px;
}

.filter-card,
.table-card {
  border-radius: 8px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
}

.filter-control {
  width: 170px;
}

.filter-control--wide {
  width: 240px;
}

.filter-actions :deep(.el-form-item__content) {
  gap: 8px;
}

.log-table :deep(.el-table__cell) {
  padding: 8px 0;
}

.log-table :deep(.el-table__body tr:hover > td.el-table__cell) {
  background: #eef5ff;
}

.log-type-tag {
  font-weight: 600;
}

.task-link {
  padding: 0;
  font-weight: 600;
}

.mono-text {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
}

.table-pagination {
  margin-top: 12px;
  justify-content: flex-end;
}

.error-message {
  display: block;
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #f56c6c;
}

.log-viewer {
  max-height: 600px;
  display: flex;
  flex-direction: column;
}

.log-header {
  margin-bottom: 15px;
}

.log-content {
  flex: 1;
  overflow: auto;
  background: #1e1e1e;
  padding: 15px;
  border-radius: 4px;
}

.log-content pre {
  margin: 0;
  color: #d4d4d4;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

@media (max-width: 960px) {
  .filter-control,
  .filter-control--wide {
    width: 100%;
  }
}
</style>
