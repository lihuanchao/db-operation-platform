import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessageBox } from 'element-plus'
import type { ArchiveTask } from '@/types'
import { useArchiveTaskStore } from '@/stores/archiveTask'

const routeState = vi.hoisted(() => ({
  params: {} as Record<string, string>
}))

const {
  getArchiveTaskListMock,
  getArchiveTaskMock,
  getCronJobListMock,
  getConnectionListMock
} = vi.hoisted(() => ({
  getArchiveTaskListMock: vi.fn(),
  getArchiveTaskMock: vi.fn(),
  getCronJobListMock: vi.fn(),
  getConnectionListMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRoute: () => routeState
}))

vi.mock('@/api/archiveTask', () => ({
  getArchiveTaskList: getArchiveTaskListMock,
  getArchiveTask: getArchiveTaskMock,
  createArchiveTask: vi.fn(),
  updateArchiveTask: vi.fn(),
  deleteArchiveTask: vi.fn(),
  executeArchiveTask: vi.fn()
}))

vi.mock('@/api/cronJob', () => ({
  getCronJobList: getCronJobListMock,
  getCronJob: vi.fn(),
  createCronJob: vi.fn(),
  updateCronJob: vi.fn(),
  deleteCronJob: vi.fn(),
  toggleCronJob: vi.fn()
}))

vi.mock('@/api/dbConnection', () => ({
  getConnectionList: getConnectionListMock,
  getConnection: vi.fn(),
  createConnection: vi.fn(),
  updateConnection: vi.fn(),
  deleteConnection: vi.fn(),
  testConnection: vi.fn(),
  testConnectionDirect: vi.fn()
}))

import ArchiveTaskWithCron from './ArchiveTaskWithCron.vue'

function buildArchiveTask(overrides: Partial<ArchiveTask> = {}): ArchiveTask {
  return {
    id: 101,
    task_name: '订单归档任务',
    source_connection_id: 11,
    source_database: 'sales',
    source_table: 'orders',
    dest_connection_id: 12,
    dest_database: 'archive',
    dest_table: 'orders_2026',
    where_condition: 'created_at < NOW()',
    is_enabled: true,
    updated_at: '2026-04-08 10:00:00',
    ...overrides
  }
}

function buildArchiveListResponse(items: ArchiveTask[]) {
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

describe('ArchiveTaskWithCron', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    const wrapper = mount(ArchiveTaskWithCron, {
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
      archiveStore: useArchiveTaskStore()
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    routeState.params = {}

    getArchiveTaskListMock.mockResolvedValue(buildArchiveListResponse([]))
    getArchiveTaskMock.mockResolvedValue({ success: true, data: buildArchiveTask() })
    getCronJobListMock.mockResolvedValue({
      success: true,
      data: { items: [], total: 0, page: 1, per_page: 10 }
    })
    getConnectionListMock.mockResolvedValue({
      success: true,
      data: { items: [], total: 0, page: 1, per_page: 10 }
    })
  })

  it('loads archive detail route into task context before refreshing the list', async () => {
    routeState.params = { id: '101' }
    getArchiveTaskListMock.mockResolvedValueOnce(buildArchiveListResponse([
      buildArchiveTask({ id: 202, task_name: '订单归档任务-副本' })
    ]))

    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    expect(getArchiveTaskMock).toHaveBeenCalledWith(101)
    expect(getArchiveTaskListMock).not.toHaveBeenCalled()
    expect(archiveStore.filters.task_name).toBe('')
    expect(wrapper.text()).toContain('订单归档任务')
    expect(wrapper.text()).not.toContain('订单归档任务-副本')
    expect(wrapper.text()).toContain('共 1 条')
    expect(wrapper.get('[data-testid="archive-context"]').text()).toContain('订单归档任务')
  })

  it('falls back to the normal list when the archive detail id is invalid', async () => {
    routeState.params = { id: '999' }
    getArchiveTaskMock.mockRejectedValueOnce(new Error('Request failed with status code 404'))

    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    expect(getArchiveTaskMock).toHaveBeenCalledWith(999)
    expect(getArchiveTaskListMock).toHaveBeenLastCalledWith({
      page: 1,
      per_page: 10,
      task_name: '',
      source_connection_id: undefined
    })
    expect(archiveStore.filters.task_name).toBe('')
    expect(wrapper.find('[data-testid="archive-context"]').exists()).toBe(false)
  })

  it('refreshes the located task after editing in exact detail context', async () => {
    routeState.params = { id: '101' }

    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    const updatedTask = buildArchiveTask({
      task_name: '订单归档任务-已更新',
      source_table: 'orders_history'
    })
    const editSpy = vi.spyOn(archiveStore, 'editTask').mockResolvedValue(updatedTask)
    const vm = wrapper.vm as any

    vm.formRef = {
      validate: vi.fn().mockResolvedValue(undefined)
    }
    vm.handleEdit(buildArchiveTask())
    vm.formData.task_name = '订单归档任务-已更新'
    vm.formData.source_table = 'orders_history'

    await vm.handleFormSubmit()
    await flushPromises()

    expect(editSpy).toHaveBeenCalledWith(101, expect.objectContaining({
      task_name: '订单归档任务-已更新',
      source_table: 'orders_history'
    }))
    expect(wrapper.get('[data-testid="archive-context"]').text()).toContain('订单归档任务-已更新')
    expect(wrapper.text()).toContain('orders_history')
    expect(wrapper.text()).not.toContain('源表orders')
  })

  it('leaves exact detail context after deleting the located task', async () => {
    routeState.params = { id: '101' }
    getArchiveTaskListMock.mockResolvedValueOnce(buildArchiveListResponse([
      buildArchiveTask({ id: 202, task_name: '普通列表任务', source_table: 'orders_archive' })
    ]))

    const confirmSpy = vi.spyOn(ElMessageBox, 'confirm').mockResolvedValue('confirm' as any)
    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    const removeSpy = vi.spyOn(archiveStore, 'removeTask').mockResolvedValue(undefined)
    const vm = wrapper.vm as any

    await vm.handleDelete(buildArchiveTask())
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalled()
    expect(removeSpy).toHaveBeenCalledWith(101)
    expect(getArchiveTaskListMock).toHaveBeenCalledWith({
      page: 1,
      per_page: 10,
      task_name: '',
      source_connection_id: undefined
    })
    expect(wrapper.find('[data-testid="archive-context"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('普通列表任务')
  })
})
