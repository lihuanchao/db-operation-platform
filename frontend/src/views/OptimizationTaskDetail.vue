<template>
  <AppLayout>
    <div class="page-container">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <div class="page-title-group">
            <h1 class="page-title">{{ title }}</h1>
            <span v-if="task" :class="['status-badge', `status-badge--${task.status}`]">
              {{ statusText(task.status) }}
            </span>
          </div>
        </div>
        <button class="back-btn" @click="goBack">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          返回
        </button>
      </div>

      <!-- 元信息面板 -->
      <div class="info-panel" v-loading="store.detailLoading">
        <div class="info-grid" v-if="task">
          <div class="info-item">
            <span class="info-label">任务 ID</span>
            <span class="info-value">#{{ task.id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">类型</span>
            <span :class="['type-badge', `type-badge--${task.task_type}`]">
              {{ task.task_type === 'sql' ? 'SQL' : 'MyBatis' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">数据库</span>
            <span class="info-value">{{ task.database_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">主机</span>
            <span class="info-value">{{ task.database_host }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建时间</span>
            <span class="info-value">{{ task.created_at }}</span>
          </div>
        </div>
        <div v-if="task?.status === 'failed' && task.error_message" class="error-banner">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>{{ task.error_message }}</span>
        </div>
      </div>

      <!-- SQL 对比面板 -->
      <div class="content-panel">
        <div class="panel-header">
          <div class="header-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 7h16M4 12h16M4 17h7"/>
            </svg>
            SQL 写法优化
          </div>
        </div>
        <div class="compare-container">
          <div class="compare-side">
            <div class="side-header">
              <span class="side-label">原始 SQL</span>
              <CopyButton v-if="originalContent" :text="originalContent" />
            </div>
            <div ref="originalPaneRef" class="code-area" @scroll="syncFromOriginal">
              <div class="code-content">
                <div
                  v-for="(row, index) in diffRows"
                  :key="`o-${index}`"
                  class="code-line"
                >
                  <span class="line-text" v-html="row.originalHtml"></span>
                </div>
                <div class="spacer" :style="{ height: `${originalPaneSpacer}px` }" />
              </div>
            </div>
          </div>
          <div class="compare-divider">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </div>
          <div class="compare-side">
            <div class="side-header">
              <span class="side-label">优化后 SQL</span>
              <CopyButton v-if="optimizedContent && optimizedContent !== '-'" :text="optimizedContent" />
            </div>
            <div ref="optimizedPaneRef" class="code-area" @scroll="syncFromOptimized">
              <div class="code-content">
                <div
                  v-for="(row, index) in diffRows"
                  :key="`n-${index}`"
                  class="code-line"
                >
                  <span class="line-text" v-html="row.optimizedHtml"></span>
                </div>
                <div class="spacer" :style="{ height: `${optimizedPaneSpacer}px` }" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 索引推荐面板 -->
      <div class="content-panel">
        <div class="panel-header">
          <div class="header-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
            索引推荐
          </div>
          <CopyButton v-if="indexRecommendation && indexRecommendation !== '无需新增索引'" :text="indexRecommendation" />
        </div>
        <div class="index-content">
          <pre>{{ indexRecommendation }}</pre>
        </div>
      </div>

      <!-- 命中规则面板 -->
      <div class="content-panel">
        <div class="panel-header">
          <div class="header-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            命中规则
            <span v-if="matchedRuleList.length > 0" class="rule-count">{{ matchedRuleList.length }}</span>
          </div>
        </div>
        <div class="rules-container">
          <div v-for="(rule, idx) in matchedRuleList" :key="idx" class="rule-card">
            <div class="rule-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <div class="rule-text">{{ rule }}</div>
          </div>
          <div v-if="matchedRuleList.length === 0" class="empty-rules">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/>
              <path d="M8 15s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/>
            </svg>
            <span>未识别命中规则</span>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
const originalPaneSpacer = ref(0)
const optimizedPaneSpacer = ref(0)

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
    return 'MyBatis 优化结果'
  }
  return 'SQL 优化结果'
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
  window.addEventListener('resize', syncPaneScrollRange)
  const taskId = Number(route.params.id)
  if (!taskId) return
  await refreshTask(taskId)
  await nextTick()
  syncPaneScrollRange()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncPaneScrollRange)
  if (timer.value) {
    window.clearInterval(timer.value)
    timer.value = null
  }
})

watch(diffRows, async () => {
  await nextTick()
  syncPaneScrollRange()
}, { immediate: true })

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
  if (status === 'queued') return '等待中'
  if (status === 'running') return '优化中'
  if (status === 'completed') return '已完成'
  return '失败'
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

function syncPaneScrollRange() {
  if (!originalPaneRef.value || !optimizedPaneRef.value) {
    return
  }
  originalPaneSpacer.value = 0
  optimizedPaneSpacer.value = 0
  requestAnimationFrame(() => {
    const originalHeight = originalPaneRef.value?.scrollHeight ?? 0
    const optimizedHeight = optimizedPaneRef.value?.scrollHeight ?? 0
    if (originalHeight === optimizedHeight) {
      return
    }
    if (originalHeight > optimizedHeight) {
      optimizedPaneSpacer.value = originalHeight - optimizedHeight
    } else {
      originalPaneSpacer.value = optimizedHeight - originalHeight
    }
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
.page-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 页面头部 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #475569;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.back-btn:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
  color: #1e293b;
}

.back-btn svg {
  width: 16px;
  height: 16px;
}

.page-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

/* 信息面板 */
.info-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 16px 20px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
  color: #1e293b;
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  font-size: 13px;
}

.error-banner svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

/* 内容面板 */
.content-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.header-title svg {
  width: 18px;
  height: 18px;
  color: #3b82f6;
}

.rule-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 600;
  border-radius: 10px;
}

/* 对比容器 */
.compare-container {
  display: flex;
  gap: 0;
}

.compare-side {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.side-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.side-label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.compare-divider {
  width: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  border-left: 1px solid #e2e8f0;
  border-right: 1px solid #e2e8f0;
}

.compare-divider svg {
  width: 18px;
  height: 18px;
  color: #94a3b8;
}

.code-area {
  height: 380px;
  overflow-y: auto;
  overflow-x: hidden;
  background: #ffffff;
}

.code-content {
  min-width: 100%;
}

.code-line {
  display: flex;
  align-items: flex-start;
  min-height: 24px;
  font-family: 'Consolas', 'Monaco', 'SF Mono', monospace;
  font-size: 12px;
  line-height: 1.7;
}

.line-text {
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
  padding: 0 16px;
  color: #1e293b;
}

.spacer {
  width: 1px;
  pointer-events: none;
}

/* 索引推荐 */
.index-content {
  padding: 14px 16px;
}

.index-content pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', 'SF Mono', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #1e293b;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  padding: 12px 14px;
}

/* 规则列表 */
.rules-container {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.rule-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #16a34a;
  flex-shrink: 0;
  margin-top: 1px;
}

.rule-icon svg {
  width: 18px;
  height: 18px;
}

.rule-text {
  flex: 1;
  font-size: 13px;
  line-height: 1.6;
  color: #166534;
}

.empty-rules {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  gap: 10px;
  color: #94a3b8;
}

.empty-rules svg {
  width: 48px;
  height: 48px;
  color: #cbd5e1;
}

.empty-rules span {
  font-size: 13px;
}

/* 徽章 */
.type-badge,
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 4px;
}

.type-badge--sql {
  background: #dbeafe;
  color: #1d4ed8;
}

.type-badge--mybatis {
  background: #d1fae5;
  color: #047857;
}

.status-badge--queued {
  background: #fef3c7;
  color: #92400e;
}

.status-badge--running {
  background: #fee2e2;
  color: #dc2626;
}

.status-badge--completed {
  background: #dcfce7;
  color: #15803d;
}

.status-badge--failed {
  background: #fee2e2;
  color: #dc2626;
}

/* 响应式 */
@media (max-width: 1200px) {
  .info-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 960px) {
  .compare-container {
    flex-direction: column;
  }

  .compare-divider {
    width: 100%;
    height: 40px;
    border-left: none;
    border-right: none;
    border-top: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
  }

  .info-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .header-left {
    flex-wrap: wrap;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
