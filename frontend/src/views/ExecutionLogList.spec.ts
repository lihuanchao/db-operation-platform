import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { ExecutionLog } from '@/types'
import { useExecutionLogStore } from '@/stores/executionLog'

const pushMock = vi.fn()

const {
  getExecutionLogListMock,
  getExecutionLogMock,
  getLogContentMock,
  downloadExecutionLogMock
} = vi.hoisted(() => ({
  getExecutionLogListMock: vi.fn(),
  getExecutionLogMock: vi.fn(),
  getLogContentMock: vi.fn(),
  downloadExecutionLogMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/executionLog', () => ({
  getExecutionLogList: getExecutionLogListMock,
  getExecutionLog: getExecutionLogMock,
  getLogContent: getLogContentMock,
  downloadExecutionLog: downloadExecutionLogMock
}))

import ExecutionLogList from './ExecutionLogList.vue'

function buildLog(overrides: Partial<ExecutionLog> = {}): ExecutionLog {
  return {
    id: 22,
    task_id: 202,
    task_name: 'sales.orders 闪回任务',
    start_time: '2026-04-08 10:00:00',
    end_time: '2026-04-08 10:04:00',
    status: 1,
    log_file: '/tmp/flashback-22.log',
    error_message: null,
    created_at: '2026-04-08 10:00:00',
    log_type: 'flashback',
    detail_path: '/flashback-tasks/22',
    ...overrides
  }
}

describe('ExecutionLogList', () => {
  function mountView(options: {
    setupStore?: (store: ReturnType<typeof useExecutionLogStore>) => void
  } = {}) {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useExecutionLogStore()
    options.setupStore?.(store)

    const wrapper = mount(ExecutionLogList, {
      global: {
        plugins: [pinia, ElementPlus],
        stubs: {
          AppLayout: {
            template: '<div class="layout-stub"><slot /></div>'
          }
        }
      }
    })

    return {
      wrapper,
      store
    }
  }

  function buildListResponse(items: ExecutionLog[]) {
    return {
      success: true,
      data: {
        items,
        total: items.length,
        page: 1,
        per_page: 10
      }
    }
  }

  function findButtonByText(wrapper: ReturnType<typeof mount>, text: string) {
    const button = wrapper.findAll('button').find((item) => item.text().includes(text))
    expect(button, `button containing ${text}`).toBeDefined()
    return button!
  }

  beforeEach(() => {
    vi.clearAllMocks()

    getExecutionLogListMock.mockResolvedValue(buildListResponse([buildLog()]))

    getExecutionLogMock.mockResolvedValue({ success: true, data: buildLog() })
    getLogContentMock.mockResolvedValue({ success: true, data: { content: 'log line', has_file: true } })
    downloadExecutionLogMock.mockResolvedValue({ status: 200, data: new Blob(['log line']) })
  })

  it('clears stale task_id filters on mount and reset for unified log queries', async () => {
    const { wrapper, store } = mountView({
      setupStore(currentStore) {
        currentStore.setFilters({
          task_id: 999,
          task_name: 'legacy',
          status: 2,
          log_type: 'archive'
        })
      }
    })

    await flushPromises()

    expect(getExecutionLogListMock).toHaveBeenCalledWith({
      page: 1,
      per_page: 10,
      task_id: undefined,
      task_name: '',
      status: undefined,
      log_type: 'all'
    })

    store.setFilters({
      task_id: 123,
      task_name: 'dirty again',
      status: 0,
      log_type: 'flashback'
    })

    await findButtonByText(wrapper, '重置').trigger('click')
    await flushPromises()

    expect(getExecutionLogListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 10,
      task_id: undefined,
      task_name: '',
      status: undefined,
      log_type: 'all'
    })
  }, 15000)

  it('shows download only for flashback rows without log_file and hides archive placeholders', async () => {
    getExecutionLogListMock.mockResolvedValueOnce(buildListResponse([
      buildLog({
        id: 22,
        task_name: 'sales.orders 闪回任务',
        log_type: 'flashback',
        log_file: null,
        detail_path: '/flashback-tasks/22'
      }),
      buildLog({
        id: 101,
        task_id: 101,
        task_name: '订单归档任务',
        log_type: 'archive',
        log_file: null,
        detail_path: '/archive-tasks/101'
      })
    ]))

    const { wrapper, store } = mountView()
    const downloadSpy = vi.spyOn(store, 'downloadLog').mockResolvedValue(null)
    await flushPromises()

    expect(wrapper.text()).toContain('日志类型')
    expect(wrapper.text()).toContain('数据闪回')
    expect(wrapper.text()).toContain('订单归档任务')

    await wrapper.get('[data-detail-path="/flashback-tasks/22"]').trigger('click')
    await wrapper.get('[data-detail-path="/archive-tasks/101"]').trigger('click')

    expect(wrapper.find('[data-download-key="flashback-22"]').exists()).toBe(true)
    expect(wrapper.find('[data-download-key="archive-101"]').exists()).toBe(false)

    await wrapper.get('[data-download-key="flashback-22"]').trigger('click')

    expect(pushMock).toHaveBeenNthCalledWith(1, '/flashback-tasks/22')
    expect(pushMock).toHaveBeenNthCalledWith(2, '/archive-tasks/101')
    expect(downloadSpy).toHaveBeenCalledWith('flashback', 22)
  })

  it('keeps the current log type when refreshed rows share the same id', async () => {
    getExecutionLogListMock
      .mockResolvedValueOnce(buildListResponse([
        buildLog({
          id: 7,
          task_id: 7,
          task_name: '订单归档任务',
          log_type: 'archive',
          detail_path: '/archive-tasks/7'
        })
      ]))
      .mockResolvedValueOnce(buildListResponse([
        buildLog({
          id: 7,
          task_id: 7,
          task_name: 'sales.orders 闪回任务',
          log_type: 'flashback',
          detail_path: '/flashback-tasks/7'
        }),
        buildLog({
          id: 7,
          task_id: 7,
          task_name: '订单归档任务',
          log_type: 'archive',
          detail_path: '/archive-tasks/7'
        })
      ]))
      .mockResolvedValueOnce(buildListResponse([
        buildLog({
          id: 7,
          task_id: 7,
          task_name: 'sales.orders 闪回任务',
          log_type: 'flashback',
          detail_path: '/flashback-tasks/7'
        }),
        buildLog({
          id: 7,
          task_id: 7,
          task_name: '订单归档任务',
          log_type: 'archive',
          detail_path: '/archive-tasks/7'
        })
      ]))

    const { wrapper } = mountView()
    await flushPromises()

    await findButtonByText(wrapper, '查看日志').trigger('click')
    await flushPromises()
    await findButtonByText(wrapper, '刷新日志').trigger('click')
    await flushPromises()

    expect(getLogContentMock).toHaveBeenNthCalledWith(1, 'archive', 7)
    expect(getLogContentMock).toHaveBeenNthCalledWith(2, 'archive', 7)
  })
})
