<template>
  <AppLayout>
    <div class="page-header">
      <h2>权限管理</h2>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="panel-card">
          <template #header>用户列表</template>
          <el-table
            :data="userStore.list"
            v-loading="userStore.loading"
            highlight-current-row
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
          <template #header>连接授权</template>
          <div v-if="!currentUserId" class="placeholder">请选择左侧普通用户进行授权</div>
          <template v-else>
            <el-checkbox-group v-model="permissionStore.selectedConnectionIds" class="permission-list">
              <el-checkbox
                v-for="connection in permissionStore.connections"
                :key="connection.id"
                :value="connection.id"
                class="permission-item"
              >
                {{ connection.connection_name }}（{{ connection.manage_host || connection.host }}）
              </el-checkbox>
            </el-checkbox-group>
            <div class="save-row">
              <el-button type="primary" @click="save">保存授权</el-button>
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { usePermissionAdminStore } from '@/stores/permissionAdmin'
import { useUserAdminStore } from '@/stores/userAdmin'
import type { SysUser } from '@/types'

const permissionStore = usePermissionAdminStore()
const userStore = useUserAdminStore()
const currentUserId = ref<number | null>(null)

onMounted(async () => {
  await userStore.fetchList()
  await permissionStore.fetchConnections()
})

async function handleSelectUser(row: SysUser) {
  if (row.role_code === 'admin') {
    currentUserId.value = null
    permissionStore.selectedConnectionIds = []
    return
  }
  currentUserId.value = row.id
  await permissionStore.loadUserPermissions(row.id)
}

async function save() {
  if (!currentUserId.value) return
  await permissionStore.saveUserPermissions(currentUserId.value)
}
</script>

<style scoped>
.page-header {
  margin-bottom: 14px;
}

.page-header h2 {
  margin: 0;
}

.panel-card {
  border-radius: 12px;
}

.placeholder {
  color: #8b95a7;
  padding: 8px 0;
}

.permission-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.permission-item {
  margin-right: 0;
}

.save-row {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
