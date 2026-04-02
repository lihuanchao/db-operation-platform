<template>
  <AppLayout>
    <div class="page-header">
      <h2>{{ title }}</h2>
      <el-button @click="goBack">返回任务列表</el-button>
    </div>

    <el-card v-loading="store.detailLoading" shadow="never" class="meta-card">
      <el-descriptions :column="3" border v-if="task">
        <el-descriptions-item label="任务ID">{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ task.task_type === 'sql' ? 'SQL' : 'MyBatis' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ task.created_at }}</el-descriptions-item>
        <el-descriptions-item label="数据库IP">{{ task.database_host }}</el-descriptions-item>
        <el-descriptions-item label="库名">{{ task.database_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="statusTagType(task.status)">{{ statusText(task.status) }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <el-alert
        v-if="task?.status === 'failed' && task.error_message"
        type="error"
        :title="task.error_message"
        show-icon
        style="margin-top: 12px"
      />
    </el-card>

    <el-card shadow="never" class="result-card">
      <template #header>
        <div class="card-header">
          <span>写法优化</span>
        </div>
      </template>
      <div class="compare-box">
        <div class="compare-column">
          <div class="column-header">
            <h4>原文</h4>
            <CopyButton v-if="originalContent" :text="originalContent" />
          </div>
          <div ref="originalPaneRef" class="code-pane" @scroll="syncFromOriginal">
            <div class="code-inner">
              <div
                v-for="(row, index) in diffRows"
                :key="`o-${index}`"
                class="code-row"
              >
                <span class="line-no">{{ index + 1 }}</span>
                <span class="line-content" v-html="row.originalHtml"></span>
              </div>
            </div>
          </div>
        </div>
        <div class="compare-column">
          <div class="column-header">
            <h4>最终优化后</h4>
            <CopyButton v-if="optimizedContent && optimizedContent !== '-'" :text="optimizedContent" />
          </div>
          <div ref="optimizedPaneRef" class="code-pane" @scroll="syncFromOptimized">
            <div class="code-inner">
              <div
                v-for="(row, index) in diffRows"
                :key="`n-${index}`"
                class="code-row"
              >
                <span class="line-no">{{ index + 1 }}</span>
                <span class="line-content" v-html="row.optimizedHtml"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" class="result-card">
      <template #header>
        <div class="card-header">
          <span>索引推荐</span>
          <CopyButton v-if="indexRecommendation && indexRecommendation !== '无需新增索引'" :text="indexRecommendation" />
        </div>
      </template>
      <pre class="suggestion-text">{{ indexRecommendation }}</pre>
    </el-card>

    <el-card shadow="never" class="result-card">
      <template #header>
        <div class="card-header">
          <span>命中规则</span>
        </div>
      </template>
      <div class="rule-list">
        <div v-for="rule in matchedRuleList" :key="rule" class="rule-item">
          {{ rule }}
        </div>
        <span v-if="matchedRuleList.length === 0" class="empty-rule">未识别命中规则</span>
      </div>
    </el-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import CopyButton from '@/components/Common/CopyButton.vue'
import { useOptimizationTaskStore } from '@/stores/optimizationTask'
import type { OptimizationTaskStatus } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useOptimizationTaskStore()
const timer = ref<number | null>(null)
const originalPaneRef = ref<HTMLElement | null>(null)
const optimizedPaneRef = ref<HTMLElement | null>(null)
const isSyncingScroll = ref(false)

const RULE_LABELS: Record<string, string> = {
  rule01: '投影下推：禁止 SELECT *，仅选择必要列。',
  rule02: '选择条件下推：将 WHERE 条件尽可能下沉到子查询或派生表内部。',
  rule03: '连接优化：优化 Join 顺序，避免笛卡尔积，处理数据倾斜。',
  rule04: '索引友好性：确保 WHERE/JOIN 列可直接利用索引。',
  rule05: '分区裁剪：若表已分区，确保查询条件包含分区键。',
  rule06: 'EXISTS vs IN：大表子查询优先推荐 EXISTS。',
  rule07: '聚合/排序下推：在子查询中提前完成 GROUP BY 或 ORDER BY。',
  rule08: '避免列函数：避免 WHERE YEAR(col)=... 或 WHERE FUNC(col)=...，改为范围查询。',
  rule09: '分组优化：减少参与分组的冗余列。',
  rule10: '子查询去重：提取重复子查询为 CTE。',
  rule11: '禁止随机排序：移除 ORDER BY RAND()。',
  rule12: '限制结果集：适当添加 LIMIT。',
  rule13: '简化嵌套：拆解过深的嵌套查询。',
  rule14: '分组键优化：尽量基于主键或分区键分组。',
  rule15: '防止数据倾斜：针对大表关联提出防倾斜建议。'
}

const task = computed(() => store.currentTask)

const title = computed(() => {
  if (task.value?.task_type === 'mybatis') {
    return '查看 ORM XML 文件优化结果'
  }
  return '查看 SQL 优化结果'
})

const optimizedContent = computed(() => {
  if (!task.value) return '-'
  return task.value.optimized_content || task.value.object_content || '-'
})

const originalContent = computed(() => {
  return task.value?.object_content || ''
})

interface DiffRow {
  originalHtml: string
  optimizedHtml: string
}

const diffRows = computed<DiffRow[]>(() => {
  const original = originalContent.value || ''
  const optimized = optimizedContent.value === '-' ? '' : optimizedContent.value
  return buildDiffRows(original, optimized)
})

const matchedRuleList = computed(() => {
  const raw = task.value?.matched_rules || ''
  return raw
    .split(',')
    .map(item => item.trim().toLowerCase())
    .filter(Boolean)
    .map(ruleId => `${ruleId}：${RULE_LABELS[ruleId] || '未定义规则'}`)
})

const indexRecommendation = computed(() => {
  if (!task.value) return '-'
  return task.value.index_recommendation || '暂无索引推荐'
})

onMounted(async () => {
  const taskId = Number(route.params.id)
  if (!taskId) return
  await refreshTask(taskId)
})

onBeforeUnmount(() => {
  if (timer.value) {
    window.clearInterval(timer.value)
    timer.value = null
  }
})

async function refreshTask(taskId: number) {
  const detail = await store.fetchDetail(taskId)
  if (!detail) return

  if (detail.status === 'queued' || detail.status === 'running') {
    startPolling(taskId)
  } else if (timer.value) {
    window.clearInterval(timer.value)
    timer.value = null
  }
}

function startPolling(taskId: number) {
  if (timer.value) return
  timer.value = window.setInterval(() => {
    refreshTask(taskId)
  }, 3000)
}

function goBack() {
  router.push('/optimization-tasks')
}

function statusText(status: OptimizationTaskStatus) {
  if (status === 'queued') return '优化中'
  if (status === 'running') return '优化中'
  if (status === 'completed') return '完成'
  return '失败'
}

function statusTagType(status: OptimizationTaskStatus) {
  if (status === 'queued') return 'info'
  if (status === 'running') return 'warning'
  if (status === 'completed') return 'success'
  return 'danger'
}

function syncFromOriginal() {
  if (!originalPaneRef.value || !optimizedPaneRef.value || isSyncingScroll.value) return
  isSyncingScroll.value = true
  optimizedPaneRef.value.scrollTop = originalPaneRef.value.scrollTop
  requestAnimationFrame(() => {
    isSyncingScroll.value = false
  })
}

function syncFromOptimized() {
  if (!originalPaneRef.value || !optimizedPaneRef.value || isSyncingScroll.value) return
  isSyncingScroll.value = true
  originalPaneRef.value.scrollTop = optimizedPaneRef.value.scrollTop
  requestAnimationFrame(() => {
    isSyncingScroll.value = false
  })
}

function buildDiffRows(originalText: string, optimizedText: string): DiffRow[] {
  const a = originalText.split('\n')
  const b = optimizedText.split('\n')
  const n = a.length
  const m = b.length
  const dp: number[][] = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0))

  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      if (a[i] === b[j]) {
        dp[i][j] = dp[i + 1][j + 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1])
      }
    }
  }

  const rows: DiffRow[] = []
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      rows.push({
        originalHtml: escapeHtml(a[i]),
        optimizedHtml: escapeHtml(b[j]),
      })
      i += 1
      j += 1
    } else if (
      dp[i + 1][j + 1] >= dp[i + 1][j] &&
      dp[i + 1][j + 1] >= dp[i][j + 1]
    ) {
      const changed = buildInlineDiff(a[i], b[j])
      rows.push({
        originalHtml: changed.originalHtml,
        optimizedHtml: changed.optimizedHtml,
      })
      i += 1
      j += 1
    } else if (dp[i + 1][j] > dp[i][j + 1]) {
      rows.push({
        originalHtml: wrapChangedWholeLine(a[i]),
        optimizedHtml: '&nbsp;',
      })
      i += 1
    } else {
      rows.push({
        originalHtml: '&nbsp;',
        optimizedHtml: wrapChangedWholeLine(b[j]),
      })
      j += 1
    }
  }

  while (i < n) {
    rows.push({
      originalHtml: wrapChangedWholeLine(a[i]),
      optimizedHtml: '&nbsp;',
    })
    i += 1
  }

  while (j < m) {
    rows.push({
      originalHtml: '&nbsp;',
      optimizedHtml: wrapChangedWholeLine(b[j]),
    })
    j += 1
  }

  if (rows.length === 0) {
    rows.push({
      originalHtml: '&nbsp;',
      optimizedHtml: '&nbsp;',
    })
  }

  return rows
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function wrapChangedWholeLine(text: string): string {
  if (!text) return '&nbsp;'
  return escapeHtml(text)
}

