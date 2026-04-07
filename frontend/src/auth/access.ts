export type RoleCode = 'admin' | 'user'

export interface MenuItem {
  path: string
  label: string
  roles: RoleCode[]
  matchPrefixes: string[]
}

export const MENU_ITEMS: MenuItem[] = [
  { path: '/optimization-tasks', label: 'SQL智能建议', roles: ['admin', 'user'], matchPrefixes: ['/optimization-tasks'] },
  { path: '/slow-sqls', label: '慢SQL管理', roles: ['admin', 'user'], matchPrefixes: ['/slow-sqls', '/slow-sql/'] },
  { path: '/connections', label: '连接管理', roles: ['admin'], matchPrefixes: ['/connections'] },
  { path: '/archive-tasks', label: '归档任务', roles: ['admin'], matchPrefixes: ['/archive-tasks'] },
  { path: '/execution-logs', label: '执行日志', roles: ['admin'], matchPrefixes: ['/execution-logs'] },
  { path: '/users', label: '用户管理', roles: ['admin'], matchPrefixes: ['/users'] },
  { path: '/roles', label: '角色管理', roles: ['admin'], matchPrefixes: ['/roles'] },
  { path: '/permissions', label: '权限管理', roles: ['admin'], matchPrefixes: ['/permissions'] }
]

export function getVisibleMenus(roleCode: RoleCode): MenuItem[] {
  return MENU_ITEMS.filter((item) => item.roles.includes(roleCode))
}

export function canAccessPath(roleCode: RoleCode, path: string): boolean {
  const matched = MENU_ITEMS.find((item) => item.matchPrefixes.some((prefix) => path === prefix || path.startsWith(prefix)))
  return matched ? matched.roles.includes(roleCode) : roleCode === 'admin'
}
