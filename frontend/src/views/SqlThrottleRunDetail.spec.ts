import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'

const pushMock = vi.fn()

const {
  getSqlThrottleRunMock,
  getSqlThrottleRunKillLogsMock,
  getSqlThrottleRunSnapshotMock
} = vi.hoisted(() => ({
  getSqlThrottleRunMock: vi.fn(),
  getSqlThrottleRunKillLogsMock: vi.fn(),
  getSqlThrottleRunSnapshotMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: {
      id: '33'
    }
  }),
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/sqlThrottle', () => ({
  getSqlThrottleRuleList: vi.fn(),
  runOnceSqlThrottleRule: vi.fn(),
  createSqlThrottleRule: vi.fn(),
  updateSqlThrottleRule: vi.fn(),
  enableSqlThrottleRule: vi.fn(),
  disableSqlThrottleRule: vi.fn(),
  deleteSqlThrottleRule: vi.fn(),
  getSqlThrottleRunList: vi.fn(),
  getSqlThrottleRun: getSqlThrottleRunMock,
  getSqlThrottleRunKillLogs: getSqlThrottleRunKillLogsMock,
  getSqlThrottleRunSnapshot: getSqlThrottleRunSnapshotMock
}))

import SqlThrottleRunDetail from './SqlThrottleRunDetail.vue'

describe('SqlThrottleRunDetail', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(SqlThrottleRunDetail, {
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
    getSqlThrottleRunMock.mockResolvedValue({
      success: true,
      data: {
        id: 33,
        rule_id: 1,
        rule_name: '订单限流',
        status: 'completed',
        sample_started_at: '2026-04-14 10:00:00',
        sample_finished_at: '2026-04-14 10:00:05',
        total_session_count: 20,
        candidate_fingerprint_count: 2,
        hit_fingerprint_count: 1,
        kill_attempt_count: 2,
        kill_success_count: 0,
        dry_run: true,
        error_message: null
      }
    })
    getSqlThrottleRunKillLogsMock.mockResolvedValue({
      success: true,
      data: {
        items: [
          {
            id: 901,
            run_id: 33,
            rule_id: 1,
            thread_id: 12345,
            db_user: 'app_user',
            db_host: '10.0.0.1:3306',
            db_name: 'order_db',
            fingerprint: 'SELECT * FROM orders WHERE user_id = ?',
            sample_sql_text: 'select * from orders where user_id = 1',
            exec_time_seconds: 16,
            kill_command: 'KILL QUERY',
            kill_result: 'dry_run',
            kill_error_message: null,
            killed_at: '2026-04-14 10:00:05',
            created_at: '2026-04-14 10:00:05'
          }
        ]
      }
    })
    getSqlThrottleRunSnapshotMock.mockResolvedValue({
      success: true,
      data: {
        snapshot: {
          collector_mode: 'information_schema',
          hit_fingerprints: [{ fingerprint: 'SELECT * FROM orders WHERE user_id = ?' }]
        }
      }
    })
  })

  it('renders run detail and supports back navigation', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(getSqlThrottleRunMock).toHaveBeenCalledWith(33)
    expect(getSqlThrottleRunKillLogsMock).toHaveBeenCalledWith(33)
    expect(getSqlThrottleRunSnapshotMock).toHaveBeenCalledWith(33)

    expect(wrapper.text()).toContain('SQL 限流运行详情')
    expect(wrapper.text()).toContain('运行ID：33')
    expect(wrapper.text()).toContain('12345')
    expect(wrapper.text()).toContain('SQL语句')
    expect(wrapper.text()).toContain('select * from orders where user_id = 1')
    expect(wrapper.text()).not.toContain('Kill 明细ID线程ID')
    expect(wrapper.text()).toContain('dry_run')
    expect(wrapper.text()).toContain('collector_mode')

    const backButton = wrapper.findAll('button').find((button) => button.text().includes('返回运行列表'))
    expect(backButton, 'back button').toBeDefined()
    await backButton!.trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/sql-throttle/runs')
  })
})
