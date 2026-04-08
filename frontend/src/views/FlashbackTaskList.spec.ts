import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { FlashbackTask } from '@/types'

const pushMock = vi.fn()

const { getFlashbackTaskListMock } = vi.hoisted(() => ({
  getFlashbackTaskListMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/flashbackTask', () => ({
  getFlashbackTaskList: getFlashbackTaskListMock,
  getFlashbackTask: vi.fn(),
  createFlashbackTask: vi.fn(),
  getFlashbackTaskArtifacts: vi.fn(),
  getFlashbackTaskLogContent: vi.fn(),
  downloadFlashbackTaskArtifact: vi.fn(),
  downloadFlashbackTaskLog: vi.fn()
}))

import FlashbackTaskList from './FlashbackTaskList.vue'

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
    progress: 0,
    artifacts: [],
    created_at: '2026-04-08 10:00:00',
    updated_at: '2026-04-08 10:00:00',
    ...overrides
  }
}

function buildListResponse(items: FlashbackTask[]) {
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

describe('FlashbackTaskList', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    return mount(FlashbackTaskList, {
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
    getFlashbackTaskListMock.mockResolvedValue(
      buildListResponse([
        buildTask({ id: 11, database_name: 'sales', table_name: 'orders', status: 'queued' }),
        buildTask({
          id: 12,
          database_name: 'crm',
          table_name: 'customers',
          sql_type: 'insert',
          work_type: 'rollback',
          status: 'running'
        })
      ])
    )
  })

  it('renders flashback tasks and navigates to create/detail pages', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(getFlashbackTaskListMock).toHaveBeenCalledWith({
      page: 1,
      per_page: 10,
      database_name: '',
      table_name: '',
      status: '',
      sql_type: '',
      work_type: ''
    })

    expect(wrapper.text()).toContain('数据闪回任务')
    expect(wrapper.text()).toContain('订单库')
    expect(wrapper.text()).toContain('sales.orders')
    expect(wrapper.text()).toContain('delete')
    expect(wrapper.text()).toContain('2sql')

    await wrapper.get('button.create-task-btn').trigger('click')
    await wrapper.get('[data-task-id="11"]').trigger('click')

    expect(pushMock).toHaveBeenNthCalledWith(1, '/flashback-tasks/create')
    expect(pushMock).toHaveBeenNthCalledWith(2, '/flashback-tasks/11')
  }, 15000)

  it('applies filters and requests the list again', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('input[placeholder="数据库名"]').setValue('sales')
    await wrapper.get('input[placeholder="表名"]').setValue('orders')
    await wrapper.get('button.search-btn').trigger('click')
    await flushPromises()

    expect(getFlashbackTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 10,
      database_name: 'sales',
      table_name: 'orders',
      status: '',
      sql_type: '',
      work_type: ''
    })

    await wrapper.get('button.reset-btn').trigger('click')
    await flushPromises()

    expect(getFlashbackTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 10,
      database_name: '',
      table_name: '',
      status: '',
      sql_type: '',
      work_type: ''
    })
  })
})
