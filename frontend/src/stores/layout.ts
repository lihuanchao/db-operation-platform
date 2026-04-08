import { ref } from 'vue'
import { defineStore } from 'pinia'

export type LayoutTab = {
  path: string
  title: string
  closable: boolean
}

type LayoutStorageState = {
  collapsed: boolean
  tabs: LayoutTab[]
  activePath: string
  openedMenus?: string[]
}

export const HOME_TAB: LayoutTab = {
  path: '/optimization-tasks',
  title: 'SQL智能建议',
  closable: false
}

export const LAYOUT_STORAGE_KEY = 'dbops-layout-state-v1'

function cloneTab(tab: LayoutTab): LayoutTab {
  return {
    path: tab.path,
    title: tab.title,
    closable: tab.closable
  }
}

function isLayoutTab(value: unknown): value is LayoutTab {
  return !!value
    && typeof value === 'object'
    && typeof (value as LayoutTab).path === 'string'
    && typeof (value as LayoutTab).title === 'string'
    && typeof (value as LayoutTab).closable === 'boolean'
}

function isValidState(value: unknown): value is LayoutStorageState {
  if (!value || typeof value !== 'object') {
    return false
  }

  const state = value as Partial<LayoutStorageState>
  if (typeof state.collapsed !== 'boolean' || !Array.isArray(state.tabs) || typeof state.activePath !== 'string') {
    return false
  }

  if (state.tabs.length === 0 || !isLayoutTab(state.tabs[0])) {
    return false
  }

  if (
    state.tabs[0].path !== HOME_TAB.path
    || state.tabs[0].title !== HOME_TAB.title
    || state.tabs[0].closable !== HOME_TAB.closable
  ) {
    return false
  }

  const seenPaths = new Set<string>()
  for (const tab of state.tabs) {
    if (!isLayoutTab(tab) || seenPaths.has(tab.path)) {
      return false
    }
    seenPaths.add(tab.path)
  }

  return seenPaths.has(state.activePath)
}

export const useLayoutStore = defineStore('layout', () => {
  const collapsed = ref(false)
  const tabs = ref<LayoutTab[]>([cloneTab(HOME_TAB)])
  const activePath = ref(HOME_TAB.path)
  const openedMenus = ref<string[]>([])

  function persistToStorage() {
    try {
      localStorage.setItem(
        LAYOUT_STORAGE_KEY,
        JSON.stringify({
          collapsed: collapsed.value,
          tabs: tabs.value,
          activePath: activePath.value,
          openedMenus: openedMenus.value
        })
      )
    } catch {
      // Ignore storage write failures.
    }
  }

  function resetToHomeTab() {
    collapsed.value = false
    tabs.value = [cloneTab(HOME_TAB)]
    activePath.value = HOME_TAB.path
    openedMenus.value = []
    persistToStorage()
  }

  function hydrateFromStorage() {
    try {
      const rawState = localStorage.getItem(LAYOUT_STORAGE_KEY)
      if (!rawState) {
        resetToHomeTab()
        return
      }

      const parsedState: unknown = JSON.parse(rawState)
      if (!isValidState(parsedState)) {
        resetToHomeTab()
        return
      }

      collapsed.value = parsedState.collapsed
      tabs.value = parsedState.tabs.map(cloneTab)
      activePath.value = parsedState.activePath
      openedMenus.value = Array.isArray(parsedState.openedMenus)
        ? parsedState.openedMenus.filter((item): item is string => typeof item === 'string')
        : []
    } catch {
      resetToHomeTab()
    }
  }

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
    persistToStorage()
  }

  function activateTab(path: string) {
    if (!tabs.value.some((tab) => tab.path === path)) {
      return
    }

    activePath.value = path
    persistToStorage()
  }

  function openTab(path: string, title: string, closable = true) {
    const existingTab = tabs.value.find((item) => item.path === path)
    if (existingTab) {
      activePath.value = existingTab.path
      persistToStorage()
      return
    }

    const tab = path === HOME_TAB.path
      ? cloneTab(HOME_TAB)
      : {
          path,
          title,
          closable
        }

    tabs.value = [...tabs.value, cloneTab(tab)]
    activePath.value = path
    persistToStorage()
  }

  function syncByRoute(path: string, title = path) {
    if (path === HOME_TAB.path) {
      activateTab(path)
      return
    }

    openTab(path, title, true)
  }

  function closeTab(path: string) {
    const tabIndex = tabs.value.findIndex((tab) => tab.path === path)
    if (tabIndex === -1 || !tabs.value[tabIndex].closable) {
      return
    }

    tabs.value = tabs.value.filter((tab) => tab.path !== path)
    if (activePath.value === path) {
      activePath.value = HOME_TAB.path
    }
    persistToStorage()
  }

  function setOpenedMenus(menus: string[]) {
    openedMenus.value = Array.from(
      new Set(
        menus.filter((item) => item === 'admin')
      )
    )
    persistToStorage()
  }

  hydrateFromStorage()

  return {
    collapsed,
    tabs,
    activePath,
    openedMenus,
    toggleCollapsed,
    activateTab,
    openTab,
    syncByRoute,
    closeTab,
    setOpenedMenus,
    hydrateFromStorage,
    persistToStorage,
    resetToHomeTab
  }
})
