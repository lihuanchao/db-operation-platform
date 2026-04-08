<template>
  <AppLayout>
    <div class="page-shell">
      <div class="page-header">
        <div>
          <h2>数据闪回任务</h2>
          <p>按数据库、表和状态快速筛选任务记录。</p>
        </div>

        <el-button type="primary" class="create-task-btn" @click="goToCreate">
          新建任务
        </el-button>
      </div>

      <el-card shadow="never" class="filter-card">
        <el-form :model="form" inline class="filter-form">
          <el-form-item label="数据库名">
            <el-input
              v-model="form.database_name"
              class="filter-control"
              placeholder="数据库名"
              clearable
            />
          </el-form-item>
          <el-form-item label="表名">
            <el-input
              v-model="form.table_name"
              class="filter-control"
              placeholder="表名"
              clearable
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status" class="filter-control" placeholder="全部" clearable>
              <el-option label="全部" value="" />
              <el-option label="排队中" value="queued" />
              <el-option label="执行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
            </el-select>
          </el-form-item>
          <el-form-item label="SQL 类型">
            <el-select v-model="form.sql_type" class="filter-control" placeholder="全部" clearable>
              <el-option label="全部" value="" />
              <el-option label="delete" value="delete" />
              <el-option label="insert" value="insert" />
              <el-option label="update" value="update" />
            </el-select>
          </el-form-item>
          <el-form-item label="输出类型">
            <el-select v-model="form.work_type" class="filter-control" placeholder="全部" clearable>
              <el-option label="全部" value="" />
              <el-option label="2sql" value="2sql" />
              <el-option label="rollback" value="rollback" />
              <el-option label="stats" value="stats" />
            </el-select>
          </el-form-item>
          <el-form-item class="filter-actions">
            <el-button type="primary" class="search-btn" @click="handleSearch">查询</el-button>
            <el-button class="reset-btn" @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="table-card">
        <el-table :data="store.list" v-loading="store.loading" stripe class="task-table">
          <el-table-column label="连接名称" width="160">
            <template #default="{ row }">
              {{ row.connection_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="对象" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              <button type="button" class="task-link" :data-task-id="row.id" @click="goToDetail(row.id)">
                {{ row.database_name }}.{{ row.table_name }}
              </button>
            </template>
          </el-table-column>
          <el-table-column prop="sql_type" label="SQL 类型" width="120" />
          <el-table-column prop="work_type" label="输出类型" width="120" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <span class="status-pill" :class="`status-pill--${row.status}`">
                {{ statusText(row.status) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ row.created_at || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="goToDetail(row.id)">
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="store.page"
          v-model:page-size="store.perPage"
          :total="store.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          class="table-pagination"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useFlashbackTaskStore } from '@/stores/flashbackTask'
import type { FlashbackSqlType, FlashbackTaskStatus, FlashbackWorkType } from '@/types'

const router = useRouter()
const store = useFlashbackTaskStore()

const form = reactive({
  database_name: '',
  table_name: '',
  status: '' as FlashbackTaskStatus | '',
  sql_type: '' as FlashbackSqlType | '',
  work_type: '' as FlashbackWorkType | ''
})

onMounted(() => {
  store.fetchList()
})

function goToCreate() {
  router.push('/flashback-tasks/create')
}

function goToDetail(id: number) {
  router.push(`/flashback-tasks/${id}`)
}

function handleSearch() {
  store.setFilters({
    database_name: form.database_name.trim(),
    table_name: form.table_name.trim(),
    status: form.status,
    sql_type: form.sql_type,
    work_type: form.work_type
  })
  store.fetchList()
}

function handleReset() {
  form.database_name = ''
  form.table_name = ''
  form.status = ''
  form.sql_type = ''
  form.work_type = ''
  store.resetFilters()
  store.fetchList()
}

function handlePageChange(page: number) {
  store.goToPage(page)
}

function handleSizeChange(size: number) {
  store.setPageSize(size)
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
</script>

<style scoped>
.page-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.filter-card,
.table-card {
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  box-shadow: 0 10px 26px rgba(15, 42, 61, 0.05);
}

.filter-card :deep(.el-card__body),
.table-card :deep(.el-card__body) {
  padding: 16px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.filter-control {
  width: 170px;
}

.filter-actions {
  margin-left: auto;
}

.task-table {
  width: 100%;
}

.task-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: #0b63ce;
  cursor: pointer;
  font: inherit;
}

.task-link:hover {
  text-decoration: underline;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: #eef5ff;
  color: #1f5ca8;
  font-size: 12px;
  font-weight: 600;
}

.status-pill--running {
  background: #fff7e8;
  color: #9a5b00;
}

.status-pill--completed {
  background: #eaf8ef;
  color: #1f7a3e;
}

.status-pill--failed {
  background: #feefef;
  color: #c13232;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
