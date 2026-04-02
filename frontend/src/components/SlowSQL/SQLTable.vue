<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <el-button
          type="warning"
          :disabled="!hasSelected"
          :loading="optimizeLoading"
          @click="handleBatchOptimize"
        >
          <el-icon><Lightning /></el-icon>
          批量获取优化建议
        </el-button>
        <el-button
          type="success"
          :disabled="!hasSelected"
          @click="handleBatchDownload"
        >
          <el-icon><Download /></el-icon>
          批量下载
        </el-button>
      </div>
    </template>

    <el-table
      :data="list"
      v-loading="loading"
      stripe
      style="width: 100%"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="55" />
      <el-table-column prop="host" label="主机" width="120">
        <template #default="{ row }">
          <el-tag>{{ row.host }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="database_name" label="数据库" width="150" />
      <el-table-column prop="sample" label="SQL语句" min-width="250" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="sql-preview">
            {{ row.sample.length > 60 ? row.sample.slice(0, 60) + '...' : row.sample }}
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="execution_count" label="次数" width="80" />
      <el-table-column prop="avg_time" label="平均时间" width="100">
        <template #default="{ row }">
          <el-tag type="danger">{{ row.avg_time.toFixed(2) }}s</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_seen" label="最近出现" width="160">
        <template #default="{ row }">
          {{ formatDate(row.last_seen) }}
        </template>
      </el-table-column>
      <el-table-column prop="is_optimized" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_optimized ? 'success' : 'info'">
            {{ row.is_optimized ? '已优化' : '待优化' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
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
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50, 100]"
      :total="total"
      layout="total, sizes, prev, pager, next, jumper"
      style="margin-top: 20px; justify-content: flex-end"
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Lightning, Download } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSlowSqlStore } from '@/stores/slowSql'
import { optimizeSlowSQL, downloadSlowSQL, batchOptimizeSlowSQLs, batchDownloadSlowSQLs } from '@/api/slowSql'
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
.card-header {
  display: flex;
  gap: 12px;
}

.sql-preview {
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: monospace;
  font-size: 12px;
}
</style>
