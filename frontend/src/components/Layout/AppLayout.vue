<template>
  <div class="app-layout">
    <!-- 左侧边栏 -->
    <aside class="layout-aside" :class="{ 'is-collapsed': layoutStore.collapsed }">
      <!-- Logo和系统名称 -->
      <div class="aside-header">
        <img :src="sinotrukLogo" alt="中国重汽" class="brand-logo" />
        <span v-if="!layoutStore.collapsed" class="brand-title">数据库运维平台</span>
      </div>

      <!-- 导航菜单 -->
      <div class="aside-nav">
        <Sidebar />
      </div>

      <!-- 收起按钮 -->
      <div class="aside-footer">
        <button class="collapse-btn" @click="layoutStore.toggleCollapsed()">
          <svg v-if="layoutStore.collapsed" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 5l7 7-7 7"/>
            <path d="M6 5l7 7-7 7"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 19l-7-7 7-7"/>
            <path d="M18 19l-7-7 7-7"/>
          </svg>
        </button>
      </div>
    </aside>

    <!-- 右侧内容区 -->
    <div class="layout-main">
      <!-- 顶部导航条 -->
      <header class="main-header">
        <div class="header-tabs">
          <div
            v-for="tab in layoutStore.tabs"
            :key="tab.path"
            class="header-tab"
            :class="{ 'is-active': layoutStore.activePath === tab.path }"
            @click="openTab(tab.path)"
          >
            <span class="tab-title">{{ tab.title }}</span>
            <button
              v-if="tab.closable"
              class="tab-close"
              @click.stop="closeTab(tab.path)"
            >
              ×
            </button>
          </div>
        </div>

        <!-- 用户信息 - 固定在最右侧 -->
        <div class="header-user">
          <div class="user-avatar">
            {{ userInitial }}
          </div>
          <div class="user-info">
            <div class="user-name">{{ userName }}</div>
            <div class="user-role">{{ userRole }}</div>
          </div>
          <button class="logout-btn" @click="handleLogout">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </div>
      </header>

      <!-- 内容区域 -->
      <main class="main-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MENU_ITEMS } from '@/auth/access'
import sinotrukLogo from '@/assets/sinotruk-logo.png'
import Sidebar from './Sidebar.vue'
import { HOME_TAB, useLayoutStore } from '@/stores/layout'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const layoutStore = useLayoutStore()
const authStore = useAuthStore()

const ROLE_LABELS = new Set(['管理员', '普通用户'])

const userName = computed(() => {
  const realName = (authStore.user?.real_name || '').trim()
  const employeeNo = (authStore.user?.employee_no || '').trim()

  if (realName && !ROLE_LABELS.has(realName)) {
    return realName
  }

  if (employeeNo) {
    return employeeNo
  }

  return '未登录'
})

const userRole = computed(() => {
  return authStore.user?.role_name || '用户'
})

const userInitial = computed(() => {
  const name = userName.value
  return name.charAt(name.length - 1).toUpperCase()
})

function resolveTabTitle(path: string) {
  const matchedMenu = MENU_ITEMS.find((item) => {
    if (item.path === path) {
      return true
    }
    return item.matchPrefixes.some((prefix) => path === prefix || path.startsWith(prefix))
  })
  return matchedMenu?.label ?? path
}

function shouldSyncRouteToTabs(path: string) {
  return path !== '/login'
}

async function openTab(path: string) {
  layoutStore.activateTab(path)
  await router.push(path)
}

async function closeTab(path: string) {
  const isActiveTab = layoutStore.activePath === path
  layoutStore.closeTab(path)
  if (isActiveTab) {
    await router.push(HOME_TAB.path)
  }
}

async function handleLogout() {
  layoutStore.resetToHomeTab()
  await authStore.logout()
  await router.replace('/login')
}

watch(
  () => route.path,
  (path) => {
    if (!shouldSyncRouteToTabs(path)) {
      return
    }
    layoutStore.syncByRoute(path, resolveTabTitle(path))
  },
  { immediate: true }
)
</script>

<style scoped>
.app-layout {
  width: 100%;
  height: 100vh;
  display: flex;
  overflow: hidden;
  background: #f1f5f9;
}

/* 左侧边栏 */
.layout-aside {
  width: 220px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  transition: width 0.25s ease;
  flex-shrink: 0;
  overflow: hidden;
}

.layout-aside.is-collapsed {
  width: 64px;
}

/* 收起状态下确保内容居中 */
.layout-aside.is-collapsed .aside-header {
  justify-content: center;
  padding: 0;
}

.layout-aside.is-collapsed .brand-logo {
  margin: 0;
}

/* 边栏头部 */
.aside-header {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  border-bottom: 1px solid #f1f5f9;
  flex-shrink: 0;
}

.brand-logo {
  width: 32px;
  height: 32px;
  object-fit: contain;
  flex-shrink: 0;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
}

.layout-aside.is-collapsed .brand-title {
  display: none;
}

/* 导航菜单 */
.aside-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 0;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.aside-nav::-webkit-scrollbar {
  display: none;
}

/* 边栏底部 */
.aside-footer {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-top: 1px solid #f1f5f9;
  flex-shrink: 0;
}

.collapse-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: #f8fafc;
  color: #64748b;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.collapse-btn:hover {
  background: #e2e8f0;
  color: #334155;
}

.collapse-btn svg {
  width: 18px;
  height: 18px;
}

/* 右侧内容区 */
.layout-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

/* 顶部导航条 */
.main-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 16px;
  flex-shrink: 0;
}

.header-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  padding: 4px 0;
}

.header-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.header-tab:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.header-tab.is-active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1d4ed8;
}

.tab-title {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  white-space: nowrap;
}

.header-tab.is-active .tab-title {
  color: #1d4ed8;
  font-weight: 600;
}

.tab-close {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.tab-close:hover {
  background: #e2e8f0;
  color: #475569;
}

/* 用户信息区 */
.header-user {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-left: 16px;
  margin-left: 16px;
  border-left: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.user-avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.user-role {
  font-size: 11px;
  color: #64748b;
}

.logout-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: #fef2f2;
  color: #dc2626;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.logout-btn:hover {
  background: #fee2e2;
}

.logout-btn svg {
  width: 18px;
  height: 18px;
}

/* 内容区域 */
.main-content {
  flex: 1;
  min-height: 0;
  padding: 16px;
  overflow: auto;
}
</style>
