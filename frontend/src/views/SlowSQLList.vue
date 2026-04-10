<template>
  <AppLayout>
    <div class="page-container">

      <!-- 高级筛选 -->
      <div class="advanced-filter">
        <div class="filter-row">
          <div class="filter-item">
            <label>主机</label>
            <input type="text" v-model="localFilters.host" placeholder="筛选主机" />
          </div>
          <div class="filter-item">
            <label>数据库</label>
            <input type="text" v-model="localFilters.database_name" placeholder="筛选数据库" />
          </div>
          <div class="filter-item">
            <label>优化状态</label>
            <select v-model="localFilters.is_optimized">
              <option value="">全部</option>
              <option value="0">待优化</option>
              <option value="1">已优化</option>
            </select>
          </div>
          <div class="filter-item">
            <label>时间范围</label>
            <select v-model="localFilters.time_range" @change="handleTimeRangeChange">
              <option value="">不限</option>
              <option value="1h">最近1小时</option>
              <option value="today">今天</option>
              <option value="7d">最近7天</option>
              <option value="30d">最近30天</option>
            </select>
          </div>
          <div class="filter-buttons">
            <button class="btn-filter" @click="handleSearch">筛选</button>
            <button class="btn-reset" @click="handleReset">重置</button>
          </div>
        </div>
      </div>

      <!-- 表格容器 -->
      <div class="table-container">
        <div class="table-header">
          <span class="table-title">慢SQL记录</span>
          <div class="table-actions">
            <button class="btn-action btn-action--warning" :disabled="selectedIds.length === 0" @click="handleBatchOptimize">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
              </svg>
              批量优化
            </button>
            <button class="btn-action btn-action--success" :disabled="selectedIds.length === 0" @click="handleBatchDownload">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              批量下载
            </button>
          </div>
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th class="th-checkbox">
                  <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
                </th>
                <th>主机</th>
                <th>数据库</th>
                <th>SQL语句</th>
                <th>执行次数</th>
                <th>平均时间</th>
                <th>最近出现</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in store.list" :key="item.checksum">
                <td class="td-checkbox">
                  <input type="checkbox" :checked="isSelected(item.checksum)" @change="toggleSelect(item.checksum)" />
                </td>
                <td><span class="host-badge">{{ item.host }}</span></td>
                <td>{{ item.database_name }}</td>
                <td class="td-sql">
                  <span class="sql-text">{{ truncateSql(item.sample) }}</span>
                </td>
                <td>{{ item.execution_count }}</td>
                <td><span class="time-badge">{{ item.avg_time.toFixed(2) }}s</span></td>
                <td class="td-time">{{ formatDate(item.last_seen) }}</td>
                <td>
                  <span :class="['status-badge', item.is_optimized ? 'status-badge--optimized' : 'status-badge--pending']">
                    {{ item.is_optimized ? '已优化' : '待优化' }}
                  </span>
                </td>
                <td class="td-actions">
                  <button class="btn-link" @click="goToDetail(item.checksum)">详情</button>
                  <button
                    v-if="!item.is_optimized"
                    class="btn-link btn-link--warning"
                    :disabled="optimizingIds.includes(item.checksum)"
                    @click="handleOptimize(item)"
                  >
                    {{ optimizingIds.includes(item.checksum) ? '优化中...' : '优化' }}
                  </button>
                  <button class="btn-link btn-link--success" @click="handleDownload(item.checksum)">下载</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div class="pagination" v-if="store.pagination">
          <span class="pagination-info">共 {{ store.pagination.total }} 条</span>
          <div class="pagination-buttons">
            <button class="page-btn" :disabled="store.pagination.page <= 1" @click="handlePageChange(store.pagination.page - 1, store.pagination.per_page)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M15 18l-6-6 6-6"/>
              </svg>
            </button>
            <button
            v-for="p in visiblePages"
            :key="p"
            :class="['page-btn', { active: p === store.pagination.page }]"
            @click="handlePageChange(p, store.pagination.per_page)"
          >
            {{ p }}
          </button>
            <button class="page-btn" :disabled="store.pagination.page >= totalPages" @click="handlePageChange(store.pagination.page + 1, store.pagination.per_page)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18l6-6-6-6"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useSlowSqlStore } from '@/stores/slowSql'
import { downloadSlowSQL, batchDownloadSlowSQLs } from '@/api/slowSql'
import type { SlowSQL } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const store = useSlowSqlStore()

const selectedIds = ref<string[]>([])
const optimizingIds = ref<string[]>([])

const localFilters = ref({
  host: '',
  database_name: '',
  time_range: '',
  is_optimized: '',
  ts_min: '',
  ts_max: '',
})

const showCustomTime = computed(() => localFilters.value.time_range === 'custom')

const totalPages = computed(() => {
  if (!store.pagination) return 1
  return Math.ceil(store.pagination.total / store.pagination.per_page)
})

const visiblePages = computed(() => {
  if (!store.pagination) return [1]
  const pages = []
  const start = Math.max(1, store.pagination.page - 2)
  const end = Math.min(totalPages.value, start + 4)
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

const isAllSelected = computed(() => {
  return store.list.length > 0 && selectedIds.value.length === store.list.length
})

function isSelected(checksum: string) {
  return selectedIds.value.includes(checksum)
}

function toggleSelect(checksum: string) {
  const idx = selectedIds.value.indexOf(checksum)
  if (idx >= 0) {
    selectedIds.value.splice(idx, 1)
  } else {
    selectedIds.value.push(checksum)
  }
  // Update store selection state
  store.list.forEach(item => {
    ;(item as any)._selected = selectedIds.value.includes(item.checksum)
  })
}

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = store.list.map(item => item.checksum)
  }
  // Update store selection state
  store.list.forEach(item => {
    ;(item as any)._selected = selectedIds.value.includes(item.checksum)
  })
}

