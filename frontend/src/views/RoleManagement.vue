<template>
  <AppLayout>
    <div class="page-header">
      <h2>角色管理</h2>
      <p>固定角色：管理员 / 普通用户</p>
    </div>

    <el-row :gutter="16">
      <el-col v-for="role in permissionStore.roles" :key="role.code" :xs="24" :md="12">
        <el-card class="role-card" shadow="never">
          <div class="role-head">
            <h3>{{ role.name }}</h3>
            <el-tag :type="role.code === 'admin' ? 'danger' : 'success'" effect="light">{{ role.code }}</el-tag>
          </div>
          <div class="desc-line">
            <span class="label">数据范围</span>
            <span class="value">{{ role.data_scope }}</span>
          </div>
          <div class="desc-line">
            <span class="label">页面权限</span>
          </div>
          <div class="page-tags">
            <el-tag v-for="page in role.pages" :key="page" round>{{ page }}</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { usePermissionAdminStore } from '@/stores/permissionAdmin'

const permissionStore = usePermissionAdminStore()

onMounted(() => {
  permissionStore.fetchRoles()
})
</script>

<style scoped>
.page-header {
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
}

.page-header p {
  margin: 6px 0 0;
  color: #67758c;
  font-size: 13px;
}

.role-card {
  margin-bottom: 14px;
  border-radius: 14px;
  border: 1px solid #e8edf6;
}

.role-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.role-card h3 {
  margin: 0;
  font-size: 19px;
  color: #1f2d3d;
}

.desc-line {
  margin: 8px 0;
  color: #44526b;
}

.label {
  display: inline-block;
  min-width: 68px;
  color: #6b7a92;
  font-size: 13px;
}

.value {
  color: #1f2d3d;
  font-weight: 500;
}

.page-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
