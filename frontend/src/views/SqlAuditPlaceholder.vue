<template>
  <AppLayout>
    <div class="page-container">
      <!-- 快捷操作 -->
      <div class="quick-actions">
        <div class="action-card" @click="showCreateDialog = true">
          <div class="action-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5v14M5 12h14"/>
            </svg>
          </div>
          <div class="action-content">
            <div class="action-title">新建巡检任务</div>
            <div class="action-desc">创建新的SQL审核任务</div>
          </div>
        </div>
        <div class="action-card">
          <div class="action-icon action-icon--secondary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
          </div>
          <div class="action-content">
            <div class="action-title">审核规则</div>
            <div class="action-desc">配置SQL审核规则</div>
          </div>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <div class="filter-tabs">
          <button
            v-for="tab in filterTabs"
            :key="tab.value"
            :class="['filter-tab', { active: currentFilter === tab.value }]"
            @click="currentFilter = tab.value"
          >
            {{ tab.label }}
            <span v-if="tab.count" class="tab-count">{{ tab.count }}</span>
          </button>
        </div>
        <div class="filter-actions">
          <div class="search-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="M21 21l-4.35-4.35"/>
            </svg>
            <input type="text" placeholder="搜索任务名称或ID" v-model="searchQuery" />
          </div>
          <button class="btn-refresh">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6"/>
              <path d="M1 20v-6h6"/>
              <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- 任务列表 -->
      <div class="table-container">
        <div class="table-header">
          <span class="table-title">巡检任务列表</span>
        </div>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>任务ID</th>
                <th>任务名称</th>
                <th>数据库</th>
                <th>审核规则</th>
                <th>状态</th>
                <th>问题数</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in auditTasks" :key="task.id">
                <td class="cell-id">#{{ task.id }}</td>
                <td class="cell-name">
                  <div class="name-text">{{ task.name }}</div>
                </td>
                <td>{{ task.database }}</td>
                <td>{{ task.ruleSet }}</td>
                <td>
                  <span :class="['status-badge', `status-badge--${task.status}`]">
                    {{ statusText(task.status) }}
                  </span>
                </td>
                <td>
                  <span :class="['issue-count', task.issueCount > 0 ? 'has-issues' : '']">
                    {{ task.issueCount > 0 ? task.issueCount : '-' }}
                  </span>
                </td>
                <td class="cell-time">{{ task.createdAt }}</td>
                <td class="cell-actions">
                  <button class="btn-action">查看</button>
                  <button class="btn-action">报告</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div class="pagination">
          <span class="pagination-info">共 {{ total }} 条</span>
          <div class="pagination-buttons">
            <button class="page-btn" :disabled="page <= 1">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M15 18l-6-6 6-6"/>
              </svg>
            </button>
            <button v-for="p in visiblePages" :key="p" :class="['page-btn', { active: p === page }]" @click="page = p">
              {{ p }}
            </button>
            <button class="page-btn" :disabled="page >= totalPages">
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
import { ref, computed } from 'vue'
import AppLayout from '@/components/Layout/AppLayout.vue'

const showCreateDialog = ref(false)
const currentFilter = ref('all')
const searchQuery = ref('')
const page = ref(1)
const pageSize = ref(10)

const filterTabs = [
  { value: 'all', label: '全部', count: 128 },
  { value: 'pending', label: '待审核', count: 12 },
  { value: 'running', label: '审核中', count: 3 },
  { value: 'completed', label: '已完成', count: 98 },
  { value: 'failed', label: '失败', count: 15 },
]

