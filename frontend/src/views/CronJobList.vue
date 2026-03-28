<template>
  <AppLayout>
    <div class="page-header">
      <h2>定时任务管理</h2>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新增定时任务
      </el-button>
    </div>

    <el-card shadow="never" class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="归档任务">
          <el-select v-model="filters.task_id" placeholder="请选择归档任务" clearable style="width: 250px">
            <el-option
              v-for="task in taskList"
              :key="task.id"
              :label="task.task_name"
              :value="task.id"
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
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="task_id" label="归档任务ID" width="120" />
        <el-table-column label="归档任务名称" width="200">
          <template #default="{ row }">
            {{ getTaskName(row.task_id) }}
          </template>
        </el-table-column>
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
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleToggle(row)">
              <el-icon><Switch /></el-icon>
              {{ row.is_active ? '暂停' : '激活' }}
            </el-button>
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
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

    <!-- 定时任务表单对话框 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="editingJob ? '编辑定时任务' : '新增定时任务'"
      width="600px"
      destroy-on-close
    >
      <el-form
        :model="formData"
        :rules="formRules"
        label-width="120px"
        ref="formRef"
      >
        <el-form-item label="归档任务" prop="task_id">
          <el-select v-model="formData.task_id" placeholder="请选择归档任务" style="width: 100%">
            <el-option
              v-for="task in taskList"
              :key="task.id"
              :label="task.task_name"
              :value="task.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Cron表达式" prop="cron_expression">
          <el-input v-model="formData.cron_expression" placeholder="例如：0 0 2 * * ? (每天凌晨2点执行)" />
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
          <el-switch v-model="formData.is_active" />
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
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, Edit, Delete, Switch } from '@element-plus/icons-vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useCronJobStore } from '@/stores/cronJob'
import { useArchiveTaskStore } from '@/stores/archiveTask'
import type { CronJob, ArchiveTask } from '@/types'

const store = useCronJobStore()
const taskStore = useArchiveTaskStore()

const formDialogVisible = ref(false)
const editingJob = ref<CronJob | null>(null)
const formRef = ref()

const filters = ref({
  task_id: undefined as number | undefined
})

const formData = ref<Omit<CronJob, 'id' | 'created_at' | 'updated_at' | 'next_run_time' | 'last_run_time'>>({
  task_id: 0,
  cron_expression: '',
  is_active: true
})

const formRules = {
  task_id: [{ required: true, message: '请选择归档任务', trigger: 'change' }],
  cron_expression: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]
}

const taskList = computed(() => taskStore.list)

function getTaskName(taskId: number) {
  const task = taskList.value.find(t => t.id === taskId)
  return task?.task_name || '-'
}

onMounted(async () => {
  await Promise.all([
    store.fetchList(),
    taskStore.fetchList()
  ])
})

function handleSearch() {
  store.setFilters(filters.value)
  store.fetchList()
}

function handleReset() {
  filters.value = {
    task_id: undefined
  }
  store.resetFilters()
  store.fetchList()
}

function handleAdd() {
  editingJob.value = null
  formData.value = {
    task_id: 0,
    cron_expression: '',
    is_active: true
  }
  formDialogVisible.value = true
}

function handleEdit(row: CronJob) {
  editingJob.value = { ...row }
  formData.value = {
    task_id: row.task_id,
    cron_expression: row.cron_expression,
    is_active: row.is_active
  }
  formDialogVisible.value = true
}

async function handleToggle(row: CronJob) {
  if (!row.id) return
  try {
    await store.toggleJobStatus(row.id)
  } catch (error) {
    console.error('操作失败:', error)
  }
}

async function handleDelete(row: CronJob) {
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
      await store.removeJob(row.id)
    }
  } catch {
    // User cancelled
  }
}

async function handleFormSubmit() {
  await formRef.value?.validate()
  try {
    if (editingJob.value?.id) {
      await store.editJob(editingJob.value.id, formData.value)
    } else {
      await store.addJob(formData.value)
    }
    formDialogVisible.value = false
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
