<template>
  <AppLayout>
    <div class="page-header">
      <h2>角色管理</h2>
    </div>
    <el-row :gutter="16">
      <el-col v-for="role in permissionStore.roles" :key="role.code" :xs="24" :md="12">
        <el-card class="role-card" shadow="never">
          <h3>{{ role.name }}</h3>
          <p><strong>编码：</strong>{{ role.code }}</p>
          <p><strong>页面权限：</strong>{{ role.pages.join('，') }}</p>
          <p><strong>数据范围：</strong>{{ role.data_scope }}</p>
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
  margin-bottom: 14px;
}

.page-header h2 {
  margin: 0;
}

.role-card {
  margin-bottom: 12px;
  border-radius: 12px;
}

.role-card h3 {
  margin: 0 0 8px;
}

.role-card p {
  margin: 6px 0;
  color: #42526e;
}
</style>
