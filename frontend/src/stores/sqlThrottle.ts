import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createSqlThrottleRule,
  deleteSqlThrottleRule,
  disableSqlThrottleRule,
  enableSqlThrottleRule,
  getSqlThrottleRuleList,
  getSqlThrottleRun,
  getSqlThrottleRunKillLogs,
  getSqlThrottleRunList,
  getSqlThrottleRunSnapshot,
  runOnceSqlThrottleRule,
  updateSqlThrottleRule
} from '@/api/sqlThrottle'
import type {
  SqlThrottleKillLog,
  SqlThrottleRule,
  SqlThrottleRun
} from '@/types'
import type { SqlThrottleRulePayload } from '@/api/sqlThrottle'

export const useSqlThrottleStore = defineStore('sqlThrottle', () => {
  const loadingRules = ref(false)
  const loadingRuns = ref(false)
  const loadingRunDetail = ref(false)

  const ruleList = ref<SqlThrottleRule[]>([])
  const ruleTotal = ref(0)
  const rulePage = ref(1)
  const rulePerPage = ref(10)

  const runList = ref<SqlThrottleRun[]>([])
  const runTotal = ref(0)
  const runPage = ref(1)
  const runPerPage = ref(10)

  const currentRun = ref<SqlThrottleRun | null>(null)
  const currentRunKillLogs = ref<SqlThrottleKillLog[]>([])
  const currentRunSnapshot = ref<Record<string, unknown>>({})

  const ruleFilters = ref({
    rule_name: '',
    enabled: undefined as boolean | undefined
  })

  const runFilters = ref({
    rule_name: '',
    is_hit: undefined as boolean | undefined,
    status: ''
  })

  async function fetchRuleList() {
    loadingRules.value = true
    try {
      const res = await getSqlThrottleRuleList({
        page: rulePage.value,
        per_page: rulePerPage.value,
        ...ruleFilters.value
      })
      if (res.data) {
        ruleList.value = res.data.items
        ruleTotal.value = res.data.total
        rulePage.value = res.data.page
        rulePerPage.value = res.data.per_page
      }
    } finally {
      loadingRules.value = false
    }
  }

  async function createRule(payload: SqlThrottleRulePayload) {
    const res = await createSqlThrottleRule(payload)
    await fetchRuleList()
    return res.data
  }

  async function updateRule(id: number, payload: Partial<SqlThrottleRulePayload>) {
    const res = await updateSqlThrottleRule(id, payload)
    await fetchRuleList()
    return res.data
  }

  async function enableRule(id: number) {
    await enableSqlThrottleRule(id)
    await fetchRuleList()
  }

  async function disableRule(id: number) {
    await disableSqlThrottleRule(id)
    await fetchRuleList()
  }

  async function removeRule(id: number) {
    await deleteSqlThrottleRule(id)
    await fetchRuleList()
  }

  async function runRuleNow(id: number) {
    const res = await runOnceSqlThrottleRule(id)
    return res.data
  }

  async function fetchRunList() {
    loadingRuns.value = true
    try {
      const res = await getSqlThrottleRunList({
        page: runPage.value,
        per_page: runPerPage.value,
        ...runFilters.value
      })
      if (res.data) {
        runList.value = res.data.items
        runTotal.value = res.data.total
        runPage.value = res.data.page
        runPerPage.value = res.data.per_page
      }
    } finally {
      loadingRuns.value = false
    }
  }

  async function fetchRunDetail(id: number) {
    loadingRunDetail.value = true
    try {
      const [runRes, killRes, snapshotRes] = await Promise.all([
        getSqlThrottleRun(id),
        getSqlThrottleRunKillLogs(id),
        getSqlThrottleRunSnapshot(id)
      ])
      currentRun.value = runRes.data || null
      currentRunKillLogs.value = killRes.data?.items || []
      currentRunSnapshot.value = snapshotRes.data?.snapshot || {}
    } finally {
      loadingRunDetail.value = false
    }
  }

  return {
    loadingRules,
    loadingRuns,
    loadingRunDetail,
    ruleList,
    ruleTotal,
    rulePage,
    rulePerPage,
    runList,
    runTotal,
    runPage,
    runPerPage,
    currentRun,
    currentRunKillLogs,
    currentRunSnapshot,
    ruleFilters,
    runFilters,
    fetchRuleList,
    createRule,
    updateRule,
    enableRule,
    disableRule,
    removeRule,
    runRuleNow,
    fetchRunList,
    fetchRunDetail
  }
})
