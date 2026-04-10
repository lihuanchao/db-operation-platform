<template>
  <AppLayout>
    <div class="page-container">
      <!-- 快捷操作区域 -->
      <div class="quick-actions">
        <button type="button" class="action-card action-card--primary" @click="goToCreateSql">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 7h16M4 12h16M4 17h16"/>
            </svg>
          </div>
          <div class="action-content">
            <div class="action-title">SQL 优化</div>
            <div class="action-desc">优化单个 SQL 查询</div>
          </div>
        </button>

        <button type="button" class="action-card action-card--secondary" @click="goToCreateMyBatis">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <div class="action-content">
            <div class="action-title">MyBatis 优化</div>
            <div class="action-desc">优化 XML 映射文件</div>
          </div>
        </button>
      </div>

      <!-- 任务列表区域 -->
      <div class="table-section">
        <div class="section-header">
          <div class="header-left">
            <h3 class="section-title">优化任务</h3>
            <span class="section-count">{{ store.total }} 条记录</span>
          </div>
          <div class="header-right">
            <div class="filter-tabs">
              <button
                v-for="option in filterOptions"
                :key="option.value || 'all'"
                type="button"
                class="filter-tab"
                :class="{ 'is-active': store.taskType === option.value }"
                @click="handleTypeChange(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
            <el-button class="btn-refresh" @click="store.fetchList">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
              刷新
            </el-button>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="!store.loading && store.list.length === 0" class="empty-state">
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <div class="empty-text">暂无优化任务</div>
          <div class="empty-hint">点击上方卡片创建新的优化任务</div>
        </div>

        <!-- 数据表格 -->
        <template v-else>
          <div class="table-wrapper">
            <el-table
              :data="store.list"
              v-loading="store.loading"
              class="data-table"
              :header-cell-style="{ background: '#f8fafc', color: '#475569' }"
            >
              <el-table-column label="类型" width="90">
                <template #default="{ row }">
                  <span :class="['type-badge', `type-badge--${row.task_type}`]">
                    {{ row.task_type === 'sql' ? 'SQL' : 'MyBatis' }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column label="任务预览" min-width="280" show-overflow-tooltip>
                <template #default="{ row }">
                  <button class="task-link" @click="goToDetail(row.id)">
                    {{ row.object_preview }}
                  </button>
                </template>
              </el-table-column>

              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <span :class="['status-badge', `status-badge--${row.status}`]">
                    {{ statusText(row.status) }}
                  </span>
                </template>
              </el-table-column>

              <el-table-column prop="database_name" label="数据库" width="120" />
              <el-table-column prop="database_host" label="主机" width="140" />
              <el-table-column prop="created_at" label="创建时间" width="170" />

              <el-table-column label="操作" width="70" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="goToDetail(row.id)" size="small">
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="store.page"
              v-model:page-size="store.perPage"
              :total="store.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @current-change="handlePageChange"
              @size-change="handleSizeChange"
            />
          </div>
        </template>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useOptimizationTaskStore } from '@/stores/optimizationTask'
import type { OptimizationTaskStatus, OptimizationTaskType } from '@/types'

const router = useRouter()
const store = useOptimizationTaskStore()

const filterOptions: Array<{ label: string; value: OptimizationTaskType | '' }> = [
  { label: '全部', value: '' },
  { label: 'SQL', value: 'sql' },
  { label: 'MyBatis', value: 'mybatis' }
]

onMounted(() => {
  store.fetchList()
})

function goToCreateSql() {
  router.push('/optimization-tasks/create/sql')
}

function goToCreateMyBatis() {
  router.push('/optimization-tasks/create/mybatis')
}

function goToDetail(id: number) {
  router.push(`/optimization-tasks/${id}`)
}

function handleTypeChange(value: OptimizationTaskType | '') {
  if (store.taskType === value) return
  store.setTaskType(value || '')
  store.fetchList()
}

function handlePageChange(page: number) {
  store.setPage(page)
  store.fetchList()
}

function handleSizeChange(size: number) {
  store.setPerPage(size)
  store.fetchList()
}

function statusText(status: OptimizationTaskStatus) {
  if (status === 'queued') return '等待中'
  if (status === 'running') return '优化中'
  if (status === 'completed') return '已完成'
  return '失败'
}
</script>

<style scoped>
.page-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 快捷操作区域 */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.action-card:hover {
  border-color: #3b82f6;
  background: #f8fafc;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  transform: translateY(-1px);
}

.action-card:active {
  transform: translateY(0);
}

.action-card--primary .action-icon {
  color: #3b82f6;
  background: #eff6ff;
}

.action-card--secondary .action-icon {
  color: #059669;
  background: #ecfdf5;
}

.action-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  flex-shrink: 0;
}

.action-icon svg {
  width: 22px;
  height: 22px;
}

.action-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.action-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.action-desc {
  font-size: 12px;
  color: #64748b;
}

/* 表格区域 */
.table-section {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.section-count {
  font-size: 12px;
  color: #64748b;
  background: #e2e8f0;
  padding: 2px 8px;
  border-radius: 10px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px;
  background: #e2e8f0;
  border-radius: 6px;
}

.filter-tab {
  border: none;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  background: transparent;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.filter-tab:hover {
  color: #1e293b;
}

.filter-tab.is-active {
  background: #ffffff;
  color: #3b82f6;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.btn-refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  border-color: #cbd5e1;
  color: #475569;
  font-size: 12px;
  border-radius: 6px;
}

.btn-refresh svg {
  width: 14px;
  height: 14px;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: #cbd5e1;
}

.empty-text {
  font-size: 14px;
  font-weight: 500;
  color: #475569;
}

.empty-hint {
  font-size: 12px;
  color: #94a3b8;
}

/* 表格 */
.table-wrapper {
  padding: 0;
}

.data-table {
  border-radius: 0;
}

:deep(.data-table.el-table) {
  border: none;
}

:deep(.data-table .el-table__inner-wrapper::before) {
  display: none;
}

:deep(.data-table th.el-table__cell) {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 1px solid #e2e8f0;
}

:deep(.data-table td.el-table__cell) {
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
  font-size: 13px;
}

:deep(.data-table tr:hover > td) {
  background: #f8fafc;
}

:deep(.data-table .cell) {
  padding-left: 12px;
  padding-right: 12px;
}

/* 徽章 */
.type-badge,
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
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

.task-link {
  border: none;
  background: transparent;
  padding: 0;
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  color: #3b82f6;
  cursor: pointer;
  text-align: left;
}

.task-link:hover {
  color: #2563eb;
  text-decoration: underline;
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 14px 20px;
  border-top: 1px solid #e2e8f0;
}

:deep(.pagination-wrapper .el-pagination button) {
  border-radius: 4px;
  border-color: #e2e8f0;
}

:deep(.pagination-wrapper .el-pagination .el-pager li) {
  border-radius: 4px;
}

:deep(.pagination-wrapper .el-pagination .btn-prev),
:deep(.pagination-wrapper .el-pagination .btn-next) {
  min-width: 32px;
}

:deep(.pagination-wrapper .el-select .el-input__wrapper) {
  border-radius: 4px;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
}

/* 响应式 */
@media (max-width: 960px) {
  .quick-actions {
    grid-template-columns: 1fr 1fr;
  }

  .section-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .header-right {
    flex-direction: column;
    align-items: stretch;
  }
}

@media (max-width: 768px) {
  .quick-actions {
    grid-template-columns: 1fr;
  }

  .filter-tabs {
    width: 100%;
    justify-content: space-between;
  }

  .filter-tab {
    flex: 1;
    text-align: center;
  }
}
</style>
