import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { SlowSQL } from '@/types'

const pushMock = vi.fn()

const {
  getSlowSQLListMock,
  optimizeSlowSQLMock,
  batchOptimizeSlowSQLsMock,
  downloadSlowSQLMock,
  batchDownloadSlowSQLsMock
} = vi.hoisted(() => ({
  getSlowSQLListMock: vi.fn(),
  optimizeSlowSQLMock: vi.fn(),
  batchOptimizeSlowSQLsMock: vi.fn(),
  downloadSlowSQLMock: vi.fn(),
  batchDownloadSlowSQLsMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/slowSql', () => ({
  getSlowSQLList: getSlowSQLListMock,
  getSlowSQLDetail: vi.fn(),
  optimizeSlowSQL: optimizeSlowSQLMock,
  batchOptimizeSlowSQLs: batchOptimizeSlowSQLsMock,
  downloadSlowSQL: downloadSlowSQLMock,
  batchDownloadSlowSQLs: batchDownloadSlowSQLsMock
}))

import SlowSQLList from './SlowSQLList.vue'

function buildSlowSQL(overrides: Partial<SlowSQL> = {}): SlowSQL {
  return {
    checksum: 'abc123',
    host: '10.0.0.10',
    database_name: 'orders',
    sample: 'SELECT * FROM orders WHERE id = 1',
    last_seen: '2026-04-10 10:00:00',
    execution_count: 12,
    avg_time: 1.23,
    is_optimized: 0,
    ...overrides
  }
}

function buildListResponse(items: SlowSQL[]) {
  return {
    success: true,
    data: {
      items,
      pagination: {
        page: 1,
        per_page: 10,
        total: items.length,
        total_pages: 1,
        has_prev: false,
        has_next: false,
        prev_num: null,
        next_num: null
      }
    }
  }
}

describe('SlowSQLList', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    return mount(SlowSQLList, {
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
    getSlowSQLListMock.mockResolvedValue(buildListResponse([buildSlowSQL()]))
    optimizeSlowSQLMock.mockResolvedValue({
      success: true,
      data: {
        suggestion: '建议添加索引'
      }
    })
  })

  it('disables optimize button and shows loading text while optimize request is pending', async () => {
    let resolveOptimize: ((value: unknown) => void) | undefined
    const pendingOptimize = new Promise((resolve) => {
      resolveOptimize = resolve
    })
    optimizeSlowSQLMock.mockReturnValueOnce(pendingOptimize)

    const wrapper = mountView()
    await flushPromises()

    const optimizeButton = wrapper.find('.btn-link--warning')
    expect(optimizeButton.exists()).toBe(true)
    expect(optimizeButton.text()).toContain('优化')

    await optimizeButton.trigger('click')
    await flushPromises()

    const optimizingButton = wrapper.find('.btn-link--warning')
    expect(optimizeSlowSQLMock).toHaveBeenCalledWith('abc123')
    expect(optimizingButton.attributes('disabled')).toBeDefined()
    expect(optimizingButton.text()).toContain('优化中...')

    resolveOptimize?.({
      success: true,
      data: {
        suggestion: '建议添加索引'
      }
    })
    await flushPromises()

    expect(wrapper.find('.btn-link--warning').exists()).toBe(false)
  })
})
