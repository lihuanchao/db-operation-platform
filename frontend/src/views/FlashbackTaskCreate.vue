<template>
  <AppLayout>
    <div class="page-shell">
      <div class="page-header">
        <div>
          <h2>新建数据闪回任务</h2>
          <p>连接、对象、时间窗口和 binlog 文件信息将提交给后端执行。</p>
        </div>
        <el-button class="ghost-btn back-btn" @click="goBack">返回列表</el-button>
      </div>

      <el-card shadow="never" class="form-shell">
        <template #header>
          <div class="card-title">任务配置</div>
        </template>

        <div class="connection-summary">
          <span class="connection-summary__label">连接摘要</span>
          <span class="connection-summary__value">
            {{ connectionSummary }}
          </span>
          <span class="connection-summary__mode">mode: repl</span>
        </div>

        <el-form ref="formRef" :model="formData" label-position="top" class="create-form">
          <el-row :gutter="16">
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="数据库连接" prop="db_connection_id">
                <el-select
                  v-model="formData.db_connection_id"
                  placeholder="请选择数据库连接"
                  filterable
                  class="full-width"
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
                <el-input v-model="formData.database_name" placeholder="数据库名" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="表名" prop="table_name">
                <el-input v-model="formData.table_name" placeholder="表名" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="SQL 类型" prop="sql_type">
                <el-select v-model="formData.sql_type" class="full-width">
                  <el-option label="delete" value="delete" />
                  <el-option label="insert" value="insert" />
                  <el-option label="update" value="update" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="输出类型" prop="work_type">
                <el-select v-model="formData.work_type" class="full-width">
                  <el-option label="2sql" value="2sql" />
                  <el-option label="rollback" value="rollback" />
                  <el-option label="stats" value="stats" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="模式">
                <el-input :model-value="'repl'" disabled />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="开始时间" prop="start_datetime">
                <el-input v-model="formData.start_datetime" placeholder="请输入开始时间" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="结束时间" prop="stop_datetime">
                <el-input v-model="formData.stop_datetime" placeholder="请输入结束时间" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="开始 binlog 文件" prop="start_file">
                <el-input v-model="formData.start_file" placeholder="请输入开始 binlog 文件" />
              </el-form-item>
            </el-col>
            <el-col :xs="24" :sm="24" :md="12">
              <el-form-item label="结束 binlog 文件" prop="stop_file">
                <el-input v-model="formData.stop_file" placeholder="请输入结束 binlog 文件" />
              </el-form-item>
            </el-col>
          </el-row>

          <div class="action-row">
            <el-button class="ghost-btn" @click="goBack">取消</el-button>
            <el-button type="primary" class="submit-btn" :loading="store.formLoading" @click="handleSubmit">
              提交任务
            </el-button>
          </div>
        </el-form>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { useFlashbackTaskStore } from '@/stores/flashbackTask'
import type { FlashbackSqlType, FlashbackWorkType } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const store = useFlashbackTaskStore()

const formData = reactive({
  db_connection_id: undefined as number | undefined,
  database_name: '',
  table_name: '',
  sql_type: 'delete' as FlashbackSqlType,
  work_type: '2sql' as FlashbackWorkType,
  start_datetime: '',
  stop_datetime: '',
  start_file: '',
  stop_file: ''
})

const selectedConnection = computed(() => {
  if (!formData.db_connection_id) {
    return null
  }

  return authStore.authorizedConnections.find(item => item.id === formData.db_connection_id) ?? null
})

const connectionSummary = computed(() => {
  if (!selectedConnection.value) {
    return '请选择连接后显示摘要'
  }

  return `${selectedConnection.value.connection_name} · ${selectedConnection.value.host}:${selectedConnection.value.port}`
})

onMounted(async () => {
  if (!authStore.authorizedConnections.length) {
    await authStore.fetchAuthorizedConnections()
  }

  if (!formData.db_connection_id && authStore.authorizedConnections.length === 1) {
    formData.db_connection_id = authStore.authorizedConnections[0].id
  }
})

function goBack() {
  router.push('/flashback-tasks')
}

async function handleSubmit() {
  if (!hasRequiredFields()) return

  const payload = {
    db_connection_id: formData.db_connection_id as number,
    database_name: formData.database_name.trim(),
    table_name: formData.table_name.trim(),
    sql_type: formData.sql_type,
    work_type: formData.work_type,
    ...(formData.start_datetime.trim() ? { start_datetime: formData.start_datetime.trim() } : {}),
    ...(formData.stop_datetime.trim() ? { stop_datetime: formData.stop_datetime.trim() } : {}),
    ...(formData.start_file.trim() ? { start_file: formData.start_file.trim() } : {}),
    ...(formData.stop_file.trim() ? { stop_file: formData.stop_file.trim() } : {})
  }

  const created = await store.createTask(payload)

  if (created?.id) {
    router.push(`/flashback-tasks/${created.id}`)
  }
}

function hasRequiredFields() {
  return Boolean(
    formData.db_connection_id &&
      formData.database_name.trim() &&
      formData.table_name.trim() &&
      formData.sql_type &&
      formData.work_type
  )
}
</script>

<style scoped src="../styles/task-create-workspace.css"></style>
<style scoped>
.page-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.connection-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #f7fbff;
  color: #28425c;
  font-size: 13px;
}

.connection-summary__label {
  font-weight: 700;
  color: #0f4c81;
}

.connection-summary__mode {
  margin-left: auto;
  color: #627089;
}

.create-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.full-width {
  width: 100%;
}
</style>