function buildInlineDiff(originalLine: string, optimizedLine: string): { originalHtml: string; optimizedHtml: string } {
  const originalChars = Array.from(originalLine)
  const optimizedChars = Array.from(optimizedLine)

  let prefix = 0
  while (
    prefix < originalChars.length &&
    prefix < optimizedChars.length &&
    originalChars[prefix] === optimizedChars[prefix]
  ) {
    prefix += 1
  }

  let originalSuffix = originalChars.length - 1
  let optimizedSuffix = optimizedChars.length - 1
  while (
    originalSuffix >= prefix &&
    optimizedSuffix >= prefix &&
    originalChars[originalSuffix] === optimizedChars[optimizedSuffix]
  ) {
    originalSuffix -= 1
    optimizedSuffix -= 1
  }

  const originalPrefix = originalChars.slice(0, prefix).join('')
  const optimizedPrefix = optimizedChars.slice(0, prefix).join('')
  const originalMiddle = originalChars.slice(prefix, originalSuffix + 1).join('')
  const optimizedMiddle = optimizedChars.slice(prefix, optimizedSuffix + 1).join('')
  const originalTail = originalChars.slice(originalSuffix + 1).join('')
  const optimizedTail = optimizedChars.slice(optimizedSuffix + 1).join('')

  return {
    originalHtml: combineDiffParts(originalPrefix, originalMiddle, originalTail),
    optimizedHtml: combineDiffParts(optimizedPrefix, optimizedMiddle, optimizedTail)
  }
}

