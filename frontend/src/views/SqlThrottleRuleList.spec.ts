import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'

const pushMock = vi.fn()

const {
  getConnectionListMock,
  getSqlThrottleRuleListMock,
  runOnceSqlThrottleRuleMock,
  createSqlThrottleRuleMock,
  updateSqlThrottleRuleMock,
  enableSqlThrottleRuleMock,
  disableSqlThrottleRuleMock,
  deleteSqlThrottleRuleMock
} = vi.hoisted(() => ({
  getConnectionListMock: vi.fn(),
  getSqlThrottleRuleListMock: vi.fn(),
  runOnceSqlThrottleRuleMock: vi.fn(),
  createSqlThrottleRuleMock: vi.fn(),
  updateSqlThrottleRuleMock: vi.fn(),
  enableSqlThrottleRuleMock: vi.fn(),
  disableSqlThrottleRuleMock: vi.fn(),
  deleteSqlThrottleRuleMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/dbConnection', () => ({
  getConnectionList: getConnectionListMock
}))

vi.mock('@/api/sqlThrottle', () => ({
  getSqlThrottleRuleList: getSqlThrottleRuleListMock,
  runOnceSqlThrottleRule: runOnceSqlThrottleRuleMock,
  createSqlThrottleRule: createSqlThrottleRuleMock,
  updateSqlThrottleRule: updateSqlThrottleRuleMock,
  enableSqlThrottleRule: enableSqlThrottleRuleMock,
  disableSqlThrottleRule: disableSqlThrottleRuleMock,
  deleteSqlThrottleRule: deleteSqlThrottleRuleMock,
  getSqlThrottleRunList: vi.fn(),
  getSqlThrottleRun: vi.fn(),
  getSqlThrottleRunKillLogs: vi.fn(),
  getSqlThrottleRunSnapshot: vi.fn()
}))

import SqlThrottleRuleList from './SqlThrottleRuleList.vue'

describe('SqlThrottleRuleList', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(SqlThrottleRuleList, {
      global: {
        plugins: [pinia, ElementPlus],
        stubs: {
          AppLayout: {
            template: '<div class="layout-stub"><slot /></div>'
          }
        }
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
    getConnectionListMock.mockResolvedValue({
      success: true,
      data: {
        items: [
          {
            id: 1,
            connection_name: '测试连接',
            host: '127.0.0.1',
            port: 3306,
            username: 'root',
            is_enabled: true
          }
        ]
      }
    })
    getSqlThrottleRuleListMock.mockResolvedValue({
      success: true,
      data: {
        items: [
          {
            id: 1,
            rule_name: '订单限流',
            db_connection_id: 1,
            connection_name: '测试连接',
            mysql_version: '8.0.36',
            enabled: true,
            slow_sql_seconds: 10,
            fingerprint_concurrency_threshold: 20,
            poll_interval_seconds: 15,
            max_kill_per_round: 10,
            min_rows_examined: null,
            target_db_pattern: null,
            target_user_pattern: null,
            exclude_users: ['replication'],
            exclude_hosts: [],
            exclude_dbs: [],
            exclude_fingerprints: [],
            dry_run: true,
            kill_command: 'KILL QUERY',
            kill_scope: 'same_fingerprint_only',
            kill_order: 'dup_count_desc_exec_time_desc',
            consecutive_hit_times: 2,
            status: 'idle',
            last_run_at: null,
            last_hit_at: null,
            last_error_message: null,
            creator_user_id: 1,
            created_at: '2026-04-14 10:00:00',
            updated_at: '2026-04-14 10:00:00'
          }
        ],
        total: 1,
        page: 1,
        per_page: 10
      }
    })
    runOnceSqlThrottleRuleMock.mockResolvedValue({
      success: true,
      data: {
        id: 1001
      }
    })
    createSqlThrottleRuleMock.mockResolvedValue({ success: true, data: {} })
    updateSqlThrottleRuleMock.mockResolvedValue({ success: true, data: {} })
    enableSqlThrottleRuleMock.mockResolvedValue({ success: true, data: {} })
    disableSqlThrottleRuleMock.mockResolvedValue({ success: true, data: {} })
    deleteSqlThrottleRuleMock.mockResolvedValue({ success: true, data: { id: 1 } })
  })

  it('loads rule list and supports run-now action', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('SQL 限流规则')
    expect(wrapper.text()).toContain('订单限流')
    expect(getSqlThrottleRuleListMock).toHaveBeenCalled()

    await wrapper.get('[data-run-rule-id="1"]').trigger('click')
    await flushPromises()

    expect(runOnceSqlThrottleRuleMock).toHaveBeenCalledWith(1)
    expect(getSqlThrottleRuleListMock.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('shows validation message when submitting empty create form', async () => {
    const errorSpy = vi.spyOn(ElMessage, 'error').mockImplementation(() => undefined as never)
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[data-testid="create-rule-btn"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="save-rule-btn"]').trigger('click')
    await flushPromises()

    expect(errorSpy).toHaveBeenCalledWith('请先修正表单中的校验错误')
    errorSpy.mockRestore()
  })
})
