<template>
  <AppLayout>
    <div class="page-header">
      <h2>归档任务管理</h2>
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
      <el-table :data="store.list" v-loading="store.loading" stripe style="width: 100%">
        <el-table-column prop="task_name" label="任务名称" min-width="150" />
        <el-table-column prop="source_connection.connection_name" label="源库连接" min-width="130">
          <template #default="{ row }">
            {{ row.source_connection?.connection_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="source_database" label="源库" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.source_database }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_table" label="源表" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.source_table }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="dest_connection.connection_name" label="目标库连接" min-width="130">
          <template #default="{ row }">
            {{ row.dest_connection?.connection_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="dest_database" label="目标库" width="120">
          <template #default="{ row }">
            {{ row.dest_database || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="dest_table" label="目标表" width="120">
          <template #default="{ row }">
            {{ row.dest_table || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right" align="center">
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

      <el-pagination
        v-model:current-page="store.page"
        v-model:page-size="store.perPage"
        :total="store.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </el-card>

    <!-- 任务表单对话框 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="editingTask ? '编辑任务' : '新增任务'"
      width="800px"
      destroy-on-close
    >
      <el-form
        :model="formData"
        :rules="formRules"
        label-width="120px"
        ref="formRef"
      >
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="formData.task_name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="源库连接" prop="source_connection_id">
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
            <el-form-item label="源库名称" prop="source_database">
              <el-input v-model="formData.source_database" placeholder="请输入源库名称" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="源表名称" prop="source_table">
          <el-input v-model="formData.source_table" placeholder="请输入源表名称" />
        </el-form-item>
        <el-divider content-position="left">目标库配置（可选）</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="目标库连接" prop="dest_connection_id">
              <el-select v-model="formData.dest_connection_id" placeholder="请选择目标库连接（可选）" style="width: 100%" clearable>
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
            <el-form-item label="目标库名称" prop="dest_database">
              <el-input v-model="formData.dest_database" placeholder="请输入目标库名称（可选）" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="目标表名称" prop="dest_table">
          <el-input v-model="formData.dest_table" placeholder="请输入目标表名称（可选）" />
        </el-form-item>
        <el-form-item label="归档条件" prop="where_condition">
          <el-input
            v-model="formData.where_condition"
            type="textarea"
            :rows="3"
            placeholder="请输入 WHERE 条件（如：CreateDate < '2026-02-01'）"
          />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="formData.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="formDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleFormSubmit" :loading="store.formLoading">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>

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
          <el-table-column label="操作" width="120" fixed="right">
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
import { ref, onMounted, computed } from 'vue'
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

const formDialogVisible = ref(false)
const cronDialogVisible = ref(false)
const cronFormDialogVisible = ref(false)
const editingTask = ref<ArchiveTask | null>(null)
const editingCronJob = ref<CronJob | null>(null)
const currentTask = ref<ArchiveTask | null>(null)
const formRef = ref()
const cronFormRef = ref()

const filters = ref({
  task_name: '',
  source_connection_id: undefined as number | undefined
})

const formData = ref<Omit<ArchiveTask, 'id' | 'created_at' | 'updated_at' | 'source_connection' | 'dest_connection'>>({
  task_name: '',
  source_connection_id: 0,
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
const taskList = computed(() => store.list)

function getCronJobsByTask(taskId: number) {
  return cronStore.list.filter(cron => cron.task_id === taskId)
}

onMounted(async () => {
  await Promise.all([
    store.fetchList(),
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
    task_name: '',
    source_connection_id: undefined
  }
  store.resetFilters()
  store.fetchList()
}

function handleAddTask() {
  editingTask.value = null
  formData.value = {
    task_name: '',
    source_connection_id: 0,
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
  await formRef.value?.validate()
  try {
    if (editingTask.value?.id) {
      await store.editTask(editingTask.value.id, formData.value)
    } else {
      await store.addTask(formData.value)
    }
    formDialogVisible.value = false
  } catch (error) {
    console.error('提交失败:', error)
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
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  flex-direction: row;
  justify-content: center;
  gap: 1px;
  flex-wrap: nowrap;
}

.action-buttons .el-button {
  padding: 2px 4px;
  font-size: 12px;
}


.page-header h2 {
  margin: 0;
  color: #1e3a5f;
}

.filter-card {
  margin-bottom: 20px;
}

.table-card {
  margin-bottom: 20px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
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
</style>
