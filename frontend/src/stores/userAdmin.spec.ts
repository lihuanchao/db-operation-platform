import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/userAdmin', () => ({
  getUserList: vi.fn(async () => ({
    success: true,
    data: {
      items: [
        {
          id: 1,
          employee_no: 'U1001',
          real_name: '张三',
          department: '研发',
          role_code: 'user',
          status: 'enabled'
        }
      ]
    }
  })),
  createUser: vi.fn(async () => ({ success: true })),
  updateUser: vi.fn(async () => ({ success: true })),
  updateUserStatus: vi.fn(async () => ({ success: true })),
  resetUserPassword: vi.fn(async () => ({ success: true })),
  deleteUser: vi.fn(async () => ({ success: true }))
}))

import { useUserAdminStore } from './userAdmin'

describe('user admin store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('loads user list', async () => {
    const store = useUserAdminStore()
    await store.fetchList()
    expect(store.list).toHaveLength(1)
    expect(store.list[0].employee_no).toBe('U1001')
  })
})
