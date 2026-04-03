<template>
  <AppLayout>
    <div class="page-header">
      <h2>权限管理</h2>
      <p>为普通用户分配可访问的数据库连接</p>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>用户列表</span>
              <el-input v-model="userKeyword" placeholder="搜索姓名/工号" clearable class="search-input" />
            </div>
          </template>
          <el-table
            :data="filteredUsers"
            v-loading="userStore.loading"
            highlight-current-row
            row-key="id"
            @row-click="handleSelectUser"
          >
            <el-table-column prop="real_name" label="姓名" width="130" />
            <el-table-column prop="employee_no" label="工号" width="130" />
            <el-table-column label="角色">
              <template #default="{ row }">
                {{ row.role_code === 'admin' ? '管理员' : '普通用户' }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="14">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>连接授权</span>
              <el-input v-model="connectionKeyword" placeholder="搜索连接名/IP" clearable class="search-input" />
            </div>
          </template>
          <div v-if="!currentUserId" class="placeholder">请选择左侧普通用户进行授权</div>
          <template v-else>
            <div class="selected-user">
              当前用户：<strong>{{ currentUserName }}</strong>
            </div>
            <el-checkbox-group v-model="permissionStore.selectedConnectionIds" class="permission-list">
              <el-checkbox
                v-for="connection in filteredConnections"
                :key="connection.id"
                :value="connection.id"
                class="permission-item"
              >
                {{ connection.connection_name }}（{{ connection.manage_host || connection.host }}）
              </el-checkbox>
            </el-checkbox-group>
            <div class="save-row">
              <el-button type="primary" :loading="saveLoading" @click="save">保存授权</el-button>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { usePermissionAdminStore } from '@/stores/permissionAdmin'
import { useUserAdminStore } from '@/stores/userAdmin'
import type { SysUser } from '@/types'

const permissionStore = usePermissionAdminStore()
const userStore = useUserAdminStore()
const currentUserId = ref<number | null>(null)
const currentUserName = ref('')
const saveLoading = ref(false)
const userKeyword = ref('')
const connectionKeyword = ref('')

const filteredUsers = computed(() => {
  const text = userKeyword.value.trim().toLowerCase()
  if (!text) return userStore.list
  return userStore.list.filter((item) =>
    `${item.real_name} ${item.employee_no}`.toLowerCase().includes(text)
  )
})

const filteredConnections = computed(() => {
  const text = connectionKeyword.value.trim().toLowerCase()
  if (!text) return permissionStore.connections
  return permissionStore.connections.filter((item) =>
    `${item.connection_name} ${item.manage_host || item.host || ''}`.toLowerCase().includes(text)
  )
})

onMounted(async () => {
  await userStore.fetchList()
  await permissionStore.fetchConnections()
})

async function handleSelectUser(row: SysUser) {
  if (row.role_code === 'admin') {
    currentUserId.value = null
    currentUserName.value = ''
    permissionStore.selectedConnectionIds = []
    ElMessage.info('管理员默认拥有全部权限，无需单独授权')
    return
  }
  currentUserId.value = row.id
  currentUserName.value = `${row.real_name}（${row.employee_no}）`
  await permissionStore.loadUserPermissions(row.id)
}

async function save() {
  if (!currentUserId.value) return
  saveLoading.value = true
  try {
    await permissionStore.saveUserPermissions(currentUserId.value)
    ElMessage.success('授权已保存')
  } finally {
    saveLoading.value = false
  }
}
</script>

<style scoped>
.page-header {
  margin-bottom: 14px;
}

.page-header h2 {
  margin: 0;
}

.page-header p {
  margin: 6px 0 0;
  color: #6c7a91;
  font-size: 13px;
}

.panel-card {
  border-radius: 12px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.search-input {
  width: 200px;
}

.placeholder {
  color: #8b95a7;
  padding: 8px 0;
}

.selected-user {
  margin-bottom: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f0f6ff;
  color: #2a466f;
  font-size: 13px;
}

.permission-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow: auto;
  padding-right: 4px;
}

.permission-item {
  margin-right: 0;
}

.save-row {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .search-input {
    width: 100%;
  }

  .card-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
