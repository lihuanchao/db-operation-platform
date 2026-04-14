<template>
  <AppLayout>
    <div class="page-shell">
      <div class="page-header">
        <div>
          <h2>SQL 限流运行记录</h2>
          <p>查看每一轮采样分析结果、命中情况与处置统计。</p>
        </div>
      </div>

      <el-card shadow="never" class="filter-card">
        <el-form :model="filters" inline>
          <el-form-item label="规则名称">
            <el-input v-model="filters.rule_name" clearable placeholder="请输入规则名称" class="filter-control" />
          </el-form-item>
          <el-form-item label="是否命中">
            <el-select v-model="filters.is_hit" clearable placeholder="全部" class="filter-control">
              <el-option label="已命中" value="1" />
              <el-option label="未命中" value="0" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="filters.status" clearable placeholder="全部状态" class="filter-control">
              <el-option label="completed" value="completed" />
              <el-option label="failed" value="failed" />
              <el-option label="skipped" value="skipped" />
              <el-option label="running" value="running" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="table-card">
        <el-table :data="store.runList" v-loading="store.loadingRuns" stripe>
          <el-table-column prop="rule_name" label="规则名称" min-width="180" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sample_started_at" label="开始时间" min-width="150" />
          <el-table-column prop="sample_finished_at" label="结束时间" min-width="150">
            <template #default="{ row }">
              {{ row.sample_finished_at || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="候选/命中" min-width="120">
            <template #default="{ row }">
              {{ row.candidate_fingerprint_count }}/{{ row.hit_fingerprint_count }}
            </template>
          </el-table-column>
          <el-table-column label="Kill 尝试/成功" min-width="140">
            <template #default="{ row }">
              {{ row.kill_attempt_count }}/{{ row.kill_success_count }}
            </template>
          </el-table-column>
          <el-table-column label="演练" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.dry_run ? 'warning' : 'success'">{{ row.dry_run ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="error_message" label="错误信息" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.error_message || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="goDetail(row.id)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="store.runPage"
          v-model:page-size="store.runPerPage"
          :total="store.runTotal"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          class="table-pagination"
          @current-change="store.fetchRunList"
          @size-change="handleRunSizeChange"
        />
      </el-card>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { useSqlThrottleStore } from '@/stores/sqlThrottle'

const store = useSqlThrottleStore()
const route = useRoute()
const router = useRouter()

const filters = reactive({
  rule_name: '',
  is_hit: '' as '' | '0' | '1',
  status: ''
})

function parseBoolQuery(raw: unknown): boolean | undefined {
  if (raw === true || raw === '1' || raw === 'true') {
    return true
  }
  if (raw === false || raw === '0' || raw === 'false') {
    return false
  }
  return undefined
}

onMounted(async () => {
  const routeRuleName = String(route.query.rule_name || '').trim()
  if (routeRuleName) {
    filters.rule_name = routeRuleName
    store.runFilters.rule_name = routeRuleName
  }

  const routeIsHit = parseBoolQuery(route.query.is_hit)
  if (routeIsHit !== undefined) {
    filters.is_hit = routeIsHit ? '1' : '0'
    store.runFilters.is_hit = routeIsHit
  }
  await store.fetchRunList()
})

function statusType(status: string) {
  if (status === 'completed') {
    return 'success'
  }
  if (status === 'running' || status === 'queued') {
    return 'warning'
  }
  if (status === 'skipped') {
    return 'info'
  }
  return 'danger'
}

function handleSearch() {
  store.runFilters.rule_name = filters.rule_name.trim()
  store.runFilters.is_hit = filters.is_hit === '' ? undefined : filters.is_hit === '1'
  store.runFilters.status = filters.status
  store.runPage = 1
  store.fetchRunList()
}

function handleReset() {
  filters.rule_name = ''
  filters.is_hit = ''
  filters.status = ''
  store.runFilters.rule_name = ''
  store.runFilters.is_hit = undefined
  store.runFilters.status = ''
  store.runPage = 1
  store.fetchRunList()
}

function handleRunSizeChange() {
  store.runPage = 1
  store.fetchRunList()
}

function goDetail(id: number) {
  router.push(`/sql-throttle/runs/${id}`)
}
</script>

<style scoped>
.page-shell {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
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
  width: 180px;
}

.table-card {
  flex: 1;
  min-height: 0;
}

.table-pagination {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
