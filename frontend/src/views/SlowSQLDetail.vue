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

      <div class="content-panel">
        <div class="panel-header">
          <div class="header-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 7h16M4 12h16M4 17h7"/>
            </svg>
            SQL 写法优化
          </div>
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
            <CopyButton v-if="hasOptimizedSql" :text="optimizedSqlText" />
          </div>
        </div>
        <div class="compare-container">
          <div class="compare-side">
            <div class="side-header">
              <span class="side-label">原始 SQL</span>
              <CopyButton v-if="store.currentDetail" :text="originalSqlText" />
            </div>
            <div class="code-area">
              <pre>{{ originalSqlText }}</pre>
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
            </div>
            <div class="code-area">
              <pre v-if="hasOptimizedSql">{{ optimizedSqlText }}</pre>
              <el-empty v-else description="暂无优化结果，点击上方按钮获取" />
            </div>
          </div>
        </div>
      </div>

      <div class="content-panel">
        <div class="panel-header">
          <div class="header-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
            索引推荐
          </div>
          <CopyButton v-if="hasIndexRecommendation" :text="indexRecommendationText" />
        </div>
        <div class="index-content">
          <pre>{{ indexRecommendationText }}</pre>
        </div>
      </div>

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
            <span>暂无命中规则，点击上方按钮获取</span>
          </div>
        </div>
      </div>

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
import { computed, onMounted } from 'vue'
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

const originalSqlText = computed(() => store.currentDetail?.sample || '-')

const suggestionText = computed(() => (store.currentDetail?.optimized_suggestion || '').trim())

const optimizedSqlText = computed(() => {
  if (store.currentDetail?.optimized_content) {
    return store.currentDetail.optimized_content
  }

  const writingSection = (store.currentDetail?.writing_optimization || '').trim()
  const extractedFromWriting = extractOptimizedSqlFromSection(writingSection)
  if (extractedFromWriting) {
    return extractedFromWriting
  }

  const extractedFromSuggestion = extractOptimizedSqlFromSection(suggestionText.value)
  if (extractedFromSuggestion) {
    return extractedFromSuggestion
  }

  if (store.currentDetail?.is_optimized) {
    return originalSqlText.value
  }
  return '-'
})

const hasOptimizedSql = computed(() => optimizedSqlText.value !== '-')

const indexRecommendationText = computed(() => {
  const explicitIndex = (store.currentDetail?.index_recommendation || '').trim()
  if (explicitIndex) {
    return explicitIndex
  }

  const extractedIndex = extractIndexRecommendation(suggestionText.value)
  if (extractedIndex) {
    return extractedIndex
  }

  if (suggestionText.value) {
    return '无需新增索引'
  }
  return '暂无索引推荐，点击上方按钮获取'
})

const hasIndexRecommendation = computed(() => !indexRecommendationText.value.includes('暂无索引推荐'))

const matchedRuleList = computed(() => {
  const rawMatchedRules = (store.currentDetail?.matched_rules || '').trim()
  const ruleIds = rawMatchedRules
    ? rawMatchedRules.split(',').map(rule => rule.trim().toLowerCase()).filter(Boolean)
    : extractRuleIdsFromSuggestion(suggestionText.value)

  return Array.from(new Set(ruleIds)).map(ruleId => `${ruleId}：${RULE_LABELS[ruleId] || '未定义规则'}`)
})

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

function extractOptimizedSqlFromSection(text: string) {
  if (!text) return ''
  const blocks = text.match(/```(?:sql|mysql)?\s*[\s\S]*?```/ig) || []
  if (!blocks.length) return ''

  const lastBlock = blocks[blocks.length - 1]
  return lastBlock
    .replace(/```(?:sql|mysql)?/i, '')
    .replace(/```/g, '')
    .trim()
}

function extractIndexRecommendation(text: string) {
  if (!text) return ''
  const lines = text.split('\n')
  const start = lines.findIndex((line) => /索引推荐|索引策略|表结构改造/i.test(line))
  if (start < 0) {
    return extractIndexFallback(text)
  }

  const sectionLines: string[] = []
  for (let index = start + 1; index < lines.length; index += 1) {
    const current = lines[index]
    if (/^\s*#+\s*/.test(current) || /\*\*(命中规则|写法优化)\*\*/.test(current)) {
      break
    }
    if (current.trim()) {
      sectionLines.push(current)
    }
  }

  const section = sectionLines.join('\n').trim()
  return section || extractIndexFallback(text)
}

function extractIndexFallback(text: string) {
  const candidates = text
    .split('\n')
    .map(line => line.trim())
    .filter(line => /^(CREATE\s+INDEX|ALTER\s+TABLE)/i.test(line) || /\bADD\s+INDEX\b/i.test(line))

  return candidates.join('\n').trim()
}

function extractRuleIdsFromSuggestion(text: string) {
  if (!text) return []
  const matches = text.match(/rule\d{2}/ig) || []
  return matches.map(item => item.toLowerCase())
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
  align-items: center;
  gap: 12px;
}

.content-panel {
  margin-bottom: 20px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
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

.compare-container {
  display: flex;
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
  min-height: 180px;
  max-height: 340px;
  overflow: auto;
  padding: 12px 14px;
  background: #ffffff;
}

.code-area pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', 'SF Mono', monospace;
  font-size: 12px;
  line-height: 1.7;
  color: #1e293b;
}

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
  border-radius: 8px;
  padding: 12px 14px;
}

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
  border-radius: 8px;
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
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 120px;
  color: #94a3b8;
  font-size: 13px;
}

.empty-rules svg {
  width: 22px;
  height: 22px;
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

@media (max-width: 960px) {
  .compare-container {
    flex-direction: column;
  }

  .compare-divider {
    width: 100%;
    height: 44px;
    border-left: none;
    border-right: none;
    border-top: 1px solid #e2e8f0;
    border-bottom: 1px solid #e2e8f0;
  }

  .compare-divider svg {
    transform: rotate(90deg);
  }
}
</style>
