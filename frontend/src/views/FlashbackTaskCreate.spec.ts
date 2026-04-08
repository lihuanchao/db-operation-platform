import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'

const pushMock = vi.fn()

const {
  getAuthorizedConnectionsMock,
  getFlashbackTaskListMock,
  createFlashbackTaskMock
} = vi.hoisted(() => ({
  getAuthorizedConnectionsMock: vi.fn(),
  getFlashbackTaskListMock: vi.fn(),
  createFlashbackTaskMock: vi.fn()
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/api/auth', () => ({
  getAuthorizedConnections: getAuthorizedConnectionsMock,
  getCurrentUser: vi.fn(),
  login: vi.fn(),
  logout: vi.fn()
}))

vi.mock('@/api/flashbackTask', () => ({
  getFlashbackTaskList: getFlashbackTaskListMock,
  getFlashbackTask: vi.fn(),
  createFlashbackTask: createFlashbackTaskMock,
  getFlashbackTaskArtifacts: vi.fn(),
  getFlashbackTaskLogContent: vi.fn(),
  downloadFlashbackTaskArtifact: vi.fn(),
  downloadFlashbackTaskLog: vi.fn()
}))

import FlashbackTaskCreate from './FlashbackTaskCreate.vue'

describe('FlashbackTaskCreate', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    return mount(FlashbackTaskCreate, {
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

    getAuthorizedConnectionsMock.mockResolvedValue({
      success: true,
      data: {
        items: [
          {
            id: 9,
            connection_name: '订单库',
            host: '10.0.0.11',
            port: 3306
          }
        ]
      }
    })

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

    createFlashbackTaskMock.mockResolvedValue({
      success: true,
      data: {
        id: 88,
        db_connection_id: 9,
        connection_name: '订单库',
        database_name: 'sales',
        table_name: 'orders',
        mode: 'repl',
        sql_type: 'delete',
        work_type: '2sql',
        status: 'queued',
        progress: 0,
        artifacts: [],
        created_at: '2026-04-08 10:20:00',
        updated_at: '2026-04-08 10:20:00'
      }
    })
  })

  it('shows the connection summary and blocks incomplete submission', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('repl')
    expect(wrapper.text()).toContain('10.0.0.11:3306')

    await wrapper.get('button.submit-btn').trigger('click')
    await flushPromises()

    expect(createFlashbackTaskMock).not.toHaveBeenCalled()
  }, 15000)

  it('does not fall back to the first connection when multiple connections exist', async () => {
    getAuthorizedConnectionsMock.mockResolvedValueOnce({
      success: true,
      data: {
        items: [
          {
            id: 9,
            connection_name: '订单库',
            host: '10.0.0.11',
            port: 3306
          },
          {
            id: 10,
            connection_name: '审计库',
            host: '10.0.0.12',
            port: 3307
          }
        ]
      }
    })

    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('请选择连接后显示摘要')
    expect(wrapper.text()).not.toContain('10.0.0.11:3306')
  })

  it('submits the minimal required fields and navigates to the task detail page', async () => {
    const wrapper = mountView()
    await flushPromises()

    const select = wrapper.findComponent({ name: 'ElSelect' })
    select.vm.$emit('update:modelValue', 9)
    await flushPromises()

    await wrapper.get('input[placeholder="数据库名"]').setValue('sales')
    await wrapper.get('input[placeholder="表名"]').setValue('orders')

    await wrapper.get('button.submit-btn').trigger('click')
    await flushPromises()

    expect(createFlashbackTaskMock).toHaveBeenCalledWith({
      db_connection_id: 9,
      database_name: 'sales',
      table_name: 'orders',
      sql_type: 'delete',
      work_type: '2sql'
    })
    expect(pushMock).toHaveBeenLastCalledWith('/flashback-tasks/88')
  })

  it('includes optional time and binlog fields when they are provided', async () => {
    const wrapper = mountView()
    await flushPromises()

    const select = wrapper.findComponent({ name: 'ElSelect' })
    select.vm.$emit('update:modelValue', 9)
    await flushPromises()

    await wrapper.get('input[placeholder="数据库名"]').setValue('sales')
    await wrapper.get('input[placeholder="表名"]').setValue('orders')
    await wrapper.get('input[placeholder="请输入开始时间"]').setValue('2026-04-08 10:00:00')
    await wrapper.get('input[placeholder="请输入结束时间"]').setValue('2026-04-08 10:05:00')
    await wrapper.get('input[placeholder="请输入开始 binlog 文件"]').setValue('mysql-bin.000001')
    await wrapper.get('input[placeholder="请输入结束 binlog 文件"]').setValue('mysql-bin.000002')

    await wrapper.get('button.submit-btn').trigger('click')
    await flushPromises()

    expect(createFlashbackTaskMock).toHaveBeenCalledWith({
      db_connection_id: 9,
      database_name: 'sales',
      table_name: 'orders',
      sql_type: 'delete',
      work_type: '2sql',
      start_datetime: '2026-04-08 10:00:00',
      stop_datetime: '2026-04-08 10:05:00',
      start_file: 'mysql-bin.000001',
      stop_file: 'mysql-bin.000002'
    })
  })
})
