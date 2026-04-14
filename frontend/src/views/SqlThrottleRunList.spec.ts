import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'

const routeQueryState = vi.hoisted(() => ({
  value: {} as Record<string, string>
}))

const { getSqlThrottleRunListMock } = vi.hoisted(() => ({
  getSqlThrottleRunListMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: routeQueryState.value
  }),
  useRouter: () => ({
    push: vi.fn()
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
  getSqlThrottleRunList: getSqlThrottleRunListMock,
  getSqlThrottleRun: vi.fn(),
  getSqlThrottleRunKillLogs: vi.fn(),
  getSqlThrottleRunSnapshot: vi.fn()
}))

import SqlThrottleRunList from './SqlThrottleRunList.vue'

describe('SqlThrottleRunList', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(SqlThrottleRunList, {
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
    routeQueryState.value = {}
    getSqlThrottleRunListMock.mockResolvedValue({
      success: true,
      data: {
        items: [],
        total: 0,
        page: 1,
        per_page: 10
      }
    })
  })

  it('renders rule-name/hit filters and hides rule-id/run-id labels', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('规则名称')
    expect(wrapper.text()).toContain('是否命中')
    expect(wrapper.text()).not.toContain('规则ID')
    expect(wrapper.text()).not.toContain('运行ID')
  })

  it('hydrates run list filters from route query and sends them to API', async () => {
    routeQueryState.value = {
      rule_name: '订单限流',
      is_hit: '1'
    }
    mountView()
    await flushPromises()

    expect(getSqlThrottleRunListMock).toHaveBeenCalled()
    expect(getSqlThrottleRunListMock).toHaveBeenCalledWith(
      expect.objectContaining({
        rule_name: '订单限流',
        is_hit: true
      })
    )
  })
})
