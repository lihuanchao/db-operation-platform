import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

const {
  pushMock,
  createSqlTaskMock,
  createMyBatisTaskMock,
  fetchAuthorizedConnectionsMock,
  authStoreState
} = vi.hoisted(() => ({
  pushMock: vi.fn(),
  createSqlTaskMock: vi.fn(),
  createMyBatisTaskMock: vi.fn(),
  fetchAuthorizedConnectionsMock: vi.fn(),
  authStoreState: {
    authorizedConnections: [
      {
        id: 1,
        connection_name: '订单库',
        host: '10.0.0.11',
        port: 3306
      }
    ]
  }
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock
  })
}))

vi.mock('@/stores/optimizationTask', () => ({
  useOptimizationTaskStore: () => ({
    submitLoading: false,
    createSqlTask: createSqlTaskMock,
    createMyBatisTask: createMyBatisTaskMock
  })
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    authorizedConnections: authStoreState.authorizedConnections,
    fetchAuthorizedConnections: fetchAuthorizedConnectionsMock
  })
}))

import OptimizationTaskCreateSql from './OptimizationTaskCreateSql.vue'
import OptimizationTaskCreateMyBatis from './OptimizationTaskCreateMyBatis.vue'

describe('OptimizationTaskCreate pages', () => {
  function mountSqlPage() {
    return mount(OptimizationTaskCreateSql, {
      global: {
        plugins: [ElementPlus],
        stubs: {
          AppLayout: {
            template: '<div class="layout-stub"><slot /></div>'
          }
        }
      }
    })
  }

  function mountMyBatisPage() {
    return mount(OptimizationTaskCreateMyBatis, {
      global: {
        plugins: [ElementPlus],
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
    authStoreState.authorizedConnections = [
      {
        id: 1,
        connection_name: '订单库',
        host: '10.0.0.11',
        port: 3306
      }
    ]
    createSqlTaskMock.mockResolvedValue({ id: 301 })
    createMyBatisTaskMock.mockResolvedValue({ id: 401 })
  })

  it('sql page removes intro copy and supports back + submit flow', async () => {
    const wrapper = mountSqlPage()
    await flushPromises()

    expect(wrapper.text()).not.toContain('系统将自动获取执行计划和建表语句并异步优化')

    await wrapper.find('button.back-btn').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/optimization-tasks')

    await wrapper.find('button.submit-btn').trigger('click')
    await flushPromises()
    expect(createSqlTaskMock).not.toHaveBeenCalled()

    const select = wrapper.findComponent({ name: 'ElSelect' })
    select.vm.$emit('update:modelValue', 1)
    await flushPromises()
    await wrapper.find('input[placeholder="请输入数据库名"]').setValue('orders')
    await wrapper.find('textarea[placeholder="请输入待优化 SQL（仅支持查询语句）"]').setValue('SELECT id FROM orders LIMIT 10')

    await wrapper.find('button.submit-btn').trigger('click')
    await flushPromises()

    expect(createSqlTaskMock).toHaveBeenCalledWith({
      db_connection_id: 1,
      database_name: 'orders',
      sql_text: 'SELECT id FROM orders LIMIT 10'
    })
    expect(pushMock).toHaveBeenLastCalledWith('/optimization-tasks/301')
  })

  it('mybatis page removes intro copy and supports back + submit flow', async () => {
    const wrapper = mountMyBatisPage()
    await flushPromises()

    expect(wrapper.text()).not.toContain('系统会自动提取查询并进行索引与写法优化')

    await wrapper.find('button.back-btn').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/optimization-tasks')

    await wrapper.find('button.submit-btn').trigger('click')
    await flushPromises()
    expect(createMyBatisTaskMock).not.toHaveBeenCalled()

    const select = wrapper.findComponent({ name: 'ElSelect' })
    select.vm.$emit('update:modelValue', 1)
    await flushPromises()
    await wrapper.find('input[placeholder="请输入数据库名"]').setValue('orders')
    await wrapper.find('textarea[placeholder="请输入 MyBatis XML 代码"]').setValue('<select id="findOrders">SELECT * FROM orders</select>')

    await wrapper.find('button.submit-btn').trigger('click')
    await flushPromises()

    expect(createMyBatisTaskMock).toHaveBeenCalledWith({
      db_connection_id: 1,
      database_name: 'orders',
      xml_text: '<select id="findOrders">SELECT * FROM orders</select>'
    })
    expect(pushMock).toHaveBeenLastCalledWith('/optimization-tasks/401')
  })
})
