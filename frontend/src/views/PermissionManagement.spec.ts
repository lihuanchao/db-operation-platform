import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'

const {
  getUserListMock,
  getConnectionListMock,
  getUserConnectionPermissionsMock,
  saveUserConnectionPermissionsMock
} = vi.hoisted(() => ({
  getUserListMock: vi.fn(),
  getConnectionListMock: vi.fn(),
  getUserConnectionPermissionsMock: vi.fn(),
  saveUserConnectionPermissionsMock: vi.fn()
}))

vi.mock('@/api/userAdmin', () => ({
  getUserList: getUserListMock,
  createUser: vi.fn(),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
  updateUser: vi.fn(),
  updateUserStatus: vi.fn()
}))

vi.mock('@/api/dbConnection', () => ({
  getConnectionList: getConnectionListMock
}))

vi.mock('@/api/permissionAdmin', () => ({
  getRoles: vi.fn(),
  getUserConnectionPermissions: getUserConnectionPermissionsMock,
  saveUserConnectionPermissions: saveUserConnectionPermissionsMock
}))

import PermissionManagement from './PermissionManagement.vue'
import { usePermissionAdminStore } from '@/stores/permissionAdmin'

describe('PermissionManagement', () => {
  const infoSpy = vi.spyOn(ElMessage, 'info').mockImplementation(() => null as any)
  const successSpy = vi.spyOn(ElMessage, 'success').mockImplementation(() => null as any)

  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)

    const wrapper = mount(PermissionManagement, {
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
      permissionStore: usePermissionAdminStore()
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()

    getUserListMock.mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            employee_no: 'U1001',
            real_name: '张三',
            department: 'DBA',
            role_code: 'user',
            status: 'enabled'
          },
          {
            id: 2,
            employee_no: 'A0001',
            real_name: '系统管理员',
            department: '平台组',
            role_code: 'admin',
            status: 'enabled'
          }
        ]
      }
    })

    getConnectionListMock.mockResolvedValue({
      data: {
        items: [
          {
            id: 11,
            connection_name: '订单库',
            host: '10.0.0.11',
            manage_host: '172.16.0.11',
            port: 3306,
            username: 'root',
            is_enabled: true
          },
          {
            id: 12,
            connection_name: '报表库',
            host: '10.0.0.12',
            manage_host: '172.16.0.12',
            port: 3306,
            username: 'root',
            is_enabled: true
          }
        ]
      }
    })

    getUserConnectionPermissionsMock.mockResolvedValue({
      data: {
        connection_ids: [11]
      }
    })

    saveUserConnectionPermissionsMock.mockResolvedValue({
      data: {
        connection_ids: [11]
      }
    })
  })

  it('shows the pre-selection placeholder and disables save', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('请选择左侧普通用户进行授权')
    expect(wrapper.find('button.permission-save').attributes('disabled')).toBeDefined()
  })

  it('loads permissions for a regular user and renders the summary count', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    await wrapper.findAll('.user-card')[0].trigger('click')
    await flushPromises()

    expect(getUserConnectionPermissionsMock).toHaveBeenCalledWith(1)
    expect(wrapper.text()).toContain('张三（U1001）')
    expect(wrapper.text()).toContain('已授权 1 项')
  })

  it('shows the admin shortcut hint instead of loading editable permissions', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    await wrapper.findAll('.user-card')[1].trigger('click')
    await flushPromises()

    expect(infoSpy).toHaveBeenCalledWith('管理员默认拥有全部权限，无需单独授权')
    expect(getUserConnectionPermissionsMock).not.toHaveBeenCalled()
    expect(wrapper.find('button.permission-save').attributes('disabled')).toBeDefined()
  })

  it('toggles connection selection in list rows and saves permissions', async () => {
    const { wrapper, permissionStore } = mountView()
    await flushPromises()

    await wrapper.findAll('.user-card')[0].trigger('click')
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[1].setValue('报表库')
    await flushPromises()

    await wrapper.find('.connection-card').trigger('click')
    expect(permissionStore.selectedConnectionIds).toEqual([11, 12])

    await wrapper.find('button.permission-save').trigger('click')
    await flushPromises()

    expect(saveUserConnectionPermissionsMock).toHaveBeenCalledWith(1, [11, 12])
    expect(successSpy).toHaveBeenCalledWith('授权已保存')
  })

  it('renders host column in connection authorization list', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    await wrapper.findAll('.user-card')[0].trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('主机地址')
    expect(wrapper.text()).toContain('10.0.0.11')
  })

  it('renders search-specific empty states for users and connections', async () => {
    const { wrapper } = mountView()
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('不存在')
    await flushPromises()
    expect(wrapper.text()).toContain('未匹配到用户，请调整搜索条件')

    await inputs[0].setValue('')
    await wrapper.findAll('.user-card')[0].trigger('click')
    await flushPromises()

    await inputs[1].setValue('无匹配连接')
    await flushPromises()
    expect(wrapper.text()).toContain('未匹配到连接，请调整搜索条件')
  })
})
