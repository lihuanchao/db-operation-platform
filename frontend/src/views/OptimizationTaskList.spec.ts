import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import type { OptimizationTask } from '@/types'

const pushMock = vi.fn()

const { getOptimizationTaskListMock } = vi.hoisted(() => ({
  getOptimizationTaskListMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/optimizationTask', () => ({
  getOptimizationTaskList: getOptimizationTaskListMock,
  getOptimizationTaskDetail: vi.fn(),
  createSqlOptimizationTask: vi.fn(),
  createMyBatisOptimizationTask: vi.fn()
}))

import OptimizationTaskList from './OptimizationTaskList.vue'

function buildTask(overrides: Partial<OptimizationTask> = {}): OptimizationTask {
  return {
    id: 101,
    task_type: 'sql',
    object_preview: 'SELECT * FROM orders WHERE id = 1',
    db_connection_id: 1,
    database_name: 'orders',
    database_host: '10.0.0.11',
    status: 'queued',
    progress: 0,
    created_at: '2026-04-03 10:00:00',
    updated_at: '2026-04-03 10:00:00',
    ...overrides
  }
}

function buildListResponse(items: OptimizationTask[], total = items.length, page = 1, perPage = 10) {
  return {
    success: true,
    data: {
      items,
      total,
      page,
      per_page: perPage
    }
  }
}

describe('OptimizationTaskList', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    return mount(OptimizationTaskList, {
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

    getOptimizationTaskListMock.mockResolvedValue(
      buildListResponse(
        [
          buildTask({ id: 101, task_type: 'sql', status: 'queued' }),
          buildTask({
            id: 102,
            task_type: 'mybatis',
            status: 'running',
            object_preview: '<select id="findOrders">...</select>'
          }),
          buildTask({
            id: 103,
            task_type: 'sql',
            status: 'completed',
            object_preview: 'SELECT id, name FROM users'
          }),
          buildTask({
            id: 104,
            task_type: 'mybatis',
            status: 'failed',
            object_preview: '<select id="findUsers">...</select>'
          })
        ],
        14
      )
    )
  })

  it('renders the entry workspace without middle summary cards', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(getOptimizationTaskListMock).toHaveBeenCalledWith({
      page: 1,
      per_page: 10,
      task_type: ''
    })
    expect(wrapper.text()).not.toContain('创建新的优化任务，并跟踪历史结果与状态')
    expect(wrapper.text()).not.toContain('共 14 条任务记录')
    expect(wrapper.text()).not.toContain('任务总数')
    expect(wrapper.text()).not.toContain('立即创建任务')
    expect(wrapper.text()).not.toContain('进入 XML 优化')
    expect(wrapper.findAll('.entry-card')).toHaveLength(2)
    expect(wrapper.findAll('.summary-card')).toHaveLength(0)
  })

  it('navigates from both entry cards and the task object link', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button.entry-card--sql').trigger('click')
    await wrapper.find('button.entry-card--mybatis').trigger('click')
    await wrapper.find('button.task-link').trigger('click')

    expect(pushMock).toHaveBeenNthCalledWith(1, '/optimization-tasks/create/sql')
    expect(pushMock).toHaveBeenNthCalledWith(2, '/optimization-tasks/create/mybatis')
    expect(pushMock).toHaveBeenNthCalledWith(3, '/optimization-tasks/101')
  })

  it('filters, refreshes, and paginates with the existing store contract', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.filter-chip')[2].trigger('click')
    await flushPromises()
    expect(getOptimizationTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 10,
      task_type: 'mybatis'
    })

    await wrapper.find('button.refresh-button').trigger('click')
    await flushPromises()
    expect(getOptimizationTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 10,
      task_type: 'mybatis'
    })

    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    pagination.vm.$emit('current-change', 2)
    await flushPromises()
    expect(getOptimizationTaskListMock).toHaveBeenLastCalledWith({
      page: 2,
      per_page: 10,
      task_type: 'mybatis'
    })

    pagination.vm.$emit('size-change', 20)
    await flushPromises()
    expect(getOptimizationTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 20,
      task_type: 'mybatis'
    })
  })

  it('shows the guided empty state when there is no task data', async () => {
    getOptimizationTaskListMock.mockResolvedValueOnce(buildListResponse([], 0))

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('还没有优化任务，先从上方创建一个新任务')
    expect(wrapper.find('.task-table').exists()).toBe(false)
  })
})
