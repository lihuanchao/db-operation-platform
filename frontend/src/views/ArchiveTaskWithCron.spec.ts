import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessage, ElMessageBox } from 'element-plus'
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
  const mountedWrappers: Array<{ unmount: () => void }> = []

  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    const wrapper = mount(ArchiveTaskWithCron, {
      attachTo: document.body,
      global: {
        plugins: [pinia, ElementPlus],
        stubs: {
          AppLayout: {
            template: '<div class="layout-stub"><slot /></div>'
          }
        }
      }
    })

    mountedWrappers.push(wrapper)

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

  afterEach(() => {
    while (mountedWrappers.length) {
      mountedWrappers.pop()?.unmount()
    }
    document.body.innerHTML = ''
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

  it('opens the add entry drawer and shows the drawer sections and save-execute action', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    const addButton = wrapper
      .findAll('button')
      .find(button => button.text().includes('新增归档任务'))

    expect(addButton).toBeTruthy()
    await addButton!.trigger('click')
    await flushPromises()

    expect((wrapper.vm as any).formDialogVisible).toBe(true)

    const drawer = document.body.querySelector('.el-drawer')
    const pageText = document.body.textContent || ''
    expect(drawer).not.toBeNull()
    expect(pageText).toContain('新增归档任务')
    expect(pageText).toContain('核心信息')
    expect(pageText).toContain('高级配置')
    expect(pageText).toContain('保存并执行')
    expect(pageText).not.toContain('配置归档任务的名称、来源与执行条件。')
    expect(pageText).not.toContain('可选配置归档落库位置与任务启用状态。')
    expect((wrapper.vm as any).formData.source_connection_id).toBeUndefined()
  })

  it('creates the task by calling addTask before executeTask and closes the form dialog', async () => {
    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    const addPayloads: Array<Record<string, unknown>> = []
    const addSpy = vi.spyOn(archiveStore, 'addTask').mockImplementation(async (payload: any) => {
      addPayloads.push(payload)
      return buildArchiveTask({ id: 301 })
    })
    const executeSpy = vi.spyOn(archiveStore, 'executeTask').mockImplementation(async () => {
      expect((wrapper.vm as any).formDialogVisible).toBe(false)
      return {
        message: '任务已加入后台执行'
      } as any
    })

    const vm = wrapper.vm as any
    vm.formRef = {
      validate: vi.fn().mockResolvedValue(undefined)
    }

    vm.handleAddTask()
    vm.formData.task_name = '新增归档任务'
    vm.formData.source_connection_id = 11
    vm.formData.source_database = 'sales'
    vm.formData.source_table = 'orders'
    vm.formData.where_condition = 'created_at < NOW()'

    await vm.handleFormSubmit()
    await flushPromises()

    expect(addSpy).toHaveBeenCalledTimes(1)
    expect(addPayloads[0]).toEqual(expect.objectContaining({
      task_name: '新增归档任务',
      source_connection_id: 11,
      source_database: 'sales',
      source_table: 'orders',
      where_condition: 'created_at < NOW()'
    }))
    expect(executeSpy).toHaveBeenCalledWith(301)
    expect(addSpy.mock.invocationCallOrder[0]).toBeLessThan(executeSpy.mock.invocationCallOrder[0])
    expect(vm.formDialogVisible).toBe(false)
  })

  it('warns when auto execution fails after creating a task', async () => {
    const warningSpy = vi.spyOn(ElMessage, 'warning').mockImplementation(() => null as any)
    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    vi.spyOn(archiveStore, 'addTask').mockResolvedValue(buildArchiveTask({ id: 302 }))
    vi.spyOn(archiveStore, 'executeTask').mockResolvedValue(null)

    const vm = wrapper.vm as any
    vm.formRef = {
      validate: vi.fn().mockResolvedValue(undefined)
    }

    vm.handleAddTask()
    vm.formData.task_name = '新增归档任务'
    vm.formData.source_connection_id = 11
    vm.formData.source_database = 'sales'
    vm.formData.source_table = 'orders'
    vm.formData.where_condition = 'created_at < NOW()'

    await vm.handleFormSubmit()
    await flushPromises()

    expect(warningSpy).toHaveBeenCalledWith('任务已创建成功，但自动执行失败，请在列表中手动点击“执行”重试。')
    expect(vm.formDialogVisible).toBe(false)
    warningSpy.mockRestore()
  })

  it('treats form validation failures as handled errors without submitting', async () => {
    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    const addSpy = vi.spyOn(archiveStore, 'addTask')
    const vm = wrapper.vm as any
    const validateError = new Error('validation failed')
    vm.formRef = {
      validate: vi.fn().mockRejectedValue(validateError)
    }

    vm.handleAddTask()
    vm.formData.task_name = '新增归档任务'

    await expect(vm.handleFormSubmit()).resolves.toBeUndefined()

    expect(addSpy).not.toHaveBeenCalled()
  })

  it('does not show inline validation text under required fields when submit fails', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    const vm = wrapper.vm as any
    vm.handleAddTask()
    await flushPromises()

    await vm.handleFormSubmit()
    await flushPromises()

    const drawer = document.body.querySelector('.archive-task-drawer')
    const errorNodes = drawer?.querySelectorAll('.el-form-item__error') ?? []
    expect(errorNodes.length).toBe(0)
  })

  it('shows a visible error when submit fails', async () => {
    const errorSpy = vi.spyOn(ElMessage, 'error').mockImplementation(() => null as any)
    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    vi.spyOn(archiveStore, 'addTask').mockRejectedValue(new Error('submit failed'))

    const vm = wrapper.vm as any
    vm.formRef = {
      validate: vi.fn().mockResolvedValue(undefined)
    }

    vm.handleAddTask()
    vm.formData.task_name = '新增归档任务'
    vm.formData.source_connection_id = 11
    vm.formData.source_database = 'sales'
    vm.formData.source_table = 'orders'
    vm.formData.where_condition = 'created_at < NOW()'

    await vm.handleFormSubmit()
    await flushPromises()

    expect(errorSpy).toHaveBeenCalledWith('提交失败，请稍后重试。')
    errorSpy.mockRestore()
  })

  it('warns when auto execution throws after creating a task', async () => {
    const warningSpy = vi.spyOn(ElMessage, 'warning').mockImplementation(() => null as any)
    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    vi.spyOn(archiveStore, 'addTask').mockResolvedValue(buildArchiveTask({ id: 303 }))
    vi.spyOn(archiveStore, 'executeTask').mockRejectedValue(new Error('execute failed'))

    const vm = wrapper.vm as any
    vm.formRef = {
      validate: vi.fn().mockResolvedValue(undefined)
    }

    vm.handleAddTask()
    vm.formData.task_name = '新增归档任务'
    vm.formData.source_connection_id = 11
    vm.formData.source_database = 'sales'
    vm.formData.source_table = 'orders'
    vm.formData.where_condition = 'created_at < NOW()'

    await vm.handleFormSubmit()
    await flushPromises()

    expect(warningSpy).toHaveBeenCalledWith('任务已创建成功，但自动执行失败，请在列表中手动点击“执行”重试。')
    expect(vm.formDialogVisible).toBe(false)
    warningSpy.mockRestore()
  })

  it('prevents duplicate submit calls while a submission is in progress', async () => {
    const { wrapper, archiveStore } = mountView()
    await flushPromises()

    let resolveAdd: ((value: ArchiveTask) => void) | undefined
    const pendingAdd = new Promise<ArchiveTask>((resolve) => {
      resolveAdd = resolve
    })

    const addSpy = vi.spyOn(archiveStore, 'addTask').mockReturnValue(pendingAdd)
    vi.spyOn(archiveStore, 'executeTask').mockResolvedValue({ log_id: 1 } as any)

    const vm = wrapper.vm as any
    vm.formRef = {
      validate: vi.fn().mockResolvedValue(undefined)
    }

    vm.handleAddTask()
    vm.formData.task_name = '新增归档任务'
    vm.formData.source_connection_id = 11
    vm.formData.source_database = 'sales'
    vm.formData.source_table = 'orders'
    vm.formData.where_condition = 'created_at < NOW()'

    const firstSubmit = vm.handleFormSubmit()
    const secondSubmit = vm.handleFormSubmit()

    await flushPromises()
    expect(addSpy).toHaveBeenCalledTimes(1)

    resolveAdd?.(buildArchiveTask({ id: 304 }))
    await firstSubmit
    await secondSubmit
  })
})
