// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { OptimizationTask } from '@/types'

const pushMock = vi.fn()

const { getOptimizationTaskDetailMock } = vi.hoisted(() => ({
  getOptimizationTaskDetailMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { id: '11' }
  }),
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/optimizationTask', () => ({
  getOptimizationTaskList: vi.fn(),
  getOptimizationTaskDetail: getOptimizationTaskDetailMock,
  createSqlOptimizationTask: vi.fn(),
  createMyBatisOptimizationTask: vi.fn()
}))

import OptimizationTaskDetail from './OptimizationTaskDetail.vue'

function buildTask(overrides: Partial<OptimizationTask> = {}): OptimizationTask {
  const lines = Array.from({ length: 90 }, (_, idx) => `SELECT some_really_long_column_name_${idx} FROM order_table_${idx}`)
  const sqlContent = lines.join('\n')
  return {
    id: 11,
    task_type: 'sql',
    object_preview: sqlContent,
    object_content: sqlContent,
    optimized_content: `${sqlContent}\nAND status = 'DONE'`,
    db_connection_id: 1,
    database_name: 'orders',
    database_host: '10.0.0.8',
    status: 'completed',
    progress: 100,
    created_at: '2026-04-09 09:00:00',
    updated_at: '2026-04-09 09:02:00',
    ...overrides
  }
}

describe('OptimizationTaskDetail', () => {
  let rafSpy: ReturnType<typeof vi.spyOn>

  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(OptimizationTaskDetail, {
      global: {
        plugins: [pinia, ElementPlus],
        stubs: {
          AppLayout: {
            template: '<div class="layout-stub"><slot /></div>'
          },
          CopyButton: {
            template: '<button class="copy-button-stub" />'
          }
        }
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
    rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback: FrameRequestCallback) => {
      callback(0)
      return 1
    })
    getOptimizationTaskDetailMock.mockResolvedValue({
      success: true,
      data: buildTask()
    })
  })

  afterEach(() => {
    rafSpy.mockRestore()
  })

  it('syncs vertical scrolling only between original and optimized panes', async () => {
    const wrapper = mountView()
    await flushPromises()

    const panes = wrapper.findAll('.code-pane')
    expect(panes.length).toBe(2)

    const originalPane = panes[0].element as HTMLElement
    const optimizedPane = panes[1].element as HTMLElement

    Object.defineProperty(originalPane, 'scrollHeight', { configurable: true, value: 2400 })
    Object.defineProperty(originalPane, 'clientHeight', { configurable: true, value: 380 })
    Object.defineProperty(originalPane, 'scrollWidth', { configurable: true, value: 1200 })
    Object.defineProperty(originalPane, 'clientWidth', { configurable: true, value: 600 })
    Object.defineProperty(optimizedPane, 'scrollHeight', { configurable: true, value: 2500 })
    Object.defineProperty(optimizedPane, 'clientHeight', { configurable: true, value: 380 })
    Object.defineProperty(optimizedPane, 'scrollWidth', { configurable: true, value: 1400 })
    Object.defineProperty(optimizedPane, 'clientWidth', { configurable: true, value: 600 })

    originalPane.scrollTop = 180
    originalPane.scrollLeft = 90
    await panes[0].trigger('scroll')

    expect(optimizedPane.scrollTop).toBe(180)
    expect(optimizedPane.scrollLeft).toBe(0)
  })

  it('adds spacer to shorter pane so both sides keep vertical scroll range', async () => {
    const wrapper = mountView()
    await flushPromises()

    const panes = wrapper.findAll('.code-pane')
    expect(panes.length).toBe(2)

    const originalPane = panes[0].element as HTMLElement
    const optimizedPane = panes[1].element as HTMLElement
    Object.defineProperty(originalPane, 'scrollHeight', { configurable: true, value: 2200 })
    Object.defineProperty(optimizedPane, 'scrollHeight', { configurable: true, value: 1400 })

    window.dispatchEvent(new Event('resize'))
    await flushPromises()

    const spacers = wrapper.findAll('.pane-spacer')
    expect(spacers.length).toBe(2)
    expect(spacers[0].attributes('style')).toContain('height: 0px')
    expect(spacers[1].attributes('style')).toContain('height: 800px')
  })
})
