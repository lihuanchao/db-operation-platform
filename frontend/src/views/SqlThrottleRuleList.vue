<template>
  <AppLayout>
    <div class="page-shell">
      <div class="page-header">
        <div>
          <h2>SQL 限流规则</h2>
          <p>按规则自动识别高并发慢 SQL，支持演练模式与立即执行验证。</p>
        </div>
        <el-button type="primary" data-testid="create-rule-btn" @click="openCreateDialog">新建规则</el-button>
      </div>

      <el-card shadow="never" class="filter-card">
        <el-form :model="filters" inline class="filter-form">
          <el-form-item label="规则名称">
            <el-input
              v-model="filters.rule_name"
              class="filter-control"
              clearable
              placeholder="请输入规则名称"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="启用状态">
            <el-select v-model="filters.enabled" clearable class="filter-control" placeholder="全部">
              <el-option :value="true" label="已启用" />
              <el-option :value="false" label="已停用" />
            </el-select>
          </el-form-item>
          <el-form-item class="filter-actions">
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="table-card">
        <el-table :data="store.ruleList" v-loading="store.loadingRules" stripe>
          <el-table-column prop="rule_name" label="规则名称" min-width="180" />
          <el-table-column prop="connection_name" label="连接" min-width="130" />
          <el-table-column prop="mysql_version" label="MySQL版本" min-width="120">
            <template #default="{ row }">
              {{ row.mysql_version || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="阈值" min-width="200">
            <template #default="{ row }">
              <span>{{ row.slow_sql_seconds }}s / 并发{{ row.fingerprint_concurrency_threshold }}</span>
            </template>
          </el-table-column>
          <el-table-column label="执行策略" min-width="180">
            <template #default="{ row }">
              <span>{{ row.poll_interval_seconds }}s轮询 · 每轮最多{{ row.max_kill_per_round }}条</span>
            </template>
          </el-table-column>
          <el-table-column label="演练模式" width="100">
            <template #default="{ row }">
              <el-tag :type="row.dry_run ? 'warning' : 'success'" size="small">
                {{ row.dry_run ? '演练' : '实杀' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
                {{ row.enabled ? '已启用' : '已停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="最近执行" min-width="140">
            <template #default="{ row }">
              {{ row.last_run_at || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="340" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
                <el-button link type="primary" @click="goRuns(row)">运行记录</el-button>
                <el-button
                  link
                  :type="row.enabled ? 'warning' : 'success'"
                  @click="toggleRule(row)"
                >
                  {{ row.enabled ? '停用' : '启用' }}
                </el-button>
                <el-button link type="primary" :data-run-rule-id="row.id" @click="runNow(row.id)">立即执行</el-button>
                <el-button link type="danger" @click="removeRule(row.id)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="store.rulePage"
          v-model:page-size="store.rulePerPage"
          :total="store.ruleTotal"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          class="table-pagination"
          @current-change="store.fetchRuleList"
          @size-change="handleRuleSizeChange"
        />
      </el-card>
    </div>

    <el-dialog v-model="dialogVisible" :title="editingRuleId ? '编辑限流规则' : '新建限流规则'" width="760px">
      <el-form ref="ruleFormRef" :model="formModel" :rules="formRules" label-width="140px">
        <el-form-item label="规则名称" prop="rule_name" required>
          <el-input v-model="formModel.rule_name" />
        </el-form-item>
        <el-form-item label="数据库连接" prop="db_connection_id" required>
          <el-select v-model="formModel.db_connection_id" class="full-width" placeholder="请选择连接">
            <el-option v-for="item in connectionOptions" :key="item.id" :value="item.id!" :label="item.connection_name" />
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="慢 SQL 阈值" prop="slow_sql_seconds" required>
              <el-input-number v-model="formModel.slow_sql_seconds" :min="1" :step="1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="并发阈值" prop="fingerprint_concurrency_threshold" required>
              <el-input-number v-model="formModel.fingerprint_concurrency_threshold" :min="2" :step="1" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="连续命中" prop="consecutive_hit_times" required>
              <el-input-number v-model="formModel.consecutive_hit_times" :min="1" :step="1" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="采样周期(秒)" prop="poll_interval_seconds" required>
              <el-input-number v-model="formModel.poll_interval_seconds" :min="5" :step="1" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单轮最大 Kill" prop="max_kill_per_round" required>
              <el-input-number v-model="formModel.max_kill_per_round" :min="1" :step="1" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="排除用户">
          <el-select
            v-model="formModel.exclude_users"
            class="full-width"
            multiple
            filterable
            allow-create
            default-first-option
            clearable
            collapse-tags
            collapse-tags-tooltip
            :reserve-keyword="false"
            placeholder="可输入后回车，如 replication、monitor"
          >
            <el-option
              v-for="item in exclusionSuggestions.users"
              :key="`exclude-user-${item}`"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排除 DB">
          <el-select
            v-model="formModel.exclude_dbs"
            class="full-width"
            multiple
            filterable
            allow-create
            default-first-option
            clearable
            collapse-tags
            collapse-tags-tooltip
            :reserve-keyword="false"
            placeholder="可输入后回车，如 mysql、information_schema"
          />
        </el-form-item>
        <el-form-item label="排除主机">
          <el-select
            v-model="formModel.exclude_hosts"
            class="full-width"
            multiple
            filterable
            allow-create
            default-first-option
            clearable
            collapse-tags
            collapse-tags-tooltip
            :reserve-keyword="false"
            placeholder="可输入后回车，如 127.0.0.1、10.0.0.5"
          />
        </el-form-item>
        <el-form-item label="排除指纹">
          <el-select
            v-model="formModel.exclude_fingerprints"
            class="full-width"
            multiple
            filterable
            allow-create
            default-first-option
            clearable
            collapse-tags
            collapse-tags-tooltip
            :reserve-keyword="false"
            placeholder="可输入后回车，支持粘贴 SQL 指纹"
          />
        </el-form-item>
        <el-form-item label="演练模式">
          <el-switch v-model="formModel.dry_run" />
        </el-form-item>
        <el-form-item label="启用规则">
          <el-switch v-model="formModel.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" data-testid="save-rule-btn" @click="submitRule">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useSqlThrottleStore } from '@/stores/sqlThrottle'
import { getConnectionList } from '@/api/dbConnection'
import type { DbConnection, SqlThrottleRule } from '@/types'

interface RuleFormModel {
  rule_name: string
  db_connection_id: number | undefined
  enabled: boolean
  slow_sql_seconds: number
  fingerprint_concurrency_threshold: number
  poll_interval_seconds: number
  max_kill_per_round: number
  consecutive_hit_times: number
  dry_run: boolean
  exclude_users: string[]
  exclude_hosts: string[]
  exclude_dbs: string[]
  exclude_fingerprints: string[]
}

const store = useSqlThrottleStore()
const router = useRouter()
const connectionOptions = ref<DbConnection[]>([])
const dialogVisible = ref(false)
const editingRuleId = ref<number | null>(null)
const ruleFormRef = ref<FormInstance>()

const exclusionSuggestions = {
  users: ['replication', 'backup', 'monitor', 'mysqld_exporter']
}

const filters = reactive({
  rule_name: '',
  enabled: undefined as boolean | undefined
})

const formModel = reactive<RuleFormModel>({
  rule_name: '',
  db_connection_id: undefined,
  enabled: true,
  slow_sql_seconds: 10,
  fingerprint_concurrency_threshold: 20,
  poll_interval_seconds: 15,
  max_kill_per_round: 10,
  consecutive_hit_times: 2,
  dry_run: true,
  exclude_users: [],
  exclude_hosts: [],
  exclude_dbs: [],
  exclude_fingerprints: []
})

const formRules: FormRules<RuleFormModel> = {
  rule_name: [
    { required: true, message: '规则名称不能为空', trigger: ['blur', 'change'] }
  ],
  db_connection_id: [
    { required: true, message: '请选择数据库连接', trigger: ['change'] }
  ],
  slow_sql_seconds: [
    { required: true, type: 'number', message: '慢 SQL 阈值不能为空', trigger: ['change', 'blur'] },
    {
      validator: (_rule, value, callback) => {
        if (typeof value !== 'number' || value < 1) {
          callback(new Error('慢 SQL 阈值必须大于 0'))
          return
        }
        callback()
      },
      trigger: ['change', 'blur']
    }
  ],
  fingerprint_concurrency_threshold: [
    { required: true, type: 'number', message: '并发阈值不能为空', trigger: ['change', 'blur'] },
    {
      validator: (_rule, value, callback) => {
        if (typeof value !== 'number' || value < 2) {
          callback(new Error('并发阈值必须大于 1'))
          return
        }
        callback()
      },
      trigger: ['change', 'blur']
    }
  ],
  poll_interval_seconds: [
    { required: true, type: 'number', message: '采样周期不能为空', trigger: ['change', 'blur'] },
    {
      validator: (_rule, value, callback) => {
        if (typeof value !== 'number' || value < 5) {
          callback(new Error('采样周期必须大于等于 5 秒'))
          return
        }
        callback()
      },
      trigger: ['change', 'blur']
    }
  ],
  max_kill_per_round: [
    { required: true, type: 'number', message: '单轮最大 Kill 不能为空', trigger: ['change', 'blur'] },
    {
      validator: (_rule, value, callback) => {
        if (typeof value !== 'number' || value < 1) {
          callback(new Error('单轮最大 Kill 必须大于 0'))
          return
        }
        callback()
      },
      trigger: ['change', 'blur']
    }
  ],
  consecutive_hit_times: [
    { required: true, type: 'number', message: '连续命中次数不能为空', trigger: ['change', 'blur'] },
    {
      validator: (_rule, value, callback) => {
        if (typeof value !== 'number' || value < 1) {
          callback(new Error('连续命中次数必须大于等于 1'))
          return
        }
        callback()
      },
      trigger: ['change', 'blur']
    }
  ]
}

onMounted(async () => {
  await Promise.all([
    loadConnections(),
    store.fetchRuleList()
  ])
})

function normalizeList(raw: string[]) {
  const deduped = new Set(
    raw
      .map(item => item.trim())
      .filter(Boolean)
  )
  return Array.from(deduped)
}

function resetForm() {
  editingRuleId.value = null
  formModel.rule_name = ''
  formModel.db_connection_id = undefined
  formModel.enabled = true
  formModel.slow_sql_seconds = 10
  formModel.fingerprint_concurrency_threshold = 20
  formModel.poll_interval_seconds = 15
  formModel.max_kill_per_round = 10
  formModel.consecutive_hit_times = 2
  formModel.dry_run = true
  formModel.exclude_users = []
  formModel.exclude_hosts = []
  formModel.exclude_dbs = []
  formModel.exclude_fingerprints = []
  ruleFormRef.value?.clearValidate()
}

async function loadConnections() {
  const res = await getConnectionList({
    page: 1,
    per_page: 500
  })
  connectionOptions.value = res.data?.items || []
}

function handleSearch() {
  store.ruleFilters.rule_name = filters.rule_name
  store.ruleFilters.enabled = filters.enabled
  store.rulePage = 1
  store.fetchRuleList()
}

function handleReset() {
  filters.rule_name = ''
  filters.enabled = undefined
  store.ruleFilters.rule_name = ''
  store.ruleFilters.enabled = undefined
  store.rulePage = 1
  store.fetchRuleList()
}

function handleRuleSizeChange() {
  store.rulePage = 1
  store.fetchRuleList()
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: SqlThrottleRule) {
  editingRuleId.value = row.id
  formModel.rule_name = row.rule_name
  formModel.db_connection_id = row.db_connection_id
  formModel.enabled = row.enabled
  formModel.slow_sql_seconds = row.slow_sql_seconds
  formModel.fingerprint_concurrency_threshold = row.fingerprint_concurrency_threshold
  formModel.poll_interval_seconds = row.poll_interval_seconds
  formModel.max_kill_per_round = row.max_kill_per_round
  formModel.consecutive_hit_times = row.consecutive_hit_times
  formModel.dry_run = row.dry_run
  formModel.exclude_users = [...row.exclude_users]
  formModel.exclude_hosts = [...row.exclude_hosts]
  formModel.exclude_dbs = [...row.exclude_dbs]
  formModel.exclude_fingerprints = [...row.exclude_fingerprints]
  ruleFormRef.value?.clearValidate()
  dialogVisible.value = true
}

async function submitRule() {
  const formInstance = ruleFormRef.value
  if (!formInstance) {
    ElMessage.error('请先修正表单中的校验错误')
    return
  }
  const valid = await formInstance.validate().catch(() => false)
  if (!valid) {
    ElMessage.error('请先修正表单中的校验错误')
    return
  }
  if (formModel.db_connection_id === undefined) {
    ElMessage.error('请先修正表单中的校验错误')
    return
  }

  const payload = {
    rule_name: formModel.rule_name.trim(),
    db_connection_id: formModel.db_connection_id,
    enabled: formModel.enabled,
    slow_sql_seconds: formModel.slow_sql_seconds,
    fingerprint_concurrency_threshold: formModel.fingerprint_concurrency_threshold,
    poll_interval_seconds: formModel.poll_interval_seconds,
    max_kill_per_round: formModel.max_kill_per_round,
    consecutive_hit_times: formModel.consecutive_hit_times,
    dry_run: formModel.dry_run,
    exclude_users: normalizeList(formModel.exclude_users),
    exclude_hosts: normalizeList(formModel.exclude_hosts),
    exclude_dbs: normalizeList(formModel.exclude_dbs),
    exclude_fingerprints: normalizeList(formModel.exclude_fingerprints)
  }

  if (editingRuleId.value) {
    await store.updateRule(editingRuleId.value, payload)
    ElMessage.success('规则更新成功')
  } else {
    await store.createRule(payload)
    ElMessage.success('规则创建成功')
  }
  dialogVisible.value = false
}

async function toggleRule(row: SqlThrottleRule) {
  if (row.enabled) {
    await store.disableRule(row.id)
    ElMessage.success('规则已停用')
  } else {
    await store.enableRule(row.id)
    ElMessage.success('规则已启用')
  }
}

async function runNow(id: number) {
  const result = await store.runRuleNow(id)
  ElMessage.success(`已执行，运行ID: ${result?.id || '-'}`)
  await store.fetchRuleList()
}

async function removeRule(id: number) {
  await ElMessageBox.confirm('删除后规则将停用，历史运行记录会保留。是否继续？', '确认删除', {
    type: 'warning'
  })
  await store.removeRule(id)
  ElMessage.success('规则已删除')
}

function goRuns(rule: SqlThrottleRule) {
  router.push({
    path: '/sql-throttle/runs',
    query: { rule_name: rule.rule_name }
  })
}
</script>

<style scoped>
.page-shell {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.page-header h2 {
  margin: 0;
  color: #1e3a5f;
  font-size: 22px;
}

.page-header p {
  margin: 6px 0 0;
  color: #5f7084;
  font-size: 13px;
}

.filter-control {
  width: 220px;
}

.table-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}

.row-actions {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 0;
  white-space: nowrap;
}

.row-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.row-actions :deep(.el-button.is-link) {
  padding-left: 2px;
  padding-right: 2px;
}

.table-pagination {
  margin-top: 12px;
  justify-content: flex-end;
}

.full-width {
  width: 100%;
}
</style>
