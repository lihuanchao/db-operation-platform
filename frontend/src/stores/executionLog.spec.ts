import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const {
  getExecutionLogListMock,
  getExecutionLogMock,
  downloadExecutionLogMock
} = vi.hoisted(() => ({
  getExecutionLogListMock: vi.fn(),
  getExecutionLogMock: vi.fn(),
  downloadExecutionLogMock: vi.fn()
}))

vi.mock('@/api/executionLog', () => ({
  getExecutionLogList: getExecutionLogListMock,
  getExecutionLog: getExecutionLogMock,
  downloadExecutionLog: downloadExecutionLogMock,
  getLogContent: vi.fn()
}))

import { useExecutionLogStore } from './executionLog'

function buildLog(overrides: Record<string, unknown> = {}) {
  return {
    id: 11,
    task_id: 101,
    task_name: '归档任务-101',
    start_time: '2026-04-08 09:00:00',
    end_time: '2026-04-08 09:03:00',
    status: 1,
    log_file: '/tmp/archive-11.log',
    error_message: null,
    created_at: '2026-04-08 09:00:00',
    log_type: 'archive',
    detail_path: '/archive-tasks/101',
    ...overrides
  }
}

describe('execution log store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('passes unified filters to the execution log list API', async () => {
    getExecutionLogListMock.mockResolvedValueOnce({
      success: true,
      data: {
        items: [
          buildLog({
            id: 22,
            task_name: 'demo_db.orders',
            log_type: 'flashback',
            detail_path: '/flashback-tasks/22'
          })
        ],
        total: 1,
        page: 1,
        per_page: 10
      }
    })

    const store = useExecutionLogStore()
    store.setFilters({
      task_name: 'demo',
      status: 2,
      log_type: 'all'
    })

    await store.fetchList()

    expect(getExecutionLogListMock).toHaveBeenCalledWith({
      page: 1,
      per_page: 10,
      task_id: undefined,
      task_name: 'demo',
      status: 2,
      log_type: 'all'
    })
    expect(store.list).toHaveLength(1)
    expect(store.list[0].log_type).toBe('flashback')
    expect(store.list[0].detail_path).toBe('/flashback-tasks/22')
  })

  it('downloads a typed execution log', async () => {
    downloadExecutionLogMock.mockResolvedValueOnce({
      status: 200,
      data: new Blob(['log-content'])
    })

    const store = useExecutionLogStore()
    await store.downloadLog('flashback', 11)

    expect(downloadExecutionLogMock).toHaveBeenCalledWith('flashback', 11)
  })

  it('supports the existing detail fetch contract', async () => {
    getExecutionLogMock.mockResolvedValueOnce({
      success: true,
      data: buildLog({ id: 44 })
    })

    const store = useExecutionLogStore()
    const detail = await store.fetchDetail(44)

    expect(getExecutionLogMock).toHaveBeenCalledWith(44)
    expect(detail?.id).toBe(44)
  })
})
