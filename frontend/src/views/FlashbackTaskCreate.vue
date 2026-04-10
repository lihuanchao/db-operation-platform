<template>
  <AppLayout>
    <section class="page-shell">
      <header class="hero-header">
        <div class="hero-copy">
          <h2>新建数据闪回任务</h2>
          <p>配置连接、对象与回放范围后提交执行。</p>
        </div>
        <div class="hero-actions">
          <span class="mode-badge">Mode: repl</span>
          <el-button class="ghost-btn back-btn" @click="goBack">返回列表</el-button>
        </div>
      </header>

      <div class="flat-panel">
        <div class="connection-summary">
          <span class="connection-summary__label">连接摘要</span>
          <span class="connection-summary__value">
            {{ connectionSummary }}
          </span>
        </div>

        <el-form ref="formRef" :model="formData" label-position="top" class="create-form">
          <section class="form-section form-section--base">
            <div class="section-head">
              <h3>基础信息</h3>
              <span class="section-tag">必填</span>
            </div>
            <el-row :gutter="16" class="row-conn-mode">
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
                <el-form-item label="模式">
                  <el-input :model-value="'repl'" disabled />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16" class="row-sql-output">
              <el-col :xs="24" :sm="24" :md="12">
                <el-form-item label="SQL 类型" prop="sql_type">
                  <el-radio-group v-model="formData.sql_type" class="chip-group">
                    <el-radio-button value="delete">delete</el-radio-button>
                    <el-radio-button value="insert">insert</el-radio-button>
                    <el-radio-button value="update">update</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="24" :md="12">
                <el-form-item label="输出类型" prop="work_type">
                  <el-radio-group v-model="formData.work_type" class="chip-group">
                    <el-radio-button value="2sql">2sql</el-radio-button>
                    <el-radio-button value="rollback">rollback</el-radio-button>
                    <el-radio-button value="stats">stats</el-radio-button>
                  </el-radio-group>
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="16" class="row-db-table">
              <el-col :xs="24" :sm="24" :md="12">
                <el-form-item label="数据库名" prop="database_name">
                  <el-input v-model="formData.database_name" placeholder="数据库名" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :sm="24" :md="12">
                <el-form-item label="表名" prop="table_name">
                  <el-input v-model="formData.table_name" placeholder="表名" />
                </el-form-item>
              </el-col>
            </el-row>
          </section>

          <div class="split-sections">
            <section class="form-section form-section--time">
              <div class="section-head">
                <h3>时间窗口</h3>
                <span class="section-tag section-tag--muted">可选</span>
              </div>
              <el-row :gutter="12">
                <el-col :xs="24" :sm="24" :md="12">
                  <el-form-item label="开始时间" prop="start_datetime">
                    <el-date-picker
                      v-model="formData.start_datetime"
                      type="datetime"
                      value-format="YYYY-MM-DD HH:mm:ss"
                      format="YYYY-MM-DD HH:mm:ss"
                      placeholder="请选择开始时间"
                      class="full-width"
                      clearable
                    />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="24" :md="12">
                  <el-form-item label="结束时间" prop="stop_datetime">
                    <el-date-picker
                      v-model="formData.stop_datetime"
                      type="datetime"
                      value-format="YYYY-MM-DD HH:mm:ss"
                      format="YYYY-MM-DD HH:mm:ss"
                      placeholder="请选择结束时间"
                      class="full-width"
                      clearable
                    />
                  </el-form-item>
                </el-col>
              </el-row>
            </section>

            <section class="form-section form-section--binlog">
              <div class="section-head">
                <h3>Binlog 范围</h3>
                <span class="section-tag section-tag--muted">可选</span>
              </div>
              <el-row :gutter="12">
                <el-col :xs="24" :sm="24" :md="12">
                  <el-form-item label="开始文件" prop="start_file">
                    <el-input v-model="formData.start_file" placeholder="请输入开始 binlog 文件" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :sm="24" :md="12">
                  <el-form-item label="结束文件" prop="stop_file">
                    <el-input v-model="formData.stop_file" placeholder="请输入结束 binlog 文件" />
                  </el-form-item>
                </el-col>
              </el-row>
            </section>
          </div>

          <div class="action-row">
            <div class="action-buttons">
              <el-button class="ghost-btn" @click="goBack">取消</el-button>
              <el-button type="primary" class="submit-btn" :loading="store.formLoading" @click="handleSubmit">
                提交任务
              </el-button>
            </div>
          </div>
        </el-form>
      </div>
    </section>
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
  start_datetime: '' as string | null,
  stop_datetime: '' as string | null,
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
  const startDatetime = normalizeOptionalString(formData.start_datetime)
  const stopDatetime = normalizeOptionalString(formData.stop_datetime)

  const payload = {
    db_connection_id: formData.db_connection_id as number,
    database_name: formData.database_name.trim(),
    table_name: formData.table_name.trim(),
    sql_type: formData.sql_type,
    work_type: formData.work_type,
    ...(startDatetime ? { start_datetime: startDatetime } : {}),
    ...(stopDatetime ? { stop_datetime: stopDatetime } : {}),
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

function normalizeOptionalString(value: string | null | undefined) {
  if (typeof value !== 'string') {
    return ''
  }
  return value.trim()
}
</script>

<style scoped>
.page-shell {
  width: 100%;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-bottom: 2px;
}

.hero-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 2px 0;
  border-radius: 0;
  background: transparent;
}