const auditTasks = ref([
  { id: 1024, name: '生产库日常巡检', database: 'prod-mysql-01', ruleSet: '企业标准规则', status: 'completed', issueCount: 5, createdAt: '2026-04-10 09:30:00' },
  { id: 1023, name: '订单库性能审核', database: 'prod-order-db', ruleSet: '性能优化规则', status: 'completed', issueCount: 2, createdAt: '2026-04-10 08:15:00' },
  { id: 1022, name: '用户库安全巡检', database: 'prod-user-db', ruleSet: '安全审计规则', status: 'running', issueCount: 0, createdAt: '2026-04-10 07:00:00' },
  { id: 1021, name: '报表库周检', database: 'prod-report-db', ruleSet: '企业标准规则', status: 'completed', issueCount: 0, createdAt: '2026-04-09 18:30:00' },
  { id: 1020, name: '日志库审核', database: 'prod-log-db', ruleSet: '企业标准规则', status: 'pending', issueCount: 0, createdAt: '2026-04-09 16:00:00' },
  { id: 1019, name: '支付库安全检查', database: 'prod-payment-db', ruleSet: '安全审计规则', status: 'failed', issueCount: 0, createdAt: '2026-04-09 14:20:00' },
  { id: 1018, name: '库存库巡检', database: 'prod-inventory-db', ruleSet: '企业标准规则', status: 'completed', issueCount: 3, createdAt: '2026-04-09 12:00:00' },
  { id: 1017, name: '消息队列库审核', database: 'prod-mq-db', ruleSet: '性能优化规则', status: 'completed', issueCount: 1, createdAt: '2026-04-09 10:30:00' },
])

const total = ref(128)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
const visiblePages = computed(() => {
  const pages = []
  const start = Math.max(1, page.value - 2)
  const end = Math.min(totalPages.value, start + 4)
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

function statusText(status: string) {
  const map: Record<string, string> = {
    pending: '待审核',
    running: '审核中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}
</script>

<style scoped>
.page-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 快捷操作 */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.action-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
}

.action-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #eff6ff;
  border-radius: 8px;
  color: #3b82f6;
  flex-shrink: 0;
}

.action-icon--secondary {
  background: #f0fdf4;
  color: #16a34a;
}

.action-icon svg {
  width: 22px;
  height: 22px;
}

.action-content {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.action-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.action-desc {
  font-size: 12px;
  color: #64748b;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 12px 16px;
  border-radius: 8px;
}

.filter-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
}

.filter-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  background: transparent;
  border: none;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.filter-tab:hover {
  color: #1e293b;
  background: #f1f5f9;
}

.filter-tab.active {
  color: #3b82f6;
  background: #eff6ff;
}

.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
  font-weight: 600;
  border-radius: 9px;
}

.filter-tab.active .tab-count {
  background: #3b82f6;
  color: #ffffff;
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  width: 240px;
  transition: all 0.15s ease;
}

.search-box:focus-within {
  border-color: #3b82f6;
  background: #ffffff;
}

.search-box svg {
  width: 16px;
  height: 16px;
  color: #94a3b8;
  flex-shrink: 0;
}

.search-box input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 13px;
  color: #1e293b;
  outline: none;
}

.search-box input::placeholder {
  color: #94a3b8;
}

.btn-refresh {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-refresh:hover {
  border-color: #cbd5e1;
  background: #f1f5f9;
}

.btn-refresh svg {
  width: 16px;
  height: 16px;
  color: #64748b;
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

.cell-id {
  color: #64748b;
  font-family: 'SF Mono', 'Consolas', monospace;
  font-size: 12px;
}

.name-text {
  font-weight: 500;
  color: #1e293b;
}

.cell-time {
  color: #64748b;
  font-size: 12px;
}

.cell-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-action {
  padding: 4px 10px;
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #475569;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.btn-action:hover {
  border-color: #3b82f6;
  color: #3b82f6;
  background: #eff6ff;
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

.status-badge--running {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-badge--completed {
  background: #dcfce7;
  color: #15803d;
}

.status-badge--failed {
  background: #fee2e2;
  color: #dc2626;
}

/* 问题数 */
.issue-count {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
}

.issue-count.has-issues {
  color: #dc2626;
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
  .quick-actions {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .search-box {
    width: 100%;
  }
}
</style>
