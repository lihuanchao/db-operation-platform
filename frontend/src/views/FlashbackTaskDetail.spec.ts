import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { FlashbackTask } from '@/types'

const pushMock = vi.fn()

const {
  authStoreState,
  getFlashbackTaskMock,
  getFlashbackTaskLogContentMock,
  downloadFlashbackTaskArtifactMock,
  downloadFlashbackTaskLogMock
} = vi.hoisted(() => ({
  authStoreState: {
    authorizedConnections: [
      {
        id: 1,
        connection_name: '订单库',
        host: '10.0.0.11',
        port: 3306
      }
    ],
    fetchAuthorizedConnections: vi.fn()
  },
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

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => authStoreState
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
    start_file: 'mysql-bin.000001',
    stop_file: 'mysql-bin.000002',
    start_datetime: '2026-04-08 10:00:00',
    stop_datetime: '2026-04-08 10:05:00',
    creator_employee_no: 'E0001',
    started_at: '2026-04-08 10:00:10',
    finished_at: '2026-04-08 10:04:10',
    masked_command: 'mysqldump -h 127.0.0.1 -user repl -password ****** --where=***',
    status: 'queued',
    progress: 20,
    artifacts: [
      { id: 'status', name: 'binlog_status.txt', size: 120 },
      { id: 'trx', name: 'biglong_trx.txt', size: 220 },
      { id: 'sql', name: 'orders.sql', size: 320 }
    ],
    created_at: '2026-04-08 10:00:00',
    updated_at: '2026-04-08 10:01:00',
    error_message: null,
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
    authStoreState.authorizedConnections = [
      {
        id: 1,
        connection_name: '订单库',
        host: '10.0.0.11',
        port: 3306
      }
    ]
    authStoreState.fetchAuthorizedConnections.mockResolvedValue(undefined)

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
    expect(wrapper.text()).toContain('10.0.0.11:3306')
    expect(wrapper.text()).toContain('2026-04-08 10:00:00')
    expect(wrapper.text()).toContain('2026-04-08 10:05:00')
    expect(wrapper.text()).toContain('mysql-bin.000001')
    expect(wrapper.text()).toContain('mysql-bin.000002')
    expect(wrapper.text()).toContain('E0001')
    expect(wrapper.text()).toContain('2026-04-08 10:00:10')
    expect(wrapper.text()).toContain('2026-04-08 10:04:10')
    expect(wrapper.text()).toContain('mysqldump -h 127.0.0.1')
    expect(wrapper.text()).toContain('-user ******')
    expect(wrapper.text()).toContain('-password ******')
    expect(wrapper.text()).not.toContain('-user repl')

    await wrapper.get('[data-artifact-id="sql"]').trigger('click')
    await wrapper.get('button.refresh-log-btn').trigger('click')
    await wrapper.get('button.download-log-btn').trigger('click')
    await flushPromises()

    expect(getFlashbackTaskLogContentMock).toHaveBeenCalledTimes(2)
    expect(downloadFlashbackTaskArtifactMock).toHaveBeenCalledWith(11, 'sql')
    expect(downloadFlashbackTaskLogMock).toHaveBeenCalledWith(11)
  })

  it('loads connections when the list is empty before resolving host and port', async () => {
    authStoreState.authorizedConnections = []
    authStoreState.fetchAuthorizedConnections.mockImplementationOnce(async () => {
      authStoreState.authorizedConnections = [
        {
          id: 1,
          connection_name: '订单库',
          host: '10.0.0.11',
          port: 3306
        }
      ]
    })
    getFlashbackTaskMock.mockResolvedValueOnce({
      success: true,
      data: buildTask()
    })

    const wrapper = mountView()
    await flushPromises()

    expect(authStoreState.fetchAuthorizedConnections).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('10.0.0.11:3306')
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

  it('shows the task error message when present', async () => {
    getFlashbackTaskMock.mockResolvedValueOnce({
      success: true,
      data: buildTask({
        status: 'failed',
        error_message: 'replication halted'
      })
    })

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('replication halted')
  })
})
