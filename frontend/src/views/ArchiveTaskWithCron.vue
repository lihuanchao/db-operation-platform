<template>
  <AppLayout>
    <div class="page-shell">
      <div class="page-header">
        <div class="page-title-group">
          <h2>归档任务管理</h2>
          <p v-if="locatedTask" class="page-context" data-testid="archive-context">
            已定位到任务：{{ locatedTask.task_name }}，共 1 条记录
          </p>
        </div>
        <el-button type="primary" @click="handleAddTask">
          <el-icon><Plus /></el-icon>
          新增归档任务
        </el-button>
      </div>

      <el-card shadow="never" class="filter-card">
        <el-form :model="filters" inline>
          <el-form-item label="任务名称">
            <el-input v-model="filters.task_name" placeholder="请输入任务名称" clearable />
          </el-form-item>
          <el-form-item label="源库连接">
            <el-select v-model="filters.source_connection_id" placeholder="请选择源库连接" clearable style="width: 200px">
              <el-option
                v-for="conn in connectionList"
                :key="conn.id"
                :label="conn.connection_name"
                :value="conn.id"
              />
            </el-select>
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
        <div class="table-wrap">
          <el-table :data="displayRows" v-loading="store.loading" stripe class="archive-table" table-layout="fixed" height="100%">
            <el-table-column prop="task_name" label="任务名称" min-width="110" show-overflow-tooltip />
            <el-table-column prop="source_connection.connection_name" label="源库连接" min-width="100" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.source_connection?.connection_name || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="source_database" label="源库" min-width="85" show-overflow-tooltip>
              <template #default="{ row }">
                <el-tag size="small">{{ row.source_database }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="source_table" label="源表" min-width="85" show-overflow-tooltip>
              <template #default="{ row }">
                <el-tag size="small">{{ row.source_table }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="dest_connection.connection_name" label="目标库连接" min-width="100" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.dest_connection?.connection_name || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="dest_database" label="目标库" min-width="85" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.dest_database || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="dest_table" label="目标表" min-width="85" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.dest_table || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="is_enabled" label="状态" min-width="72">
              <template #default="{ row }">
                <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
                  {{ row.is_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" min-width="130" show-overflow-tooltip />
            <el-table-column label="操作" min-width="150" align="center">
              <template #default="{ row }">
                <div class="action-buttons">
                  <el-button link type="primary" size="small" @click="handleExecute(row)">
                    执行
                  </el-button>
                  <el-button link type="primary" size="small" @click="handleCronManagement(row)">
                    定时
                  </el-button>
                  <el-button link type="primary" size="small" @click="handleEdit(row)">
                    编辑
                  </el-button>
                  <el-button link type="danger" size="small" @click="handleDelete(row)">
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <el-pagination
          :current-page="displayPage"
          :page-size="displayPerPage"
          :total="displayTotal"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          class="table-pagination"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </el-card>
    </div>

    <!-- 任务表单抽屉 -->
    <el-drawer
      v-model="formDialogVisible"
      :title="editingTask ? '编辑归档任务' : '新增归档任务'"
      direction="rtl"
      size="560px"
      class="archive-task-drawer"
      destroy-on-close
    >
      <div class="drawer-body">
        <el-form
          :model="formData"
          :rules="formRules"
          :show-message="false"
          label-width="96px"
          ref="formRef"
        >
          <section class="form-section">
            <div class="section-heading">
              <h3>核心信息</h3>
            </div>
            <el-form-item label="任务名称" prop="task_name">
              <el-input v-model="formData.task_name" placeholder="请输入任务名称" />
            </el-form-item>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="源连接" prop="source_connection_id">
                  <el-select v-model="formData.source_connection_id" placeholder="请选择源库连接" style="width: 100%">
                    <el-option
                      v-for="conn in connectionList"
                      :key="conn.id"
                      :label="conn.connection_name"
                      :value="conn.id"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="源库" prop="source_database">
                  <el-input v-model="formData.source_database" placeholder="请输入源库名称" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="源表" prop="source_table">
              <el-input v-model="formData.source_table" placeholder="请输入源表名称" />
            </el-form-item>
            <el-form-item label="归档条件" prop="where_condition">
              <el-input
                v-model="formData.where_condition"
                type="textarea"
                :rows="4"
                placeholder="请输入 WHERE 条件（如：CreateDate < '2026-02-01'）"
              />
            </el-form-item>
          </section>

          <section class="form-section">
            <div class="section-heading">
              <h3>高级配置</h3>
            </div>
            <el-row :gutter="16">
              <el-col :span="12">
                <el-form-item label="目标连接" prop="dest_connection_id">
                  <el-select v-model="formData.dest_connection_id" placeholder="请选择目标库连接" style="width: 100%" clearable>
                    <el-option
                      v-for="conn in connectionList"
                      :key="conn.id"
                      :label="conn.connection_name"
                      :value="conn.id"
                    />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="目标库" prop="dest_database">
                  <el-input v-model="formData.dest_database" placeholder="请输入目标库名称" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="目标表" prop="dest_table">
              <el-input v-model="formData.dest_table" placeholder="请输入目标表名称" />
            </el-form-item>
            <el-form-item label="启用状态">
              <el-switch v-model="formData.is_enabled" />
            </el-form-item>
          </section>
        </el-form>
      </div>
      <template #footer>
        <span class="drawer-footer">
          <el-button @click="formDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleFormSubmit" :loading="store.formLoading || isSubmitting" :disabled="store.formLoading || isSubmitting">
            {{ editingTask ? '保存' : '保存并执行' }}
          </el-button>
        </span>
      </template>
    </el-drawer>

    <!-- 定时任务管理对话框 -->
    <el-dialog
      v-model="cronDialogVisible"
      :title="currentTask?.task_name ? `定时任务管理 - ${currentTask.task_name}` : '定时任务管理'"
      width="800px"
      destroy-on-close
    >
      <div class="cron-dialog-content">
        <div class="cron-header">
          <el-button type="primary" @click="handleAddCron">
            <el-icon><Plus /></el-icon>
            新增定时任务
          </el-button>
        </div>

        <el-table :data="getCronJobsByTask(currentTask?.id || 0)" style="width: 100%">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="cron_expression" label="Cron表达式" width="180" />
          <el-table-column prop="next_run_time" label="下次运行时间" width="180">
            <template #default="{ row }">
              {{ row.next_run_time || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="last_run_time" label="上次运行时间" width="180">
            <template #default="{ row }">
              {{ row.last_run_time || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                {{ row.is_active ? '激活' : '暂停' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-button link type="primary" size="small" @click="handleToggleCron(row)">
                  {{ row.is_active ? '暂停' : '激活' }}
                </el-button>
                <el-button link type="primary" size="small" @click="handleEditCron(row)">
                  编辑
                </el-button>
                <el-button link type="danger" size="small" @click="handleDeleteCron(row)">
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 定时任务表单 -->
      <el-dialog
        v-model="cronFormDialogVisible"
        :title="editingCronJob ? '编辑定时任务' : '新增定时任务'"
        width="600px"
        destroy-on-close
      >
        <el-form
          :model="cronFormData"
          :rules="cronFormRules"
          :show-message="false"
          label-width="120px"
          ref="cronFormRef"
        >
          <el-form-item label="Cron表达式" prop="cron_expression">
            <el-input v-model="cronFormData.cron_expression" placeholder="例如：0 0 2 * * ? (每天凌晨2点执行)" />
          </el-form-item>
          <el-form-item label="说明">
            <div class="cron-help">
              <div>Cron表达式格式：秒 分 时 日 月 周</div>
              <div>示例：</div>
              <ul>
                <li>0 0 2 * * ? - 每天凌晨2点执行</li>
                <li>0 0 2 * * 0 - 每周日凌晨2点执行</li>
                <li>0 0 2 1 * ? - 每月1号凌晨2点执行</li>
              </ul>
            </div>
          </el-form-item>
          <el-form-item label="激活状态">
            <el-switch v-model="cronFormData.is_active" />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="cronFormDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleCronFormSubmit" :loading="cronStore.formLoading">
              确定
            </el-button>
          </span>
        </template>
      </el-dialog>
    </el-dialog>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Edit, Delete, VideoPlay, Switch } from '@element-plus/icons-vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useArchiveTaskStore } from '@/stores/archiveTask'
import { useCronJobStore } from '@/stores/cronJob'
import { useDbConnectionStore } from '@/stores/dbConnection'
import type { ArchiveTask, CronJob, DbConnection } from '@/types'

const store = useArchiveTaskStore()
const cronStore = useCronJobStore()
const connectionStore = useDbConnectionStore()
const route = useRoute()

const formDialogVisible = ref(false)
const cronDialogVisible = ref(false)
const cronFormDialogVisible = ref(false)
const isSubmitting = ref(false)
const editingTask = ref<ArchiveTask | null>(null)
const editingCronJob = ref<CronJob | null>(null)
const currentTask = ref<ArchiveTask | null>(null)
const locatedTask = ref<ArchiveTask | null>(null)
const formRef = ref()
const cronFormRef = ref()

const defaultFilters = {
  task_name: '',
  source_connection_id: undefined as number | undefined
}

const filters = ref({
  ...defaultFilters
})

type ArchiveTaskFormData = Omit<ArchiveTask, 'id' | 'created_at' | 'updated_at' | 'source_connection' | 'dest_connection' | 'source_connection_id'> & {
  source_connection_id: number | undefined
}

const formData = ref<ArchiveTaskFormData>({
  task_name: '',
  source_connection_id: undefined,
  source_database: '',
  source_table: '',
  dest_connection_id: undefined,
  dest_database: '',
  dest_table: '',
  where_condition: '',
  is_enabled: true
})

const cronFormData = ref<Omit<CronJob, 'id' | 'created_at' | 'updated_at' | 'next_run_time' | 'last_run_time'>>({
  task_id: 0,
  cron_expression: '',
  is_active: true
})

const formRules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  source_connection_id: [{ required: true, message: '请选择源库连接', trigger: 'change' }],
  source_database: [{ required: true, message: '请输入源库名称', trigger: 'blur' }],
  source_table: [{ required: true, message: '请输入源表名称', trigger: 'blur' }],
  where_condition: [{ required: true, message: '请输入归档条件', trigger: 'blur' }]
}

const cronFormRules = {
  cron_expression: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]
}

const connectionList = computed(() => connectionStore.list)
const displayRows = computed(() => (locatedTask.value ? [locatedTask.value] : store.list))
const displayTotal = computed(() => (locatedTask.value ? 1 : store.total))
const displayPage = computed(() => (locatedTask.value ? 1 : store.page))
const displayPerPage = computed(() => (locatedTask.value ? 1 : store.perPage))

function getCronJobsByTask(taskId: number) {
  return cronStore.list.filter(cron => cron.task_id === taskId)
}

function resolveRouteTaskId() {
  const routeTaskId = Array.isArray(route.params.id) ? route.params.id[0] : route.params.id
  const taskId = Number(routeTaskId)

  return Number.isInteger(taskId) && taskId > 0 ? taskId : null
}

async function syncRouteTaskContext() {
  filters.value = {
    ...defaultFilters
  }
  locatedTask.value = null
  store.resetFilters()

  const taskId = resolveRouteTaskId()
  if (taskId !== null) {
    try {
      const detail = await store.fetchDetail(taskId)
      if (detail) {
        locatedTask.value = detail
        return
      }
    } catch {
      locatedTask.value = null
    }
  }

  await store.fetchList()
}

watch(() => route.params.id, () => {
  void syncRouteTaskContext()
}, { immediate: true })

onMounted(async () => {
  await Promise.all([
    cronStore.fetchList(),
    connectionStore.fetchList()
  ])
})

function handleSearch() {
  store.setFilters(filters.value)
  store.fetchList()
}

function handleReset() {
  filters.value = {
    ...defaultFilters
  }
  locatedTask.value = null
  store.resetFilters()
  store.fetchList()
}

function handleAddTask() {
  editingTask.value = null
  formData.value = {
    task_name: '',
    source_connection_id: undefined,
    source_database: '',
    source_table: '',
    dest_connection_id: undefined,
    dest_database: '',
    dest_table: '',
    where_condition: '',
    is_enabled: true
  }
  formDialogVisible.value = true
}

function handleEdit(row: ArchiveTask) {
  editingTask.value = { ...row }
  formData.value = {
    task_name: row.task_name,
    source_connection_id: row.source_connection_id,
    source_database: row.source_database,
    source_table: row.source_table,
    dest_connection_id: row.dest_connection_id,
    dest_database: row.dest_database || '',
    dest_table: row.dest_table || '',
    where_condition: row.where_condition,
    is_enabled: row.is_enabled
  }
  formDialogVisible.value = true
}

function handleCronManagement(row: ArchiveTask) {
  currentTask.value = row
  cronDialogVisible.value = true
}

function handleAddCron() {
  if (!currentTask.value) return
  editingCronJob.value = null
  cronFormData.value = {
    task_id: currentTask.value.id!,
    cron_expression: '',
    is_active: true
  }
  cronFormDialogVisible.value = true
}

function handleEditCron(row: CronJob) {
  editingCronJob.value = { ...row }
  cronFormData.value = {
    task_id: row.task_id,
    cron_expression: row.cron_expression,
    is_active: row.is_active
  }
  cronFormDialogVisible.value = true
}

async function handleExecute(row: ArchiveTask) {
  try {
    await ElMessageBox.confirm(
      `确定要立即执行任务「${row.task_name}」吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await store.executeTask(row.id!)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('执行失败:', error)
    }
  }
}

async function handleDelete(row: ArchiveTask) {
  try {
    await ElMessageBox.confirm(
      `确定要删除任务「${row.task_name}」吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    if (row.id) {
      await store.removeTask(row.id)
      if (locatedTask.value?.id === row.id) {
        locatedTask.value = null
        if (currentTask.value?.id === row.id) {
          currentTask.value = null
          cronDialogVisible.value = false
        }
        filters.value = {
          ...defaultFilters
        }
        store.resetFilters()
        await store.fetchList()
      }
    }
  } catch {
    // User cancelled
  }
}

async function handleToggleCron(row: CronJob) {
  if (!row.id) return
  try {
    await cronStore.toggleJobStatus(row.id)
  } catch (error) {
    console.error('操作失败:', error)
  }
}

async function handleDeleteCron(row: CronJob) {
  try {
    await ElMessageBox.confirm(
      `确定要删除该定时任务吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    if (row.id) {
      await cronStore.removeJob(row.id)
    }
  } catch {
    // User cancelled
  }
}

async function handleFormSubmit() {
  if (isSubmitting.value) {
    return
  }
  isSubmitting.value = true

  try {
    try {
      await formRef.value?.validate()
    } catch (error) {
      console.error('表单校验失败:', error)
      return
    }

    let savedTask: ArchiveTask | null = null
    const editingTaskId = editingTask.value?.id
    const sourceConnectionId = formData.value.source_connection_id
    if (sourceConnectionId === undefined) {
      return
    }
    const submitPayload = {
      ...formData.value,
      source_connection_id: sourceConnectionId
    }

    if (editingTaskId) {
      savedTask = await store.editTask(editingTaskId, submitPayload) ?? null
    } else {
      savedTask = await store.addTask(submitPayload) ?? null
    }

    if (!savedTask) {
      return
    }

    if (savedTask && locatedTask.value?.id === savedTask.id) {
      locatedTask.value = {
        ...savedTask
      }
      if (currentTask.value?.id === savedTask.id) {
        currentTask.value = {
          ...savedTask
        }
      }
    }

    formDialogVisible.value = false

    if (!editingTaskId && savedTask.id) {
      try {
        const executeResult = await store.executeTask(savedTask.id)
        if (!executeResult) {
          ElMessage.warning('任务已创建成功，但自动执行失败，请在列表中手动点击“执行”重试。')
        }
      } catch (error) {
        console.error('自动执行失败:', error)
        ElMessage.warning('任务已创建成功，但自动执行失败，请在列表中手动点击“执行”重试。')
      }
    }
  } catch (error) {
    console.error('提交失败:', error)
    ElMessage.error('提交失败，请稍后重试。')
  } finally {
    isSubmitting.value = false
  }
}

async function handleCronFormSubmit() {
  await cronFormRef.value?.validate()
  try {
    if (editingCronJob.value?.id) {
      await cronStore.editJob(editingCronJob.value.id, cronFormData.value)
    } else {
      await cronStore.addJob(cronFormData.value)
    }
    cronFormDialogVisible.value = false
  } catch (error) {
    console.error('提交失败:', error)
  }
}

function handlePageChange(page: number) {
  store.goToPage(page)
}

function handleSizeChange(size: number) {
  store.setPageSize(size)
}
</script>

<style scoped>
.page-shell {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.action-buttons {
  display: flex;
  flex-direction: row;
  justify-content: center;
  gap: 0;
  flex-wrap: nowrap;
}

.action-buttons :deep(.el-button.is-link) {
  padding: 0 2px !important;
  min-width: auto !important;
  font-size: 12px;
}

.action-buttons :deep(.el-button + .el-button) {
  margin-left: 0 !important;
}


.page-header h2 {
  margin: 0;
  color: #1e3a5f;
}

.page-context {
  margin: 0;
  color: #51657c;
  font-size: 13px;
}

.filter-card {
  margin-bottom: 0;
}

.table-card {
  margin-bottom: 0;
  flex: 1;
  min-height: 0;
}

.table-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.table-pagination {
  margin-top: 6px;
  justify-content: flex-end;
}

.archive-table {
  width: 100%;
}

.table-card :deep(.el-card__body) {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.table-wrap :deep(.el-table) {
  width: 100%;
  height: 100%;
}

.table-wrap :deep(.el-table__inner-wrapper) {
  height: 100%;
}

.table-wrap :deep(.el-table__body-wrapper) {
  overflow-x: hidden !important;
}

.cron-dialog-content {
  padding: 10px 0;
}

.cron-header {
  margin-bottom: 15px;
}

.cron-help {
  font-size: 12px;
  color: #909399;
}

.cron-help ul {
  margin: 5px 0 0 20px;
  padding: 0;
}

.cron-help li {
  margin: 3px 0;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}

.drawer-body {
  height: 100%;
  overflow-y: auto;
  padding-right: 4px;
}

.form-section {
  padding: 18px 18px 8px;
  margin-bottom: 16px;
  border: 1px solid #e4ebf3;
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.section-heading {
  margin-bottom: 16px;
}

.section-heading h3 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: #1e3a5f;
}

.archive-task-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #e6edf5;
  color: #1e3a5f;
}

.archive-task-drawer :deep(.el-drawer__body) {
  padding: 18px 24px;
  background: #f5f8fc;
}

.archive-task-drawer :deep(.el-drawer__footer) {
  padding: 16px 24px 20px;
  border-top: 1px solid #e6edf5;
  background: #ffffff;
}
</style>
