<template>
  <AppLayout>
    <div class="page-header">
      <h2>创建 SQL 优化任务</h2>
      <el-button class="ghost-btn back-btn" @click="goBack">返回列表</el-button>
    </div>

    <el-card shadow="never" class="form-shell">
      <template #header>
        <div class="card-title">任务配置</div>
      </template>

      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-width="96px"
        label-position="top"
      >
        <el-row :gutter="16">
          <el-col :xs="24" :sm="24" :md="12">
            <el-form-item label="数据库连接" prop="db_connection_id">
              <el-select
                v-model="formData.db_connection_id"
                placeholder="请选择数据库连接"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="conn in authStore.authorizedConnections"
                  :key="conn.id"
                  :label="`${conn.connection_name} (${conn.host}:${conn.port})`"
                  :value="conn.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="12">
            <el-form-item label="数据库名" prop="database_name">
              <el-input v-model="formData.database_name" placeholder="请输入数据库名" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="SQL 内容" prop="sql_text" class="content-area-item">
          <el-input
            v-model="formData.sql_text"
            type="textarea"
            :rows="15"
            resize="none"
            placeholder="请输入待优化 SQL（仅支持查询语句）"
          />
          <div class="text-counter">{{ formData.sql_text.length }} 字符</div>
        </el-form-item>

        <div class="action-row">
          <el-button class="ghost-btn" @click="goBack">取消</el-button>
          <el-button
            type="primary"
            class="submit-btn"
            :loading="store.submitLoading"
            @click="handleSubmit"
          >
            开始优化
          </el-button>
        </div>
      </el-form>
    </el-card>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useOptimizationTaskStore } from '@/stores/optimizationTask'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const store = useOptimizationTaskStore()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const formData = ref({
  db_connection_id: undefined as number | undefined,
  database_name: '',
  sql_text: ''
})

const rules = {
  db_connection_id: [{ required: true, message: '请选择数据库连接', trigger: 'change' }],
  database_name: [{ required: true, message: '请输入数据库名', trigger: 'blur' }],
  sql_text: [{ required: true, message: '请输入SQL内容', trigger: 'blur' }]
}

onMounted(async () => {
  if (!authStore.authorizedConnections.length) {
    await authStore.fetchAuthorizedConnections()
  }
})

function goBack() {
  router.push('/optimization-tasks')
}

function hasRequiredFields() {
  return Boolean(
    formData.value.db_connection_id &&
      formData.value.database_name.trim() &&
      formData.value.sql_text.trim()
  )
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid || !hasRequiredFields()) return

  const task = await store.createSqlTask({
    db_connection_id: formData.value.db_connection_id as number,
    database_name: formData.value.database_name.trim(),
    sql_text: formData.value.sql_text.trim()
  })

  if (task?.id) {
    router.push(`/optimization-tasks/${task.id}`)
  } else {
    ElMessage.error('创建任务失败')
  }
}
</script>

<style scoped src="../styles/task-create-workspace.css"></style>
