<template>
  <AppLayout>
    <div class="page-shell" v-loading="store.loadingRunDetail">
      <div class="page-header">
        <div>
          <h2>SQL 限流运行详情</h2>
          <p>运行ID：{{ runId }}</p>
        </div>
        <el-button @click="goBack">返回运行列表</el-button>
      </div>

      <el-row :gutter="12" class="summary-row">
        <el-col :span="6">
          <el-card shadow="never" class="metric-card">
            <div class="metric-label">执行状态</div>
            <div class="metric-value">{{ store.currentRun?.status || '-' }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="metric-card">
            <div class="metric-label">活跃会话</div>
            <div class="metric-value">{{ store.currentRun?.total_session_count ?? 0 }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="metric-card">
            <div class="metric-label">命中指纹</div>
            <div class="metric-value">{{ store.currentRun?.hit_fingerprint_count ?? 0 }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="never" class="metric-card">
            <div class="metric-label">Kill 成功</div>
            <div class="metric-value">{{ store.currentRun?.kill_success_count ?? 0 }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="detail-card">
        <template #header>
          <span>Kill 明细</span>
        </template>
        <el-table :data="store.currentRunKillLogs" stripe>
          <el-table-column prop="thread_id" label="线程ID" width="110" />
          <el-table-column prop="db_user" label="用户" min-width="110" />
          <el-table-column prop="db_name" label="DB" min-width="120" />
          <el-table-column prop="sample_sql_text" label="SQL语句" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.sample_sql_text || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="exec_time_seconds" label="执行时长(s)" width="120" />
          <el-table-column prop="kill_result" label="结果" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="killResultType(row.kill_result)">{{ row.kill_result }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="kill_error_message" label="错误信息" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.kill_error_message || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="killed_at" label="处置时间" min-width="150" />
        </el-table>
      </el-card>

      <el-card shadow="never" class="detail-card">
        <template #header>
          <span>采样快照</span>
        </template>
        <pre class="snapshot-content">{{ prettySnapshot }}</pre>
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useSqlThrottleStore } from '@/stores/sqlThrottle'

const route = useRoute()
const router = useRouter()
const store = useSqlThrottleStore()

const runId = Number(route.params.id)

const prettySnapshot = computed(() => {
  return JSON.stringify(store.currentRunSnapshot || {}, null, 2)
})

onMounted(async () => {
  if (!Number.isNaN(runId) && runId > 0) {
    await store.fetchRunDetail(runId)
  }
})

function goBack() {
  router.push('/sql-throttle/runs')
}

function killResultType(result: string) {
  if (result === 'success' || result === 'dry_run') {
    return 'success'
  }
  if (result === 'already_finished') {
    return 'warning'
  }
  return 'danger'
}
</script>

<style scoped>
.page-shell {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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

.summary-row {
  margin-top: 2px;
}

.metric-card {
  min-height: 90px;
}

.metric-label {
  color: #64748b;
  font-size: 13px;
}

.metric-value {
  margin-top: 10px;
  color: #1e293b;
  font-size: 22px;
  font-weight: 700;
}

.detail-card {
  min-height: 0;
}

.snapshot-content {
  margin: 0;
  max-height: 320px;
  overflow: auto;
  background: #0f172a;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
}
</style>
