<template>
  <AppLayout>
    <section class="entry-grid" aria-label="创建优化任务">
      <button type="button" class="entry-card entry-card--sql" @click="goToCreateSql">
        <span class="entry-card__eyebrow">SQL 工作台</span>
        <strong class="entry-card__title">优化单个 SQL 查询</strong>
      </button>

      <button type="button" class="entry-card entry-card--mybatis" @click="goToCreateMyBatis">
        <span class="entry-card__eyebrow">XML 工作台</span>
        <strong class="entry-card__title">优化 MyBatis XML 文件</strong>
      </button>
    </section>

    <el-card shadow="never" class="table-card">
      <div class="table-shell">
        <div class="table-head">
          <div>
            <h3>历史任务</h3>
          </div>

          <div class="table-actions">
            <div class="filter-group" role="tablist" aria-label="任务类型筛选">
              <button
                v-for="option in filterOptions"
                :key="option.value || 'all'"
                type="button"
                class="filter-chip"
                :class="{ 'is-active': store.taskType === option.value }"
                @click="handleTypeChange(option.value)"
              >
                {{ option.label }}
              </button>
            </div>

            <el-button class="refresh-button" @click="store.fetchList">刷新</el-button>
          </div>
        </div>

        <div v-if="!store.loading && store.list.length === 0" class="table-empty">
          <strong>还没有优化任务，先从上方创建一个新任务</strong>
        </div>

        <template v-else>
          <el-table :data="store.list" v-loading="store.loading" class="task-table">
            <el-table-column label="类型" width="110">
              <template #default="{ row }">
                <span class="type-pill" :class="`type-pill--${row.task_type}`">
                  {{ row.task_type === 'sql' ? 'SQL' : 'MyBatis' }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="对象" min-width="280" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="task-object">
                  <el-button link type="primary" class="task-link" @click="goToDetail(row.id)">
                    {{ row.object_preview }}
                  </el-button>
                  <span class="task-subline">{{ row.database_name }} · {{ row.database_host }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <span class="status-pill" :class="`status-pill--${row.status}`">
                  {{ statusText(row.status) }}
                </span>
              </template>
            </el-table-column>

            <el-table-column prop="database_name" label="库名" width="120" />
            <el-table-column prop="database_host" label="数据库IP" width="140" />
            <el-table-column prop="created_at" label="创建时间" width="170" />

            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="goToDetail(row.id)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            class="task-pagination"
            v-model:current-page="store.page"
            v-model:page-size="store.perPage"
            :total="store.total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="handlePageChange"
            @size-change="handleSizeChange"
          />
        </template>
      </div>
    </el-card>
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
  if (status === 'queued') return '优化中'
  if (status === 'running') return '优化中'
  if (status === 'completed') return '完成'
  return '失败'
}
</script>

<style scoped>
.entry-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.entry-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  width: 100%;
  padding: 22px;
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 42, 61, 0.06);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease;
}

.entry-card:hover {
  border-color: #7dd3fc;
  box-shadow: 0 18px 36px rgba(3, 105, 161, 0.1);
  transform: translateY(-1px);
}

.entry-card:focus-visible {
  outline: none;
  border-color: #0369a1;
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.16);
}

.entry-card--sql {
  background: #ffffff;
}

.entry-card__eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 10px;
  border-radius: 4px;
  background: #e8f3fb;
  color: #075985;
  font-size: 12px;
  font-weight: 700;
}

.entry-card__title {
  color: #0f2a3d;
  font-size: 20px;
  font-weight: 700;
  line-height: 1.3;
}

.table-card {
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 42, 61, 0.06);
}

.table-shell {
  padding: 22px;
}

.table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.table-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f2a3d;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: 6px;
  background: #f3f7fb;
}

.filter-chip {
  border: none;
  border-radius: 6px;
  padding: 8px 14px;
  background: transparent;
  color: #536779;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.filter-chip:hover {
  color: #0f2a3d;
}

.filter-chip.is-active {
  background: #ffffff;
  color: #0369a1;
  box-shadow: 0 6px 18px rgba(15, 42, 61, 0.08);
}

.filter-chip:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.16);
}

.refresh-button.el-button {
  border-color: #d7e3ef;
  color: #33546b;
}

.table-empty {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 32px;
  border: 1px dashed #d9e6f2;
  border-radius: 18px;
  background: #f8fbfd;
}

.table-empty strong {
  color: #0f2a3d;
  font-size: 16px;
}

.task-object {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-link.el-button {
  justify-content: flex-start;
  margin: 0;
  padding: 0;
  font-weight: 700;
}

.task-subline {
  color: #64748b;
  font-size: 12px;
}

.type-pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 76px;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
}

.type-pill--sql {
  background: #e0f2fe;
  color: #075985;
}

.type-pill--mybatis {
  background: #e9fdf3;
  color: #047857;
}

.status-pill--queued,
.status-pill--running {
  background: #fff7dd;
  color: #9a6700;
}

.status-pill--completed {
  background: #eafaf2;
  color: #047857;
}

.status-pill--failed {
  background: #feecec;
  color: #b42318;
}

.task-pagination {
  margin-top: 18px;
  justify-content: flex-end;
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: #f8fbfd;
  color: #0f2a3d;
}

:deep(.el-table .cell) {
  padding-left: 10px;
  padding-right: 10px;
}

@media (max-width: 960px) {
  .entry-grid {
    grid-template-columns: 1fr 1fr;
  }

  .table-head,
  .table-actions {
    align-items: stretch;
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .entry-grid {
    grid-template-columns: 1fr;
  }

  .table-shell {
    padding: 18px;
  }

  .filter-group {
    width: 100%;
    justify-content: space-between;
  }

  .filter-chip {
    flex: 1;
  }

  .task-pagination {
    overflow-x: auto;
  }
}
</style>
