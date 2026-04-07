# Main Layout Topbar Tabs Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现固定顶栏、可收缩左侧导航、可持久化功能标签栏（首页不可关闭，关闭当前标签固定回首页），并接入用户提供 Logo。

**Architecture:** 保持现有路由结构和业务页面不变，仅在 `AppLayout + Sidebar + layout store` 三层完成壳层改造。使用 Pinia 管理侧栏收缩与标签状态，路由变化驱动标签同步，`localStorage` 持久化恢复。通过 store 单测 + 布局组件单测覆盖关键交互，避免回归。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Pinia, Vue Router, Element Plus, Vitest, Vue Test Utils

---

## File Structure

- Create: `frontend/src/stores/layout.ts`
  - 职责：管理 `collapsed / tabs / activePath`，封装持久化与标签操作规则。
- Create: `frontend/src/stores/layout.spec.ts`
  - 职责：验证 `layout` store 的首页固定、关闭行为、持久化恢复逻辑。
- Create: `frontend/src/components/Layout/AppLayout.spec.ts`
  - 职责：验证顶栏渲染、侧栏收缩入口、标签切换/关闭、退出登录流程。
- Create: `frontend/src/components/Layout/Sidebar.spec.ts`
  - 职责：验证侧栏在收缩态下工作、菜单点击导航、权限菜单渲染。
- Modify: `frontend/src/components/Layout/AppLayout.vue`
  - 职责：新增固定顶栏 + 标签栏 + 主体区骨架，接入 `layout store` 与路由同步。
- Modify: `frontend/src/components/Layout/Sidebar.vue`
  - 职责：接入收缩状态、移除旧用户区、优化图标与收缩交互细节。
- Create: `frontend/src/assets/sinotruk-logo.png`
  - 职责：顶部品牌 Logo（由用户上传图接入）。

## Task 1: Build Layout Store With Persistence (TDD)

**Files:**
- Create: `frontend/src/stores/layout.spec.ts`
- Create: `frontend/src/stores/layout.ts`
- Test: `frontend/src/stores/layout.spec.ts`

- [ ] **Step 1: Write the failing store test first**

`frontend/src/stores/layout.spec.ts`

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLayoutStore, HOME_TAB, LAYOUT_STORAGE_KEY } from './layout'