function combineDiffParts(prefix: string, middle: string, tail: string): string {
  const prefixHtml = escapeHtml(prefix)
  const middleHtml = escapeHtml(middle)
  const tailHtml = escapeHtml(tail)
  const result = `${prefixHtml}${middleHtml}${tailHtml}`
  return result || '&nbsp;'
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
}

.meta-card,
.result-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-item {
  padding: 10px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fafcff;
  color: #303133;
  line-height: 1.6;
  font-size: 13px;
}

.empty-rule {
  color: #909399;
}

.compare-box {
  display: flex;
  gap: 16px;
}

.compare-column {
  flex: 1;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px;
  min-width: 0;
}

.compare-column h4 {
  margin: 0 0 8px;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.suggestion-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', monospace;
  line-height: 1.6;
}

.code-pane {
  height: 380px;
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #fff;
}

.code-inner {
  min-width: 100%;
}

.code-row {
  display: flex;
  align-items: flex-start;
  min-height: 24px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.7;
}

.line-no {
  width: 42px;
  flex-shrink: 0;
  padding: 0 8px 0 10px;
  color: #9aa4b2;
  user-select: none;
  text-align: right;
}

.line-content {
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
  padding-right: 12px;
}

@media (max-width: 960px) {
  .compare-box {
    flex-direction: column;
  }
}
</style>
