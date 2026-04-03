<template>
  <AppLayout>
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="openCreate">新增用户</el-button>
    </div>

    <el-table :data="store.list" v-loading="store.loading" stripe>
      <el-table-column prop="real_name" label="姓名" width="140" />
      <el-table-column prop="employee_no" label="工号" width="140" />
      <el-table-column prop="department" label="部门" min-width="180" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          {{ row.role_code === 'admin' ? '管理员' : '普通用户' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'enabled' ? 'success' : 'info'">
            {{ row.status === 'enabled' ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最近登录" width="170" />
      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link type="warning" @click="toggleStatus(row)">
            {{ row.status === 'enabled' ? '禁用' : '启用' }}
          </el-button>
          <el-button link type="info" @click="resetPassword(row)">重置密码</el-button>
          <el-button link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="520px">
      <el-form label-width="92px">
        <el-form-item label="工号">
          <el-input v-model="form.employee_no" :disabled="isEdit" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="初始密码">
          <el-input v-model="form.password" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_code" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="启用" value="enabled" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useUserAdminStore } from '@/stores/userAdmin'
import type { SysUser } from '@/types'

const store = useUserAdminStore()
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const form = reactive({
  employee_no: '',
  password: 'InitPass123',
  real_name: '',
  department: '',
  role_code: 'user' as 'admin' | 'user',
  status: 'enabled' as 'enabled' | 'disabled'
})

const isEdit = ref(false)

onMounted(() => {
  store.fetchList()
})

function resetForm() {
  form.employee_no = ''
  form.password = 'InitPass123'
  form.real_name = ''
  form.department = ''
  form.role_code = 'user'
  form.status = 'enabled'
}

function openCreate() {
  resetForm()
  editingId.value = null
  isEdit.value = false
  dialogVisible.value = true
}

function openEdit(row: SysUser) {
  editingId.value = row.id
  isEdit.value = true
  form.employee_no = row.employee_no
  form.real_name = row.real_name
  form.department = row.department
  form.role_code = row.role_code
  form.status = row.status
  dialogVisible.value = true
}

async function submitForm() {
  if (isEdit.value && editingId.value) {
    await store.editUser(editingId.value, {
      real_name: form.real_name,
      department: form.department,
      role_code: form.role_code,
      status: form.status
    })
  } else {
    await store.addUser({
      employee_no: form.employee_no,
      password: form.password,
      real_name: form.real_name,
      department: form.department,
      role_code: form.role_code,
      status: form.status
    })
  }
  dialogVisible.value = false
}

async function toggleStatus(row: SysUser) {
  const targetStatus = row.status === 'enabled' ? 'disabled' : 'enabled'
  await store.setUserStatus(row.id, targetStatus)
}

async function resetPassword(row: SysUser) {
  await ElMessageBox.confirm(`确认重置 ${row.real_name} 的密码为默认值？`, '确认重置')
  await store.updatePassword(row.id, 'InitPass123')
}

async function remove(row: SysUser) {
  await ElMessageBox.confirm(`确认删除用户 ${row.real_name}？`, '确认删除', { type: 'warning' })
  await store.removeUser(row.id)
}
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.page-header h2 {
  margin: 0;
}
</style>
