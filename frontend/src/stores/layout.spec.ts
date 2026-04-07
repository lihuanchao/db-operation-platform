import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { HOME_TAB, LAYOUT_STORAGE_KEY, useLayoutStore } from './layout'

describe('layout store', () => {
  function readPersistedState() {
    return JSON.parse(localStorage.getItem(LAYOUT_STORAGE_KEY) ?? 'null') as {
      collapsed?: boolean
      tabs?: Array<{ path: string; title: string; closable: boolean }>
      activePath?: string
    } | null
  }

  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('uses only home tab by default when storage is empty', () => {
    const store = useLayoutStore()

    expect(store.tabs).toEqual([HOME_TAB])
    expect(store.collapsed).toBe(false)
    expect(store.activePath).toBe(HOME_TAB.path)
  })

  it('does not duplicate tabs for the same path and only activates the existing tab', () => {
    const store = useLayoutStore()
    const tab = { path: '/slow-sqls', title: '慢SQL列表', closable: true }

    store.openTab(tab.path, tab.title, tab.closable)
    store.openTab(tab.path, '其他标题', false)

    expect(store.tabs).toEqual([HOME_TAB, tab])
    expect(store.activePath).toBe(tab.path)
  })

  it('keeps the home tab open and returns to home after closing the active non-home tab', () => {
    const store = useLayoutStore()
    const tab = { path: '/users', title: '用户管理', closable: true }

    store.openTab(tab.path, tab.title, tab.closable)
    store.closeTab(tab.path)

    expect(store.tabs).toEqual([HOME_TAB])
    expect(store.activePath).toBe(HOME_TAB.path)

    store.closeTab(HOME_TAB.path)

    expect(store.tabs).toEqual([HOME_TAB])
    expect(store.activePath).toBe(HOME_TAB.path)
  })

  it('persists collapsed and active path changes to localStorage', () => {
    const store = useLayoutStore()

    store.toggleCollapsed()

    expect(readPersistedState()?.collapsed).toBe(true)

    store.syncByRoute('/permissions', '权限管理')

    expect(readPersistedState()?.activePath).toBe('/permissions')
  })

  it('does not close tabs marked as non-closable', () => {
    const store = useLayoutStore()

    store.openTab('/reports', '报表', false)
    store.closeTab('/reports')

    expect(store.tabs).toEqual([
      HOME_TAB,
      { path: '/reports', title: '报表', closable: false }
    ])
    expect(store.activePath).toBe('/reports')
  })

  it('hydrates valid data and falls back to home when storage data is invalid', () => {
    localStorage.setItem(
      LAYOUT_STORAGE_KEY,
      JSON.stringify({
        collapsed: true,
        tabs: [
          HOME_TAB,
          { path: '/permissions', title: '权限管理', closable: true }
        ],
        activePath: '/permissions'
      })
    )

    const restoredStore = useLayoutStore()

    expect(restoredStore.collapsed).toBe(true)
    expect(restoredStore.tabs).toEqual([
      HOME_TAB,
      { path: '/permissions', title: '权限管理', closable: true }
    ])
    expect(restoredStore.activePath).toBe('/permissions')

    localStorage.setItem(
      LAYOUT_STORAGE_KEY,
      JSON.stringify({
        collapsed: true,
        tabs: [
          { path: HOME_TAB.path, title: 'wrong-title', closable: HOME_TAB.closable }
        ],
        activePath: HOME_TAB.path
      })
    )
    setActivePinia(createPinia())

    const invalidHomeTabStore = useLayoutStore()

    expect(invalidHomeTabStore.tabs).toEqual([HOME_TAB])
    expect(invalidHomeTabStore.activePath).toBe(HOME_TAB.path)

    localStorage.setItem(LAYOUT_STORAGE_KEY, '{invalid-json')
    setActivePinia(createPinia())

    const fallbackStore = useLayoutStore()

    expect(fallbackStore.tabs).toEqual([HOME_TAB])
    expect(fallbackStore.collapsed).toBe(false)
    expect(fallbackStore.activePath).toBe(HOME_TAB.path)
  })
})
