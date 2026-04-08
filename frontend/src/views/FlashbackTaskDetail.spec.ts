import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { FlashbackTask } from '@/types'

const pushMock = vi.fn()

const {
  getFlashbackTaskMock,
  getFlashbackTaskLogContentMock,
  downloadFlashbackTaskArtifactMock,
  downloadFlashbackTaskLogMock
} = vi.hoisted(() => ({
  getFlashbackTaskMock: vi.fn(),
  getFlashbackTaskLogContentMock: vi.fn(),
  downloadFlashbackTaskArtifactMock: vi.fn(),
  downloadFlashbackTaskLogMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: {
      id: '11'
    }
  }),
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/flashbackTask', () => ({
  getFlashbackTaskList: vi.fn(),
  getFlashbackTask: getFlashbackTaskMock,
  createFlashbackTask: vi.fn(),
  getFlashbackTaskArtifacts: vi.fn(),
  getFlashbackTaskLogContent: getFlashbackTaskLogContentMock,
  downloadFlashbackTaskArtifact: downloadFlashbackTaskArtifactMock,
  downloadFlashbackTaskLog: downloadFlashbackTaskLogMock
}))

import FlashbackTaskDetail from './FlashbackTaskDetail.vue'

function buildTask(overrides: Partial<FlashbackTask> = {}): FlashbackTask {
  return {
    id: 11,
    db_connection_id: 1,
    connection_name: '订单库',
    database_name: 'sales',
    table_name: 'orders',
    mode: 'repl',
    sql_type: 'delete',
    work_type: '2sql',
    status: 'queued',
    progress: 20,
    artifacts: [
      { id: 'status', name: 'binlog_status.txt', size: 120 },
      { id: 'trx', name: 'biglong_trx.txt', size: 220 },
      { id: 'sql', name: 'orders.sql', size: 320 }
    ],
    created_at: '2026-04-08 10:00:00',
    updated_at: '2026-04-08 10:01:00',
    ...overrides
  }
}

describe('FlashbackTaskDetail', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    return mount(FlashbackTaskDetail, {
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
    vi.useFakeTimers()

    getFlashbackTaskMock.mockResolvedValue({
      success: true,
      data: buildTask()
    })
    getFlashbackTaskLogContentMock.mockResolvedValue({
      success: true,
      data: {
        content: 'flashback log content',
        has_file: true
      }
    })
    downloadFlashbackTaskArtifactMock.mockResolvedValue({
      status: 200,
      data: new Blob(['artifact'])
    })
    downloadFlashbackTaskLogMock.mockResolvedValue({
      status: 200,
      data: new Blob(['log'])
    })

    Object.defineProperty(window.URL, 'createObjectURL', {
      value: vi.fn(() => 'blob:mock-url'),
      writable: true
    })
    Object.defineProperty(window.URL, 'revokeObjectURL', {
      value: vi.fn(),
      writable: true
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllTimers()
  })

  it('renders the task summary, artifact downloads and log content', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(getFlashbackTaskMock).toHaveBeenCalledWith(11)
    expect(getFlashbackTaskLogContentMock).toHaveBeenCalledWith(11)
    expect(wrapper.text()).toContain('数据闪回任务详情')
    expect(wrapper.text()).toContain('orders')
    expect(wrapper.text()).toContain('flashback log content')
    expect(wrapper.findAll('[data-artifact-id]')).toHaveLength(3)
    expect(wrapper.text()).toContain('binlog_status.txt')
    expect(wrapper.text()).toContain('biglong_trx.txt')
    expect(wrapper.text()).toContain('orders.sql')

    await wrapper.get('[data-artifact-id="sql"]').trigger('click')
    await wrapper.get('button.download-log-btn').trigger('click')
    await flushPromises()

    expect(downloadFlashbackTaskArtifactMock).toHaveBeenCalledWith(11, 'sql')
    expect(downloadFlashbackTaskLogMock).toHaveBeenCalledWith(11)
  })

  it('starts polling while the task is queued or running', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(getFlashbackTaskMock).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()

    expect(getFlashbackTaskMock).toHaveBeenCalledTimes(2)

    wrapper.unmount()
  })
})
