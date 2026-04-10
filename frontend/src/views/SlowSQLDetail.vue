<template>
  <AppLayout>
    <div class="page-shell">
      <div class="page-header">
        <h2>慢SQL详情</h2>
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
      </div>

      <el-card v-loading="store.detailLoading" class="detail-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>基本信息</span>
          </div>
        </template>
        <el-descriptions :column="2" border v-if="store.currentDetail">
          <el-descriptions-item label="Checksum">
            <code>{{ store.currentDetail.checksum }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="主机">
            <el-tag>{{ store.currentDetail.host }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="数据库">
            {{ store.currentDetail.database_name }}
          </el-descriptions-item>
          <el-descriptions-item label="用户">
            {{ store.currentDetail.user_max }}
          </el-descriptions-item>
          <el-descriptions-item label="平均时间">
            <el-tag type="danger">{{ store.currentDetail.avg_time.toFixed(2) }}秒</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最大时间">
            {{ store.currentDetail.max_time?.toFixed(2) }}秒
          </el-descriptions-item>
          <el-descriptions-item label="最小时间">
            {{ store.currentDetail.min_time?.toFixed(2) }}秒
          </el-descriptions-item>
          <el-descriptions-item label="总计时间">
            {{ store.currentDetail.total_time?.toFixed(2) }}秒
          </el-descriptions-item>
          <el-descriptions-item label="执行次数">
            {{ store.currentDetail.execution_count }}
          </el-descriptions-item>
          <el-descriptions-item label="最近出现">
            {{ formatDate(store.currentDetail.last_seen) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="detail-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>SQL语句</span>
            <CopyButton v-if="store.currentDetail" :text="store.currentDetail.sample" />
          </div>
        </template>
        <div class="sql-content">
          <p class="sql-preview">{{ store.currentDetail?.sample || '-' }}</p>
        </div>
      </el-card>

      <el-card class="detail-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>优化建议</span>
            <div class="header-actions">
              <el-button
                v-if="!store.currentDetail?.is_optimized"
                type="warning"
                :loading="store.optimizeLoading"
                @click="handleOptimize"
              >
                <el-icon><MagicStick /></el-icon>
                获取优化建议
              </el-button>
              <CopyButton
                v-if="store.currentDetail?.optimized_suggestion"
                :text="store.currentDetail.optimized_suggestion"
              />
            </div>
          </div>
        </template>
        <div class="suggestion-content">
          <div v-if="store.currentDetail?.optimized_suggestion" class="markdown-body">
            <div v-html="formatSuggestion(store.currentDetail.optimized_suggestion)"></div>
          </div>
          <el-empty v-else description="暂无优化建议，点击上方按钮获取" />
        </div>
      </el-card>

      <div class="action-bar">
        <el-button type="success" @click="handleDownload" v-if="store.currentDetail">
          <el-icon><Download /></el-icon>
          下载Markdown格式报告
        </el-button>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, MagicStick, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import CopyButton from '@/components/Common/CopyButton.vue'
import { useSlowSqlStore } from '@/stores/slowSql'
import { downloadSlowSQL } from '@/api/slowSql'

const route = useRoute()
const router = useRouter()
const store = useSlowSqlStore()

onMounted(() => {
  const checksum = route.params.checksum as string
  if (checksum) {
    store.fetchDetail(checksum)
  }
})

function goBack() {
  router.push('/slow-sqls')
}

function formatDate(date: string | Date) {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleString('zh-CN')
}

function formatSuggestion(text: string) {
  return text.replace(/\n/g, '<br>')
}

async function handleOptimize() {
  const checksum = route.params.checksum as string
  if (!checksum) return
  try {
    await store.optimize(checksum)
    ElMessage.success('优化成功')
  } catch {
    // Error already handled by interceptor
  }
}

function handleDownload() {
  const checksum = route.params.checksum as string
  if (checksum) {
    downloadSlowSQL(checksum)
  }
}
</script>

<style scoped>
.page-shell {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
}

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

.detail-card {
  width: 100%;
  max-width: 100%;
  margin-bottom: 20px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.sql-content {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 10px 12px;
  overflow: hidden;
}

.sql-preview {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-all;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  text-overflow: ellipsis;
}

.suggestion-content {
  min-height: 100px;
}

.markdown-body {
  line-height: 1.8;
}

.markdown-body h3 {
  margin-top: 1.5rem;
  margin-bottom: 1rem;
  color: #0ea5e9;
}

.markdown-body h4 {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.markdown-body ul {
  margin-bottom: 1rem;
}

.action-bar {
  margin-top: 20px;
}

code {
  display: inline-block;
  max-width: 100%;
  word-break: break-all;
}

:deep(.el-card__body) {
  overflow-x: hidden;
}

:deep(.el-descriptions__body) {
  width: 100%;
}

:deep(.el-descriptions__cell) {
  word-break: break-all;
}
</style>
