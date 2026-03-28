<template>
  <AppLayout>
    <div class="page-header">
      <h2>数据库连接管理</h2>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新增连接
      </el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="连接名称">
          <el-input v-model="filters.connection_name" placeholder="请输入连接名称" clearable />
        </el-form-item>
        <el-form-item label="主机地址">
          <el-input v-model="filters.host" placeholder="请输入主机地址" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table :data="store.list" v-loading="store.loading" stripe style="width: 100%">
        <el-table-column prop="connection_name" label="连接名称" width="180" />
        <el-table-column prop="host" label="主机地址" width="150">
          <template #default="{ row }">
            <el-tag size="small">{{ row.host }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="manage_host" label="管理IP" width="150">
          <template #default="{ row }">
            {{ row.manage_host || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="port" label="端口" width="100" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleTest(row)">
              <el-icon><Connection /></el-icon>
              测试连接
            </el-button>
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="store.page"
        v-model:page-size="store.perPage"
        :total="store.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </el-card>

    <el-dialog
      v-model="formDialogVisible"
      :title="editingConnection ? '编辑连接' : '新增连接'"
      width="600px"
      destroy-on-close
    >
      <ConnectionForm
        ref="formRef"
        :connection="editingConnection"
        @saved="handleFormSaved"
        @cancel="formDialogVisible = false"
      />
    </el-dialog>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Edit, Delete, Connection } from '@element-plus/icons-vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import ConnectionForm from '@/components/Connection/ConnectionForm.vue'
import { useDbConnectionStore } from '@/stores/dbConnection'
import type { DbConnection } from '@/types'

const store = useDbConnectionStore()
const router = useRouter()

const formDialogVisible = ref(false)
const editingConnection = ref<DbConnection | null>(null)
const formRef = ref()

const filters = ref({
  connection_name: '',
  host: ''
})

onMounted(() => {
  store.fetchList()
})

function handleSearch() {
  store.setFilters(filters.value)
  store.fetchList()
}

function handleReset() {
  filters.value = {
    connection_name: '',
    host: ''
  }
  store.resetFilters()
  store.fetchList()
}

function handleAdd() {
  editingConnection.value = null
  formDialogVisible.value = true
}

function handleEdit(row: DbConnection) {
  editingConnection.value = { ...row }
  formDialogVisible.value = true
}

async function handleTest(row: DbConnection) {
  if (!row.id) return
  await store.testConnectionAction(row.id)
}

async function handleDelete(row: DbConnection) {
  try {
    await ElMessageBox.confirm(
      `确定要删除连接「${row.connection_name}」吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    if (row.id) {
      await store.removeConnection(row.id)
    }
  } catch {
    // User cancelled
  }
}

function handleFormSaved() {
  formDialogVisible.value = false
}

function handlePageChange(page: number) {
  store.goToPage(page)
}

function handleSizeChange(size: number) {
  store.setPageSize(size)
}
</script>

<style scoped>
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

.filter-card {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}
</style>