.hero-copy h2 {
  margin: 0;
  color: #153253;
  letter-spacing: 0.2px;
  font-size: 16px;
  font-weight: 700;
}

.hero-copy p {
  margin: 2px 0 0;
  color: #64778f;
  font-size: 11px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mode-badge {
  height: 22px;
  padding: 0 8px;
  display: inline-flex;
  align-items: center;
  border: 1px solid #c8d8ec;
  border-radius: 0;
  background: #eef5ff;
  color: #2b4c73;
  font-size: 11px;
  font-weight: 600;
}

.flat-panel {
  width: 100%;
  border: none;
  background: #ffffff;
  border-radius: 0;
  padding: 0;
}

.connection-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  padding: 5px 8px;
  border: 1px solid #d5e3f3;
  border-left: 3px solid #4f7eb8;
  border-radius: 0;
  background: #f4f9ff;
  color: #2b4663;
  font-size: 12px;
}

.connection-summary__label {
  font-weight: 700;
  color: #1f4f80;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.split-sections {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.form-section {
  padding: 4px 0;
  border: none;
  border-radius: 0;
  background: transparent;
}

.section-head {
  margin-bottom: 4px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e8f0fa;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-head h3 {
  margin: 0;
  color: #1f334f;
  font-size: 12px;
  font-weight: 700;
}

.section-tag {
  height: 18px;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
  border: 1px solid #b8cee9;
  color: #2d5788;
  font-size: 10px;
  font-weight: 600;
}

.section-tag--muted {
  border-color: #d2dce9;
  color: #698099;
}

.create-form :deep(.el-form-item) {
  margin-bottom: 4px;
}

.create-form :deep(.el-form-item__label) {
  padding-bottom: 2px;
  font-weight: 600;
  font-size: 11px;
  color: #2a3d57;
}

.create-form :deep(.el-input__wrapper),
.create-form :deep(.el-select__wrapper),
.create-form :deep(.el-date-editor.el-input__wrapper) {
  min-height: 29px;
  border-radius: 0 !important;
}

.create-form :deep(.el-radio-group) {
  display: inline-flex;
}

.create-form :deep(.el-radio-button__inner) {
  padding: 4px 9px;
  font-size: 11px;
  border-radius: 0 !important;
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: 2px;
  padding-top: 6px;
  border-top: 1px solid #e7eef7;
  gap: 8px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.full-width {
  width: 100%;
}

.create-form :deep(.el-button),
.hero-actions :deep(.el-button) {
  border-radius: 0 !important;
}

@media (max-width: 960px) {
  .page-shell {
    gap: 10px;
  }

  .hero-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-actions {
    width: 100%;
    justify-content: space-between;
  }

  .split-sections {
    grid-template-columns: 1fr;
  }

  .action-row {
    justify-content: flex-end;
  }
}
</style>
