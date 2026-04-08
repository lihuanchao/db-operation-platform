import { describe, expect, it } from 'vitest'
import { canAccessPath, getVisibleMenus } from './access'

describe('access helpers', () => {
  it('shows only optimization and slow sql for normal user', () => {
    const menus = getVisibleMenus('user').map((item) => item.path)
    expect(menus).toEqual(['/optimization-tasks', '/slow-sqls'])
  })

  it('allows normal user to access detail routes under allowed modules', () => {
    expect(canAccessPath('user', '/optimization-tasks/12')).toBe(true)
    expect(canAccessPath('user', '/slow-sql/abc123')).toBe(true)
  })

  it('blocks normal user from admin pages', () => {
    expect(canAccessPath('user', '/connections')).toBe(false)
    expect(canAccessPath('user', '/users')).toBe(false)
  })

  it('allows admin to access admin pages', () => {
    expect(canAccessPath('admin', '/permissions')).toBe(true)
  })

  it('shows unified log center and flashback menus for admin', () => {
    const menus = getVisibleMenus('admin').map((item) => item.path)

    expect(menus).toContain('/execution-logs')
    expect(menus).toContain('/flashback-tasks')
    expect(canAccessPath('admin', '/flashback-tasks/22')).toBe(true)
  })
})
