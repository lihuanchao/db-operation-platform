<template>
  <AppLayout>
    <div class="page-header">
      <div class="header-main">
        <h2>创建 SQL 优化任务</h2>
        <p>选择连接后输入 SQL，系统将自动获取执行计划和建表语句并异步优化。</p>
      </div>
      <el-button class="ghost-btn" @click="goBack">返回列表</el-button>
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
                  v-for="conn in connectionList"
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

        <el-form-item label="SQL 内容" prop="sql_text" class="sql-area-item">
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
          <el-button type="primary" :loading="store.submitLoading" @click="handleSubmit">
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
import { getConnectionList } from '@/api/dbConnection'
import { useOptimizationTaskStore } from '@/stores/optimizationTask'
import type { DbConnection } from '@/types'

const router = useRouter()
const store = useOptimizationTaskStore()
const formRef = ref<FormInstance>()
const connectionList = ref<DbConnection[]>([])

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
  const res = await getConnectionList({ page: 1, per_page: 200 })
  if (res.data) {
    connectionList.value = res.data.items.filter(item => item.is_enabled)
  }
})

function goBack() {
  router.push('/optimization-tasks')
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  const task = await store.createSqlTask({
    db_connection_id: formData.value.db_connection_id as number,
    database_name: formData.value.database_name,
    sql_text: formData.value.sql_text
  })

  if (task?.id) {
    router.push(`/optimization-tasks/${task.id}`)
  } else {
    ElMessage.error('创建任务失败')
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.header-main h2 {
  margin: 0;
  color: #1f2d3d;
  letter-spacing: 0.3px;
}

.header-main p {
  margin: 8px 0 0;
  color: #637381;
  font-size: 13px;
}

.form-shell {
  border: 1px solid #e8edf4;
  border-radius: 14px;
  background:
    radial-gradient(circle at right top, rgba(108, 92, 231, 0.08), transparent 45%),
    #ffffff;
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  color: #22324a;
}

.sql-area-item :deep(.el-textarea__inner) {
  font-family: 'Consolas', 'Monaco', 'SFMono-Regular', monospace;
  line-height: 1.6;
  border-radius: 10px;
}

.text-counter {
  margin-top: 8px;
  text-align: right;
  font-size: 12px;
  color: #8b95a7;
}

.action-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}

.ghost-btn {
  border-color: #d7deeb;
  color: #42526e;
}
</style>