function truncateSql(sql: string) {
  return sql.length > 60 ? sql.slice(0, 60) + '...' : sql
}

function formatDate(date: string | Date) {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleString('zh-CN')
}

function goToDetail(checksum: string) {
  router.push(`/slow-sql/${checksum}`)
}

async function handleOptimize(row: SlowSQL) {
  if (optimizingIds.value.includes(row.checksum)) return
  try {
    optimizingIds.value.push(row.checksum)
    await store.optimize(row.checksum)
    ElMessage.success('优化成功')
  } catch {
    // Error already handled by interceptor
  } finally {
    optimizingIds.value = optimizingIds.value.filter(id => id !== row.checksum)
  }
}

function handleDownload(checksum: string) {
  downloadSlowSQL(checksum)
}

async function handleBatchOptimize() {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先选择要优化的SQL')
    return
  }

  try {
    await ElMessageBox.confirm(`确定要优化选中的 ${selectedIds.value.length} 条SQL吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    await store.batchOptimize(selectedIds.value)
    ElMessage.success('批量优化完成')
  } catch {
    // User cancelled
  }
}

function handleBatchDownload() {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先选择要下载的SQL')
    return
  }
  batchDownloadSlowSQLs(selectedIds.value)
}

function handleSearch() {
  store.setFilters(localFilters.value)
  store.fetchList()
}

function handleReset() {
  localFilters.value = {
    host: '',
    database_name: '',
    time_range: '',
    is_optimized: '',
    ts_min: '',
    ts_max: '',
  }
  store.resetFilters()
  store.fetchList()
}

function handleRefresh() {
  store.fetchList()
}

function handleTimeRangeChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (value !== 'custom') {
    localFilters.value.ts_min = ''
    localFilters.value.ts_max = ''
  }
}

function handlePageChange(page: number, perPage: number) {
  if (page < 1 || page > totalPages.value) return
  store.setFilters({ page, per_page: perPage })
  store.fetchList()
}

// Sync local filters with store
watch(() => store.filters, (newFilters) => {
  localFilters.value = { ...newFilters }
}, { deep: true })

onMounted(() => {
  store.fetchList()
})
</script>

<style scoped>
.page-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 高级筛选 */
.advanced-filter {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 14px 16px;
  border-radius: 8px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-item label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  white-space: nowrap;
}

.filter-item input,
.filter-item select {
  padding: 7px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  color: #1e293b;
  background: #f8fafc;
  transition: all 0.15s ease;
  min-width: 140px;
}

.filter-item input:focus,
.filter-item select:focus {
  outline: none;
  border-color: #3b82f6;
  background: #ffffff;
}

.filter-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.btn-filter {
  padding: 7px 14px;
  background: #3b82f6;
  border: 1px solid #3b82f6;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.btn-filter:hover {
  background: #2563eb;
  border-color: #2563eb;
}

.btn-reset {
  padding: 7px 14px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.btn-reset:hover {
  border-color: #cbd5e1;
  background: #f8fafc;
}

/* 表格容器 */
.table-container {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.table-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.table-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.btn-action:hover:not(:disabled) {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.btn-action:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-action svg {
  width: 14px;
  height: 14px;
}

.btn-action--warning {
  color: #92400e;
  border-color: #fed7aa;
  background: #fff7ed;
}

.btn-action--warning:hover:not(:disabled) {
  color: #78350f;
  border-color: #fdba74;
  background: #ffedd5;
}

.btn-action--success {
  color: #15803d;
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.btn-action--success:hover:not(:disabled) {
  color: #166534;
  border-color: #86efac;
  background: #dcfce7;
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead {
  background: #f8fafc;
}

.data-table th {
  padding: 10px 14px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

.data-table td {
  padding: 12px 14px;
  font-size: 13px;
  color: #1e293b;
  border-bottom: 1px solid #f1f5f9;
}

.data-table tbody tr:hover {
  background: #f8fafc;
}

.th-checkbox,
.td-checkbox {
  width: 40px;
}

.th-checkbox input,
.td-checkbox input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.host-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
}

.td-sql {
  max-width: 300px;
}

.sql-text {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #475569;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
}

.time-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
}

.td-time {
  color: #64748b;
  font-size: 12px;
}

.td-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-link {
  padding: 0;
  background: transparent;
  border: none;
  color: #3b82f6;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s ease;
}

.btn-link:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-link:hover {
  color: #2563eb;
}

.btn-link--warning {
  color: #d97706;
}

.btn-link--warning:hover {
  color: #b45309;
}

.btn-link--success {
  color: #16a34a;
}

.btn-link--success:hover {
  color: #15803d;
}

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 4px;
}

.status-badge--pending {
  background: #fef3c7;
  color: #92400e;
}

.status-badge--optimized {
  background: #dcfce7;
  color: #15803d;
}

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-top: 1px solid #e2e8f0;
}

.pagination-info {
  font-size: 12px;
  color: #64748b;
}

.pagination-buttons {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  padding: 0 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.page-btn:hover:not(:disabled) {
  border-color: #cbd5e1;
  background: #f8fafc;
}

.page-btn.active {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #ffffff;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-btn svg {
  width: 16px;
  height: 16px;
}

/* 响应式 */
@media (max-width: 960px) {
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-item {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-buttons {
    margin-left: 0;
    width: 100%;
  }

  .filter-buttons button {
    flex: 1;
  }
}
</style>
