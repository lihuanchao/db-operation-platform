import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { SlowSQL } from '@/types'

const pushMock = vi.fn()

const {
  getSlowSQLDetailMock,
  optimizeSlowSQLMock
} = vi.hoisted(() => ({
  getSlowSQLDetailMock: vi.fn(),
  optimizeSlowSQLMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: {
      checksum: 'abc123'
    }
  }),
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/slowSql', () => ({
  getSlowSQLList: vi.fn(),
  getSlowSQLDetail: getSlowSQLDetailMock,
  optimizeSlowSQL: optimizeSlowSQLMock,
  batchOptimizeSlowSQLs: vi.fn(),
  downloadSlowSQL: vi.fn(),
  batchDownloadSlowSQLs: vi.fn()
}))

import SlowSQLDetail from './SlowSQLDetail.vue'

function buildSlowSQL(overrides: Partial<SlowSQL> = {}): SlowSQL {
  return {
    checksum: 'abc123',
    host: '10.0.0.10',
    database_name: 'orders',
    user_max: 'app_user',
    sample: 'SELECT * FROM orders WHERE created_at > NOW() - INTERVAL 7 DAY',
    last_seen: '2026-04-10 10:00:00',
    execution_count: 12,
    avg_time: 1.23,
    max_time: 2.31,
    min_time: 0.45,
    total_time: 14.76,
    optimized_suggestion: '',
    is_optimized: 0,
    ...overrides
  }
}

describe('SlowSQLDetail', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    return mount(SlowSQLDetail, {
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
    getSlowSQLDetailMock.mockResolvedValue({
      success: true,
      data: buildSlowSQL({
        is_optimized: 1,
        optimized_suggestion: '### SQL优化报告',
        optimized_content: 'SELECT id, created_at FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)',
        index_recommendation: 'CREATE INDEX idx_orders_created_at ON orders(created_at);',
        matched_rules: 'rule01,rule04'
      } as Partial<SlowSQL> as SlowSQL)
    })
    optimizeSlowSQLMock.mockResolvedValue({
      success: true,
      data: {
        suggestion: '### SQL优化报告',
        optimized_content: 'SELECT id FROM orders',
        index_recommendation: '无需新增索引',
        matched_rules: 'rule01'
      }
    })
  })

  it('renders sql writing optimization, index recommendation and hit-rules sections', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(getSlowSQLDetailMock).toHaveBeenCalledWith('abc123')
    expect(wrapper.text()).toContain('SQL 写法优化')
    expect(wrapper.text()).toContain('索引推荐')
    expect(wrapper.text()).toContain('命中规则')
    expect(wrapper.text()).toContain('原始 SQL')
    expect(wrapper.text()).toContain('优化后 SQL')
    expect(wrapper.text()).toContain('rule01')
    expect(wrapper.text()).toContain('rule04')
    expect(wrapper.text()).not.toContain('SQL语句')
    expect(wrapper.text()).not.toContain('优化建议')
  })
})
