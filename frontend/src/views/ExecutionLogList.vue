<template>
  <AppLayout>
    <div class="page-header">
      <h2>执行日志</h2>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="归档任务">
          <el-select v-model="filters.task_id" placeholder="请选择归档任务" clearable style="width: 250px">
            <el-option
              v-for="task in taskList"
              :key="task.id"
              :label="task.task_name"
              :value="task.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="执行状态">
          <el-select v-model="filters.status" placeholder="请选择执行状态" clearable style="width: 150px">
            <el-option label="失败" :value="0" />
            <el-option label="成功" :value="1" />
            <el-option label="执行中" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
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
      <el-table :data="store.list" v-loading="store.loading" stripe style="width: 100%">
        <el-table-column prop="task_name" label="任务名称" width="200">
          <template #default="{ row }">
            {{ row.task_name || '-' }}
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
        <el-table-column prop="log_file" label="日志文件">
          <template #default="{ row }">
            {{ row.log_file || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="200">
          <template #default="{ row }">
            <el-tooltip v-if="row.error_message" :content="row.error_message" placement="top">
              <span class="error-message">{{ row.error_message }}</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
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
              v-if="row.log_file"
              link
              type="primary"
              size="small"
              @click="handleDownload(row)"
            >
              <el-icon><Download /></el-icon>
              下载日志
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
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </el-card>

    <!-- 查看日志对话框 -->
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
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { Search, Refresh, Download, View } from '@element-plus/icons-vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useExecutionLogStore } from '@/stores/executionLog'
import { useArchiveTaskStore } from '@/stores/archiveTask'
import { getLogContent } from '@/api/executionLog'
import type { ExecutionLog, ArchiveTask } from '@/types'

const store = useExecutionLogStore()
const taskStore = useArchiveTaskStore()

const filters = ref({
  task_id: undefined as number | undefined,
  status: undefined as number | undefined
})

const logDialogVisible = ref(false)
const currentLog = ref<ExecutionLog | null>(null)
const logContent = ref('')
const refreshingLog = ref(false)
let refreshInterval: number | null = null

const taskList = computed(() => taskStore.list)

onMounted(async () => {
  await Promise.all([
    store.fetchList(),
    taskStore.fetchList()
  ])
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

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

async function handleViewLog(row: ExecutionLog) {
  currentLog.value = row
  logDialogVisible.value = true
  await refreshLogContent()

  // 如果正在执行，定时刷新日志
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (row.status === 2) {
    refreshInterval = window.setInterval(refreshLogContent, 3000)
  }
}

async function refreshLogContent() {
  if (!currentLog.value?.id) return

  refreshingLog.value = true
  try {
    const response = await getLogContent(currentLog.value.id)
    if (response.success && response.data) {
      logContent.value = response.data.content || ''

      // 更新当前日志状态
      await store.fetchList()

      // 检查是否还在执行中
      const updatedLog = store.list.find(log => log.id === currentLog.value?.id)
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
  store.setFilters(filters.value)
  store.fetchList()
}

function handleReset() {
  filters.value = {
    task_id: undefined,
    status: undefined
  }
  store.resetFilters()
  store.fetchList()
}

async function handleDownload(row: ExecutionLog) {
  if (!row.id) return
  await store.downloadLog(row.id)
}

function handlePageChange(page: number) {
  store.goToPage(page)
}

function handleSizeChange(size: number) {
  store.setPageSize(size)
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #1e3a5f;
}

.filter-card {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}

.error-message {
  display: block;
  max-width: 300px;
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
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