describe('layout store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('starts with only home tab when storage is empty', () => {
    const store = useLayoutStore()

    expect(store.collapsed).toBe(false)
    expect(store.activePath).toBe(HOME_TAB.path)
    expect(store.tabs).toEqual([HOME_TAB])
  })

  it('opens tab once and activates existing tab without duplicate', () => {
    const store = useLayoutStore()

    store.openTab('/slow-sqls', '慢SQL列表')
    store.openTab('/slow-sqls', '慢SQL列表')

    expect(store.tabs).toEqual([HOME_TAB, { path: '/slow-sqls', title: '慢SQL列表', closable: true }])
    expect(store.activePath).toBe('/slow-sqls')
  })

  it('does not close home tab and goes home when closing active non-home tab', () => {
    const store = useLayoutStore()

    store.openTab('/connections', '连接管理')
    store.closeTab(HOME_TAB.path)
    expect(store.tabs).toEqual([HOME_TAB, { path: '/connections', title: '连接管理', closable: true }])

    store.closeTab('/connections')
    expect(store.tabs).toEqual([HOME_TAB])
    expect(store.activePath).toBe(HOME_TAB.path)
  })

  it('hydrates valid data and falls back to home when payload is invalid', () => {
    localStorage.setItem(
      LAYOUT_STORAGE_KEY,
      JSON.stringify({
        collapsed: true,
        activePath: '/slow-sqls',
        tabs: [
          HOME_TAB,
          { path: '/slow-sqls', title: '慢SQL列表', closable: true }
        ]
      })
    )

    const store = useLayoutStore()
    expect(store.collapsed).toBe(true)
    expect(store.activePath).toBe('/slow-sqls')
    expect(store.tabs).toHaveLength(2)

    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify({ collapsed: true, tabs: 'broken' }))
    store.hydrateFromStorage()
    expect(store.tabs).toEqual([HOME_TAB])
    expect(store.activePath).toBe(HOME_TAB.path)
  })
})
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd frontend && npm test -- src/stores/layout.spec.ts
```

Expected: FAIL（`Cannot find module './layout'` 或导出不存在）。

- [ ] **Step 3: Write minimal store implementation**

`frontend/src/stores/layout.ts`

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface LayoutTab {
  path: string
  title: string
  closable: boolean
}

export const HOME_TAB: LayoutTab = {
  path: '/optimization-tasks',
  title: 'SQL优化建议',
  closable: false
}

export const LAYOUT_STORAGE_KEY = 'dbops-layout-state-v1'

function isValidTab(item: unknown): item is LayoutTab {
  if (!item || typeof item !== 'object') return false
  const tab = item as Record<string, unknown>
  return (
    typeof tab.path === 'string' &&
    typeof tab.title === 'string' &&
    typeof tab.closable === 'boolean'
  )
}

export const useLayoutStore = defineStore('layout', () => {
  const collapsed = ref(false)
  const tabs = ref<LayoutTab[]>([HOME_TAB])
  const activePath = ref(HOME_TAB.path)

  function persistToStorage() {
    localStorage.setItem(
      LAYOUT_STORAGE_KEY,
      JSON.stringify({
        collapsed: collapsed.value,
        tabs: tabs.value,
        activePath: activePath.value
      })
    )
  }

  function resetToHomeTab() {
    tabs.value = [HOME_TAB]
    activePath.value = HOME_TAB.path
    collapsed.value = false
    persistToStorage()
  }

  function hydrateFromStorage() {
    const raw = localStorage.getItem(LAYOUT_STORAGE_KEY)
    if (!raw) return

    try {
      const parsed = JSON.parse(raw) as Record<string, unknown>
      const parsedTabs = Array.isArray(parsed.tabs) ? parsed.tabs.filter(isValidTab) : []
      const hasHome = parsedTabs.some((tab) => tab.path === HOME_TAB.path)
      tabs.value = hasHome ? parsedTabs : [HOME_TAB, ...parsedTabs]
      if (!tabs.value.length) tabs.value = [HOME_TAB]

      activePath.value =
        typeof parsed.activePath === 'string' && tabs.value.some((tab) => tab.path === parsed.activePath)
          ? parsed.activePath
          : HOME_TAB.path

      collapsed.value = Boolean(parsed.collapsed)
    } catch {
      resetToHomeTab()
    }
  }

  function toggleCollapsed() {
    collapsed.value = !collapsed.value
    persistToStorage()
  }

  function activateTab(path: string) {
    if (!tabs.value.some((tab) => tab.path === path)) return
    activePath.value = path
    persistToStorage()
  }

  function openTab(path: string, title: string, closable = true) {
    const existing = tabs.value.find((tab) => tab.path === path)
    if (existing) {
      existing.title = title
      existing.closable = path === HOME_TAB.path ? false : closable
      activePath.value = path
      persistToStorage()
      return
    }

    tabs.value.push({
      path,
      title,
      closable: path === HOME_TAB.path ? false : closable
    })
    activePath.value = path
    persistToStorage()
  }

  function syncByRoute(path: string, title: string, closable = true) {
    openTab(path, title, closable)
  }

  function closeTab(path: string) {
    if (path === HOME_TAB.path) return
    const nextTabs = tabs.value.filter((tab) => tab.path !== path)
    tabs.value = nextTabs.length ? nextTabs : [HOME_TAB]
    if (activePath.value === path) {
      activePath.value = HOME_TAB.path
    }
    persistToStorage()
  }

  hydrateFromStorage()

  return {
    collapsed,
    tabs,
    activePath,
    toggleCollapsed,
    activateTab,
    openTab,
    syncByRoute,
    closeTab,
    hydrateFromStorage,
    persistToStorage,
    resetToHomeTab
  }
})
```

- [ ] **Step 4: Run test to verify GREEN**

Run:

```bash
cd frontend && npm test -- src/stores/layout.spec.ts
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/layout.ts frontend/src/stores/layout.spec.ts
git commit -m "feat: add layout ui state store with tab persistence"
```

## Task 2: Add Topbar + Tabs Shell In AppLayout (TDD)

