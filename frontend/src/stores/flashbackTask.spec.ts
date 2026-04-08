import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const {
  getFlashbackTaskListMock,
  getFlashbackTaskMock,
  createFlashbackTaskMock
} = vi.hoisted(() => ({
  getFlashbackTaskListMock: vi.fn(),
  getFlashbackTaskMock: vi.fn(),
  createFlashbackTaskMock: vi.fn()
}))

vi.mock('@/api/flashbackTask', () => ({
  getFlashbackTaskList: getFlashbackTaskListMock,
  getFlashbackTask: getFlashbackTaskMock,
  createFlashbackTask: createFlashbackTaskMock,
  getFlashbackTaskArtifacts: vi.fn(),
  downloadFlashbackTaskArtifact: vi.fn(),
  getFlashbackTaskLogContent: vi.fn(),
  downloadFlashbackTaskLog: vi.fn()
}))

import { useFlashbackTaskStore } from './flashbackTask'

function buildTask(overrides: Record<string, unknown> = {}) {
  return {
    id: 11,
    db_connection_id: 1,
    connection_id: 1,
    connection_name: '测试连接',
    database_name: 'demo_db',
    table_name: 'orders',
    mode: 'repl',
    sql_type: 'delete',
    work_type: '2sql',
    status: 'queued',
    progress: 0,
    artifacts: [],
    created_at: '2026-04-08 08:00:00',
    updated_at: '2026-04-08 08:00:00',
    ...overrides
  }
}

describe('flashback task store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches flashback tasks with filters and pagination metadata', async () => {
    getFlashbackTaskListMock.mockResolvedValueOnce({
      success: true,
      data: {
        items: [buildTask({ id: 21, database_name: 'audit_db', table_name: 'events' })],
        pagination: {
          page: 2,
          per_page: 20,
          total: 42,
          total_pages: 3,
          has_prev: true,
          has_next: true,
          prev_num: 1,
          next_num: 3
        }
      }
    })

    const store = useFlashbackTaskStore()
    store.setFilters({
      database_name: 'audit',
      table_name: 'events',
      status: 'running',
      sql_type: 'insert',
      work_type: 'rollback'
    })
    store.page = 2
    store.perPage = 20

    await store.fetchList()

    expect(getFlashbackTaskListMock).toHaveBeenCalledWith({
      page: 2,
      per_page: 20,
      database_name: 'audit',
      table_name: 'events',
      status: 'running',
      sql_type: 'insert',
      work_type: 'rollback'
    })
    expect(store.list).toHaveLength(1)
    expect(store.list[0].database_name).toBe('audit_db')
    expect(store.total).toBe(42)
    expect(store.page).toBe(2)
    expect(store.perPage).toBe(20)
  })

  it('loads flashback task detail into currentTask', async () => {
    getFlashbackTaskMock.mockResolvedValueOnce({
      success: true,
      data: buildTask({
        id: 33,
        status: 'running',
        progress: 30,
        artifacts: [
          { id: 'result-sql', name: 'orders.sql', size: 10 }
        ]
      })
    })

    const store = useFlashbackTaskStore()
    const detail = await store.fetchDetail(33)

    expect(getFlashbackTaskMock).toHaveBeenCalledWith(33)
    expect(detail?.id).toBe(33)
    expect(store.currentTask?.id).toBe(33)
    expect(store.currentTask?.artifacts[0].name).toBe('orders.sql')
  })

  it('returns the created flashback task', async () => {
    getFlashbackTaskListMock.mockResolvedValue({
      success: true,
      data: {
        items: [],
        pagination: {
          page: 1,
          per_page: 10,
          total: 0,
          total_pages: 1,
          has_prev: false,
          has_next: false,
          prev_num: null,
          next_num: null
        }
      }
    })
    createFlashbackTaskMock.mockResolvedValueOnce({
      success: true,
      data: buildTask({
        id: 88,
        status: 'queued',
        database_name: 'demo_db',
        table_name: 'orders'
      })
    })

    const store = useFlashbackTaskStore()
    const created = await store.createTask({
      db_connection_id: 1,
      database_name: 'demo_db',
      table_name: 'orders',
      sql_type: 'delete',
      work_type: '2sql'
    })

    expect(createFlashbackTaskMock).toHaveBeenCalledWith({
      db_connection_id: 1,
      database_name: 'demo_db',
      table_name: 'orders',
      sql_type: 'delete',
      work_type: '2sql'
    })
    expect(created?.id).toBe(88)
    expect(store.currentTask?.id).toBe(88)
    expect(store.formLoading).toBe(false)
  })
})
