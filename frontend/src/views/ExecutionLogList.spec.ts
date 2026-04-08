import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { ExecutionLog } from '@/types'

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
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    return mount(ExecutionLogList, {
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

    getExecutionLogListMock.mockResolvedValue({
      success: true,
      data: {
        items: [
          buildLog()
        ],
        total: 1,
        page: 1,
        per_page: 10
      }
    })

    getExecutionLogMock.mockResolvedValue({ success: true, data: buildLog() })
    getLogContentMock.mockResolvedValue({ success: true, data: { content: 'log line', has_file: true } })
    downloadExecutionLogMock.mockResolvedValue({ status: 200, data: new Blob(['log line']) })
  })

  it('renders unified log filters and typed task links', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(getExecutionLogListMock).toHaveBeenCalledWith({
      page: 1,
      per_page: 10,
      task_id: undefined,
      task_name: '',
      status: undefined,
      log_type: 'all'
    })
    expect(wrapper.text()).toContain('日志类型')
    expect(wrapper.text()).toContain('sales.orders 闪回任务')
    expect(wrapper.text()).toContain('数据闪回')

    const taskLink = wrapper.get('[data-detail-path="/flashback-tasks/22"]')
    expect(taskLink.text()).toContain('sales.orders 闪回任务')

    await taskLink.trigger('click')

    expect(pushMock).toHaveBeenCalledWith('/flashback-tasks/22')
  })
})
