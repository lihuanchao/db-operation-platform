import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/auth', () => ({
  login: vi.fn(async () => ({
    success: true,
    data: {
      user: {
        id: 1,
        employee_no: 'U1001',
        real_name: '张三',
        department: '研发',
        role_code: 'user',
        status: 'enabled'
      },
      menus: [
        { path: '/optimization-tasks', label: 'SQL优化建议' },
        { path: '/slow-sqls', label: '慢SQL列表' }
      ]
    }
  })),
  getCurrentUser: vi.fn(async () => ({ success: false })),
  logout: vi.fn(async () => ({ success: true, data: { logged_out: true } })),
  getAuthorizedConnections: vi.fn(async () => ({
    success: true,
    data: {
      items: [
        {
          id: 10,
          connection_name: '业务库',
          host: '10.0.0.10',
          manage_host: '10.0.0.11',
          port: 3306,
          username: 'root',
          is_enabled: true
        }
      ]
    }
  }))
}))

import { useAuthStore } from './auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('stores user info and home path after login', async () => {
    const store = useAuthStore()
    await store.login({
      employee_no: 'U1001',
      password: 'Passw0rd!'
    })
    expect(store.isAuthenticated).toBe(true)
    expect(store.roleCode).toBe('user')
    expect(store.homePath).toBe('/optimization-tasks')
  })

  it('loads authorized connections for dropdown usage', async () => {
    const store = useAuthStore()
    await store.fetchAuthorizedConnections()
    expect(store.authorizedConnections).toHaveLength(1)
    expect(store.authorizedConnections[0].connection_name).toBe('业务库')
  })
})