**Files:**
- Create: `frontend/src/components/Layout/AppLayout.spec.ts`
- Modify: `frontend/src/components/Layout/AppLayout.vue`
- Create: `frontend/src/assets/sinotruk-logo.png`
- Test: `frontend/src/components/Layout/AppLayout.spec.ts`

- [ ] **Step 1: Write failing AppLayout test**

`frontend/src/components/Layout/AppLayout.spec.ts`

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import { ref } from 'vue'
import { useLayoutStore, HOME_TAB } from '@/stores/layout'

const pushMock = vi.fn()
const replaceMock = vi.fn()
const logoutMock = vi.fn()

const routePath = ref('/optimization-tasks')

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock
  }),
  useRoute: () => ({
    get path() {
      return routePath.value
    }
  })
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    user: { real_name: '张三' },
    logout: logoutMock
  })
}))

import AppLayout from './AppLayout.vue'

describe('AppLayout', () => {
  function mountLayout() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(AppLayout, {
      global: {
        plugins: [pinia, ElementPlus],
        stubs: {
          Sidebar: { template: '<div class="sidebar-stub" />' }
        }
      },
      slots: {
        default: '<div class="slot-body">content</div>'
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
    routePath.value = '/optimization-tasks'
    localStorage.clear()
  })

  it('renders topbar branding and username', () => {
    const wrapper = mountLayout()
    expect(wrapper.find('.brand-logo').exists()).toBe(true)
    expect(wrapper.text()).toContain('数据库运维系统')
    expect(wrapper.text()).toContain('张三')
  })

  it('toggles sidebar collapse and routes on tab click', async () => {
    const wrapper = mountLayout()
    const store = useLayoutStore()

    await wrapper.find('button.layout-collapse-btn').trigger('click')
    expect(store.collapsed).toBe(true)

    store.openTab('/slow-sqls', '慢SQL列表', true)
    await wrapper.vm.$nextTick()
    await wrapper.find('.layout-tab[data-path="/slow-sqls"]').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/slow-sqls')
  })

  it('closes active non-home tab and always returns home', async () => {
    const wrapper = mountLayout()
    const store = useLayoutStore()
    store.openTab('/connections', '连接管理', true)
    await wrapper.vm.$nextTick()

    await wrapper.find('button.layout-tab-close[data-path="/connections"]').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/optimization-tasks')
    expect(store.tabs).toEqual([HOME_TAB])
    expect(store.activePath).toBe('/optimization-tasks')
  })

  it('keeps home tab non-closable', async () => {
    const wrapper = mountLayout()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('button.layout-tab-close[data-path="/optimization-tasks"]').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd frontend && npm test -- src/components/Layout/AppLayout.spec.ts
```

Expected: FAIL（缺少顶栏、标签栏与测试选择器）。

- [ ] **Step 3: Add logo asset and AppLayout implementation**

Run:

```bash
cp /data/claude-project/画板.png /data/claude-project/frontend/src/assets/sinotruk-logo.png
```

`frontend/src/components/Layout/AppLayout.vue`

```vue
<template>
  <div class="app-layout">
    <header class="topbar">
      <div class="topbar-left">
        <img :src="sinotrukLogo" alt="SINOTRUK" class="brand-logo" />
        <div class="brand-name">数据库运维系统</div>
        <button class="layout-collapse-btn icon-btn" @click="layoutStore.toggleCollapsed()">
          <el-icon><Fold v-if="!layoutStore.collapsed" /><Expand v-else /></el-icon>
        </button>
      </div>

      <div class="topbar-right">
        <el-dropdown trigger="click" @command="handleUserCommand">
          <button class="user-trigger">
            {{ authStore.user?.real_name || '未登录' }}
            <el-icon><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div class="layout-body">
      <el-aside :width="layoutStore.collapsed ? '64px' : '220px'" class="layout-aside">
        <Sidebar />
      </el-aside>

      <section class="layout-main" :style="{ marginLeft: layoutStore.collapsed ? '64px' : '220px' }">
        <div class="tabs-bar">
          <div
            v-for="tab in layoutStore.tabs"
            :key="tab.path"
            class="layout-tab"
            :class="{ active: tab.path === layoutStore.activePath }"
            :data-path="tab.path"
            @click="goTab(tab.path)"
          >
            <span>{{ tab.title }}</span>
            <button
              v-if="tab.closable"
              class="layout-tab-close"
              :data-path="tab.path"
              @click.stop="closeTab(tab.path)"
            >
              <el-icon><Close /></el-icon>
            </button>
          </div>
        </div>

        <main class="main-scroll">
          <div class="main-content">
            <slot />
          </div>
        </main>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Close, Expand, Fold } from '@element-plus/icons-vue'
import Sidebar from './Sidebar.vue'
import { useLayoutStore, HOME_TAB } from '@/stores/layout'
import { useAuthStore } from '@/stores/auth'
import { MENU_ITEMS } from '@/auth/access'
import sinotrukLogo from '@/assets/sinotruk-logo.png'

const router = useRouter()
const route = useRoute()
const layoutStore = useLayoutStore()
const authStore = useAuthStore()

function resolveMenu(path: string) {
  return MENU_ITEMS.find((item) =>
    item.matchPrefixes.some((prefix) => path === prefix || path.startsWith(prefix))
  )
}

function syncFromRoute(path: string) {
  const matched = resolveMenu(path)
  if (!matched) {
    layoutStore.syncByRoute(HOME_TAB.path, HOME_TAB.title, false)
    return
  }
  layoutStore.syncByRoute(matched.path, matched.label, matched.path !== HOME_TAB.path)
}

function goTab(path: string) {
  layoutStore.activateTab(path)
  router.push(path)
}

function closeTab(path: string) {
  layoutStore.closeTab(path)
  router.push(HOME_TAB.path)
}

async function handleUserCommand(command: string) {
  if (command !== 'logout') return
  layoutStore.resetToHomeTab()
  await authStore.logout()
  router.replace('/login')
}

watch(
  () => route.path,
  (path) => syncFromRoute(path),
  { immediate: true }
)
</script>

<style scoped>
.app-layout {
  width: 100%;
  min-height: 100vh;
  background: #eef2f8;
}

.topbar {
  position: fixed;
  inset: 0 0 auto 0;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  background: #1677d8;
  color: #fff;
  z-index: 50;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  height: 28px;
  width: auto;
  display: block;
}

.brand-name {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.icon-btn {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  cursor: pointer;
}

.user-trigger {
  border: none;
  background: transparent;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.layout-body {
  display: flex;
  padding-top: 56px;
  min-height: 100vh;
}

.layout-aside {
  position: fixed;
  top: 56px;
  left: 0;
  bottom: 0;
  transition: width 0.2s ease;
}

.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  transition: margin-left 0.2s ease;
}

.tabs-bar {
  height: 46px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  background: #f7f9fd;
  border-bottom: 1px solid #e2e8f2;
  overflow-x: auto;
}

.layout-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 10px;
  border: 1px solid #d8e1ee;
  border-radius: 8px;
  background: #fff;
  color: #3b4a62;
  cursor: pointer;
}

.layout-tab.active {
  border-color: #1677d8;
  color: #1677d8;
}

.layout-tab-close {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.main-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.main-content {
  background: #fff;
  border-radius: 12px;
  padding: 18px;
  min-height: calc(100vh - 56px - 46px - 32px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}
</style>
```

- [ ] **Step 4: Run test to verify GREEN**

Run:

```bash
cd frontend && npm test -- src/components/Layout/AppLayout.spec.ts
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Layout/AppLayout.vue frontend/src/components/Layout/AppLayout.spec.ts frontend/src/assets/sinotruk-logo.png
git commit -m "feat: add fixed topbar and tab workspace shell"
```

## Task 3: Refactor Sidebar For Collapse + Icon Upgrade (TDD)

**Files:**
- Create: `frontend/src/components/Layout/Sidebar.spec.ts`
- Modify: `frontend/src/components/Layout/Sidebar.vue`
- Test: `frontend/src/components/Layout/Sidebar.spec.ts`

- [ ] **Step 1: Write failing Sidebar test**

`frontend/src/components/Layout/Sidebar.spec.ts`

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { createPinia, setActivePinia } from 'pinia'
import { useLayoutStore } from '@/stores/layout'

const pushMock = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  useRoute: () => ({ path: '/optimization-tasks' })
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    menus: [
      { path: '/optimization-tasks', label: 'SQL优化建议' },
      { path: '/slow-sqls', label: '慢SQL列表' },
      { path: '/connections', label: '连接管理' },
      { path: '/archive-tasks', label: '归档任务' },
      { path: '/execution-logs', label: '执行日志' },
      { path: '/users', label: '用户管理' },
      { path: '/roles', label: '角色管理' },
      { path: '/permissions', label: '权限管理' }
    ]
  })
}))

import Sidebar from './Sidebar.vue'

describe('Sidebar', () => {
  function mountView() {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(Sidebar, {
      global: {
        plugins: [pinia, ElementPlus]
      }
    })
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders menus and navigates by click', async () => {
    const wrapper = mountView()
    expect(wrapper.text()).toContain('SQL优化建议')
    await wrapper.find('li[data-path="/slow-sqls"]').trigger('click')
    expect(pushMock).toHaveBeenCalledWith('/slow-sqls')
  })

  it('passes collapse state into el-menu', async () => {
    const wrapper = mountView()
    const store = useLayoutStore()
    store.toggleCollapsed()
    await wrapper.vm.$nextTick()
    const menu = wrapper.findComponent({ name: 'ElMenu' })
    expect(menu.props('collapse')).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd frontend && npm test -- src/components/Layout/Sidebar.spec.ts
```

Expected: FAIL（当前 Sidebar 无 `data-path` 与收缩集成）。

- [ ] **Step 3: Implement Sidebar collapse integration and icons**

`frontend/src/components/Layout/Sidebar.vue`

```vue
<template>
  <div class="sidebar" :class="{ collapsed: layoutStore.collapsed }">
    <el-menu
      :default-active="activeMenu"
      :default-openeds="layoutStore.collapsed ? [] : ['archive', 'admin']"
      :collapse="layoutStore.collapsed"
      class="sidebar-menu"
      background-color="#ffffff"
      text-color="#1f2d3d"
      active-text-color="#1677d8"
    >
      <el-menu-item
        v-if="hasMenu('/optimization-tasks')"
        index="/optimization-tasks"
        data-path="/optimization-tasks"
        :title="layoutStore.collapsed ? 'SQL优化建议' : undefined"
        @click="navigate('/optimization-tasks')"
      >
        <el-icon><MagicStick /></el-icon>
        <span>SQL优化建议</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/slow-sqls')"
        index="/slow-sqls"
        data-path="/slow-sqls"
        :title="layoutStore.collapsed ? '慢SQL列表' : undefined"
        @click="navigate('/slow-sqls')"
      >
        <el-icon><DataLine /></el-icon>
        <span>慢SQL列表</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/connections')"
        index="/connections"
        data-path="/connections"
        :title="layoutStore.collapsed ? '连接管理' : undefined"
        @click="navigate('/connections')"
      >
        <el-icon><Link /></el-icon>
        <span>连接管理</span>
      </el-menu-item>

      <el-sub-menu v-if="showArchive" index="archive">
        <template #title>
          <el-icon><FolderOpened /></el-icon>
          <span>归档管理</span>
        </template>
        <el-menu-item
          v-if="hasMenu('/archive-tasks')"
          index="/archive-tasks"
          data-path="/archive-tasks"
          @click="navigate('/archive-tasks')"
        >
          <el-icon><List /></el-icon>
          <span>归档任务</span>
        </el-menu-item>
        <el-menu-item
          v-if="hasMenu('/execution-logs')"
          index="/execution-logs"
          data-path="/execution-logs"
          @click="navigate('/execution-logs')"
        >
          <el-icon><Document /></el-icon>
          <span>执行日志</span>
        </el-menu-item>
      </el-sub-menu>

      <el-sub-menu v-if="showAdmin" index="admin">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </template>
        <el-menu-item v-if="hasMenu('/users')" index="/users" data-path="/users" @click="navigate('/users')">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item v-if="hasMenu('/roles')" index="/roles" data-path="/roles" @click="navigate('/roles')">
          <el-icon><Management /></el-icon>
          <span>角色管理</span>
        </el-menu-item>
        <el-menu-item
          v-if="hasMenu('/permissions')"
          index="/permissions"
          data-path="/permissions"
          @click="navigate('/permissions')"
        >
          <el-icon><Lock /></el-icon>
          <span>权限管理</span>
        </el-menu-item>
      </el-sub-menu>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DataLine,
  Setting,
  FolderOpened,
  Document,
  List,
  MagicStick,
  Management,
  Lock,
  User,
  Link
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useLayoutStore } from '@/stores/layout'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const layoutStore = useLayoutStore()

const activeMenu = computed(() => {
  if (route.path.startsWith('/optimization-tasks')) return '/optimization-tasks'
  if (route.path.startsWith('/slow-sql')) return '/slow-sqls'
  if (route.path.startsWith('/users')) return '/users'
  if (route.path.startsWith('/roles')) return '/roles'
  if (route.path.startsWith('/permissions')) return '/permissions'
  return route.path
})

const visiblePaths = computed(() => new Set(authStore.menus.map((item) => item.path)))
const showArchive = computed(() => hasMenu('/archive-tasks') || hasMenu('/execution-logs'))
const showAdmin = computed(() => hasMenu('/users') || hasMenu('/roles') || hasMenu('/permissions'))

function hasMenu(path: string) {
  return visiblePaths.value.has(path)
}

function navigate(path: string) {
  router.push(path)
}
</script>

<style scoped>
.sidebar {
  height: 100%;
  background: #fff;
  border-right: 1px solid #e4eaf3;
  overflow: auto;
}

.sidebar-menu {
  border: none;
}

:deep(.el-menu-item.is-active) {
  background: #e8f2ff;
}
</style>
```

- [ ] **Step 4: Run test to verify GREEN**

Run:

```bash
cd frontend && npm test -- src/components/Layout/Sidebar.spec.ts
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Layout/Sidebar.vue frontend/src/components/Layout/Sidebar.spec.ts
git commit -m "feat: support collapsible sidebar with refreshed icons"
```

## Task 4: Integrate Full Layout Regression And Ship

**Files:**
- Modify: `frontend/src/components/Layout/AppLayout.vue`
- Modify: `frontend/src/components/Layout/Sidebar.vue`
- Create/Modify: `frontend/src/stores/layout.ts`, specs
- Test: full frontend tests

- [ ] **Step 1: Run focused layout tests**

Run:

```bash
cd frontend && npm test -- src/stores/layout.spec.ts src/components/Layout/AppLayout.spec.ts src/components/Layout/Sidebar.spec.ts
```

Expected: PASS。

- [ ] **Step 2: Run full frontend tests**

Run:

```bash
cd frontend && npm test
```

Expected: PASS（现有 21+ 测试全绿，新增测试也全绿）。

- [ ] **Step 3: Run production build**

Run:

```bash
cd frontend && npm run build
```

Expected: build success（允许现有 chunk warning）。

- [ ] **Step 4: Final commit**

```bash
git add frontend/src/components/Layout/AppLayout.vue frontend/src/components/Layout/Sidebar.vue frontend/src/stores/layout.ts frontend/src/stores/layout.spec.ts frontend/src/components/Layout/AppLayout.spec.ts frontend/src/components/Layout/Sidebar.spec.ts frontend/src/assets/sinotruk-logo.png
git commit -m "feat: redesign app shell with topbar, tabs, and persisted navigation state"
```

## Self-Review

1. **Spec coverage check**
   - 固定顶栏（Logo/系统名/收缩/用户下拉）：Task 2。
   - 侧栏收缩仅图标：Task 3。
   - 功能标签打开/切换/关闭：Task 2 + Task 1。
   - 关闭当前标签固定回首页：Task 2（`closeTab -> router.push(home)`）。
   - 首页标签不可关闭：Task 1 + Task 2。
   - 刷新保留：Task 1（`localStorage` hydrate/persist）。
   - 图标优化：Task 3。
2. **Placeholder scan**
   - 无 `TBD/TODO`，所有命令、文件路径、关键代码已给出。
3. **Type consistency**
   - `LayoutTab` 结构与测试断言一致（`path/title/closable`）。
   - `HOME_TAB` 与首页不可关闭规则在 store 和组件一致。
