<template>
  <AppLayout>
    <div class="page-shell">
      <div class="page-header">
        <div>
          <h2>数据闪回任务详情</h2>
          <p>查看任务摘要、结果文件、日志内容和下载入口。</p>
        </div>
        <el-button class="back-btn" @click="goBack">返回列表</el-button>
      </div>

      <el-card shadow="never" class="summary-card" v-loading="store.loading">
        <el-descriptions v-if="task" :column="3" border>
          <el-descriptions-item label="任务ID">{{ task.id }}</el-descriptions-item>
          <el-descriptions-item label="连接名称">{{ task.connection_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTagType(task.status)">{{ statusText(task.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数据库名">{{ task.database_name }}</el-descriptions-item>
          <el-descriptions-item label="表名">{{ task.table_name }}</el-descriptions-item>
          <el-descriptions-item label="mode">{{ task.mode || 'repl' }}</el-descriptions-item>
          <el-descriptions-item label="SQL 类型">{{ task.sql_type }}</el-descriptions-item>
          <el-descriptions-item label="输出类型">{{ task.work_type }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ task.created_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ task.start_datetime || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ task.stop_datetime || '-' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ task.updated_at || '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="暂无任务详情" />
      </el-card>

      <el-card shadow="never" class="artifact-card">
        <template #header>
          <div class="card-header">
            <span>结果文件</span>
          </div>
        </template>

        <div class="artifact-list" v-if="artifactList.length">
          <div v-for="artifact in artifactList" :key="artifact.id" class="artifact-item">
            <div class="artifact-meta">
              <strong>{{ artifact.name }}</strong>
              <span>{{ artifact.size }} bytes</span>
            </div>
            <el-button
              link
              type="primary"
              class="artifact-download-btn"
              :data-artifact-id="artifact.id"
              @click="handleDownloadArtifact(artifact.id)"
            >
              下载
            </el-button>
          </div>
        </div>
        <el-empty v-else description="暂无结果文件" />
      </el-card>

      <el-card shadow="never" class="log-card">
        <template #header>
          <div class="card-header">
            <span>执行日志</span>
            <el-button link type="primary" class="download-log-btn" @click="handleDownloadLog">下载日志</el-button>
          </div>
        </template>

        <div class="log-body">
          <pre class="log-content">{{ logContent || '暂无日志内容' }}</pre>
        </div>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useFlashbackTaskStore } from '@/stores/flashbackTask'
import type { FlashbackTaskStatus } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useFlashbackTaskStore()
const logContent = ref('')
const timer = ref<number | null>(null)

const taskId = computed(() => Number(route.params.id))
const task = computed(() => store.currentTask)
const artifactList = computed(() => {
  if (store.artifacts.length) {
    return store.artifacts
  }

  return store.currentTask?.artifacts ?? []
})

onMounted(async () => {
  if (!taskId.value) return
  await refreshDetail(taskId.value)
  await refreshLog(taskId.value)
})

onBeforeUnmount(() => {
  stopPolling()
})

async function refreshDetail(id: number) {
  const detail = await store.fetchDetail(id)
  if (!detail) return

  if (detail.status === 'queued' || detail.status === 'running') {
    startPolling(id)
  } else {
    stopPolling()
  }
}

async function refreshLog(id: number) {
  const res = await store.fetchLogContent(id)
  logContent.value = res?.content || ''
}

function startPolling(id: number) {
  if (timer.value) return
  timer.value = window.setInterval(() => {
    void refreshDetail(id)
    void refreshLog(id)
  }, 3000)
}

function stopPolling() {
  if (timer.value) {
    window.clearInterval(timer.value)
    timer.value = null
  }
}

function goBack() {
  router.push('/flashback-tasks')
}

function statusText(status: FlashbackTaskStatus) {
  switch (status) {
    case 'queued':
      return '排队中'
    case 'running':
      return '执行中'
    case 'completed':
      return '已完成'
    default:
      return '失败'
  }
}

function statusTagType(status: FlashbackTaskStatus) {
  switch (status) {
    case 'queued':
      return 'info'
    case 'running':
      return 'warning'
    case 'completed':
      return 'success'
    default:
      return 'danger'
  }
}

async function handleDownloadArtifact(artifactId: string) {
  if (!taskId.value) return
  await store.downloadArtifact(taskId.value, artifactId)
}

async function handleDownloadLog() {
  if (!taskId.value) return
  await store.downloadLog(taskId.value)
}
</script>

<style scoped>
.page-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.page-header h2 {
  margin: 0;
  color: #162135;
  font-size: 22px;
  font-weight: 700;
}

.page-header p {
  margin: 6px 0 0;
  color: #627089;
  font-size: 13px;
}

.summary-card,
.artifact-card,
.log-card {
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  box-shadow: 0 10px 26px rgba(15, 42, 61, 0.05);
}

.summary-card :deep(.el-card__body),
.artifact-card :deep(.el-card__body),
.log-card :deep(.el-card__body) {
  padding: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 700;
  color: #162135;
}

.artifact-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.artifact-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 12px;
  border: 1px solid #e1e8f1;
  border-radius: 8px;
  background: #fbfdff;
}

.artifact-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.artifact-meta strong {
  color: #17324d;
  font-size: 14px;
}

.artifact-meta span {
  color: #6a7689;
  font-size: 12px;
}

.log-body {
  min-height: 180px;
}

.log-content {
  margin: 0;
  padding: 12px;
  border: 1px solid #e1e8f1;
  border-radius: 8px;
  background: #f9fbfe;
  color: #203246;
  font-family: 'Consolas', 'Monaco', monospace;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
