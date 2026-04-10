<template>
  <el-card shadow="never" class="table-card">
    <div class="table-shell">
      <div class="table-head">
        <h3>慢SQL记录</h3>
        <div class="table-actions">
          <el-button
            type="warning"
            class="batch-optimize"
            :disabled="!hasSelected"
            :loading="optimizeLoading"
            @click="handleBatchOptimize"
          >
            <el-icon><Lightning /></el-icon>
            批量获取优化建议
          </el-button>
          <el-button
            type="success"
            class="batch-download"
            :disabled="!hasSelected"
            @click="handleBatchDownload"
          >
            <el-icon><Download /></el-icon>
            批量下载
          </el-button>
        </div>
      </div>

      <el-table
        :data="list"
        v-loading="loading"
        class="slow-table"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="host" label="主机" width="130">
          <template #default="{ row }">
            <span class="host-pill">{{ row.host }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="database_name" label="数据库" width="150" />
        <el-table-column prop="sample" label="SQL语句" min-width="290" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="sql-preview">
              {{ row.sample.length > 60 ? row.sample.slice(0, 60) + '...' : row.sample }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="execution_count" label="次数" width="80" />
        <el-table-column prop="avg_time" label="平均时间" width="110">
          <template #default="{ row }">
            <span class="time-pill">{{ row.avg_time.toFixed(2) }}s</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_seen" label="最近出现" width="170">
          <template #default="{ row }">
            {{ formatDate(row.last_seen) }}
          </template>
        </el-table-column>
        <el-table-column prop="is_optimized" label="状态" width="100">
          <template #default="{ row }">
            <span class="status-pill" :class="{ 'is-optimized': row.is_optimized }">
              {{ row.is_optimized ? '已优化' : '待优化' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center" class-name="op-col" label-class-name="op-col-head">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" size="small" @click="goToDetail(row.checksum)">
                详情
              </el-button>
              <el-button
                v-if="!row.is_optimized"
                link
                type="warning"
                size="small"
                :loading="optimizingIds.includes(row.checksum)"
                @click="handleOptimize(row)"
              >
                优化
              </el-button>
              <el-button link type="success" size="small" @click="handleDownload(row.checksum)">
                下载
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="table-pagination"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Lightning, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSlowSqlStore } from '@/stores/slowSql'
import { downloadSlowSQL, batchDownloadSlowSQLs } from '@/api/slowSql'
import type { SlowSQL } from '@/types'

interface Props {
  list: SlowSQL[]
  loading?: boolean
  pagination?: {
    page: number
    per_page: number
    total: number
  }
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  (e: 'page-change', page: number, perPage: number): void
}>()

const router = useRouter()
const store = useSlowSqlStore()

const currentPage = computed(() => props.pagination?.page || 1)
const pageSize = computed(() => props.pagination?.per_page || 10)
const total = computed(() => props.pagination?.total || 0)
const hasSelected = computed(() => store.hasSelected)
const optimizeLoading = computed(() => store.optimizeLoading)

const selectedRows = ref<SlowSQL[]>([])
const optimizingIds = ref<string[]>([])

function formatDate(date: string | Date) {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleString('zh-CN')
}

function handleSelectionChange(selection: SlowSQL[]) {
  selectedRows.value = selection
  // Update store selection state
  props.list.forEach(item => {
    const isSelected = selection.some(s => s.checksum === item.checksum)
    ;(item as any)._selected = isSelected
  })
}

function goToDetail(checksum: string) {
  router.push(`/slow-sql/${checksum}`)
}

async function handleOptimize(row: SlowSQL) {
  try {
    optimizingIds.value.push(row.checksum)
    await store.optimize(row.checksum)
    ElMessage.success('优化成功')
  } finally {
    optimizingIds.value = optimizingIds.value.filter(id => id !== row.checksum)
  }
}

function handleDownload(checksum: string) {
  downloadSlowSQL(checksum)
}

async function handleBatchOptimize() {
  const ids = store.selectedIds
  if (!ids.length) {
    ElMessage.warning('请先选择要优化的SQL')
    return
  }

  try {
    await ElMessageBox.confirm(`确定要优化选中的 ${ids.length} 条SQL吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await store.batchOptimize(ids)
    ElMessage.success('批量优化完成')
  } catch {
    // User cancelled
  }
}

function handleBatchDownload() {
  const ids = store.selectedIds
  if (!ids.length) {
    ElMessage.warning('请先选择要下载的SQL')
    return
  }
  batchDownloadSlowSQLs(ids)
}

function handlePageChange(page: number) {
  emit('page-change', page, pageSize.value)
}

function handleSizeChange(size: number) {
  emit('page-change', 1, size)
}
</script>

<style scoped>
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
  gap: 12px;
  margin-bottom: 16px;
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
  gap: 4px;
  padding-left: 8px;
  border-left: 1px solid #d9e6f2;
}

.table-actions :deep(.el-button + .el-button) {
  margin-left: 0 !important;
}

.batch-optimize.el-button,
.batch-download.el-button {
  border-radius: 6px;
}

.row-actions {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  gap: 0;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.row-actions :deep(.el-button.is-link) {
  padding: 0 2px !important;
  min-width: auto !important;
  font-size: 12px;
}

.row-actions :deep(.el-button + .el-button) {
  margin-left: 0 !important;
}

.slow-table :deep(.el-table__header th) {
  color: #324e68;
}

.slow-table :deep(.el-table__header-wrapper th.op-col-head),
.slow-table :deep(.el-table__body-wrapper td.op-col),
.slow-table :deep(.el-table__fixed-right th.op-col-head),
.slow-table :deep(.el-table__fixed-right td.op-col) {
  border-left: 1px solid #d9e6f2 !important;
  background: #f8fbff;
}

.host-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 6px;
  background: #e8f3fb;
  color: #075985;
  font-size: 12px;
  font-weight: 700;
}

.time-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 6px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 700;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  border-radius: 6px;
  background: #eef2f7;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.status-pill.is-optimized {
  background: #ecfdf3;
  color: #166534;
}

.sql-preview {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #334155;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 12px;
}

.table-pagination {
  margin-top: 18px;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .table-head {
    align-items: stretch;
    flex-direction: column;
  }

  .table-actions {
    flex-wrap: wrap;
  }
}
</style>
