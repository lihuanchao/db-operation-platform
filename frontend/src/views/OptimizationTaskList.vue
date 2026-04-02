<template>
  <AppLayout>
    <div class="page-header">
      <h2>优化任务列表</h2>
    </div>

    <el-row :gutter="16" class="entry-row">
      <el-col :span="12">
        <el-button class="entry-btn primary" @click="goToCreateSql">
          优化单个SQL查询
        </el-button>
      </el-col>
      <el-col :span="12">
        <el-button class="entry-btn" @click="goToCreateMyBatis">
          优化MyBatis XML文件
        </el-button>
      </el-col>
    </el-row>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="table-toolbar">
          <el-select
            v-model="store.taskType"
            placeholder="类型筛选"
            clearable
            style="width: 180px"
            @change="handleTypeChange"
          >
            <el-option label="全部类型" value="" />
            <el-option label="SQL" value="sql" />
            <el-option label="MyBatis" value="mybatis" />
          </el-select>
          <el-button @click="store.fetchList">刷新</el-button>
        </div>
      </template>

      <el-table :data="store.list" v-loading="store.loading" stripe size="small">
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.task_type === 'sql' ? 'primary' : 'success'">
              {{ row.task_type === 'sql' ? 'SQL' : 'MyBatis' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="对象" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <el-button link type="primary" @click="goToDetail(row.id)">
              {{ row.object_preview }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="86">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">
              {{ statusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="database_host" label="数据库IP" width="130" />
        <el-table-column prop="database_name" label="库名" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goToDetail(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="store.page"
        v-model:page-size="store.perPage"
        :total="store.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 20px; justify-content: flex-end"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
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

function statusTagType(status: OptimizationTaskStatus) {
  if (status === 'queued') return 'info'
  if (status === 'running') return 'warning'
  if (status === 'completed') return 'success'
  return 'danger'
}
</script>

<style scoped>
.page-header h2 {
  margin: 0 0 20px;
  color: #1f2d3d;
}

.entry-row {
  margin-bottom: 20px;
}

.entry-btn {
  width: 100%;
  height: 52px;
  border-radius: 10px;
  font-size: 18px;
}

.entry-btn.primary {
  color: #fff;
  border-color: #6c5ce7;
  background: linear-gradient(90deg, #6c5ce7, #8c7cf0);
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

:deep(.el-table .cell) {
  padding-left: 6px;
  padding-right: 6px;
}
</style>
