<template>
  <div class="sidebar" :class="{ 'is-collapsed': layoutStore.collapsed }">
    <el-menu
      ref="menuRef"
      :collapse="layoutStore.collapsed"
      :collapse-transition="false"
      :default-active="activeMenu"
      :default-openeds="layoutStore.openedMenus"
      class="sidebar-menu"
      background-color="#f8fafc"
      text-color="#475569"
      active-text-color="#1d4ed8"
      unique-opened
      @open="handleMenuOpen"
      @close="handleMenuClose"
    >
      <el-menu-item
        v-if="hasMenu('/optimization-tasks')"
        index="/optimization-tasks"
        data-path="/optimization-tasks"
        @click="navigate('/optimization-tasks')"
      >
        <el-icon class="menu-icon-svg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
          </svg>
        </el-icon>
        <span class="menu-label">SQL优化</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/sql-audit')"
        index="/sql-audit"
        data-path="/sql-audit"
        @click="navigate('/sql-audit')"
      >
        <el-icon class="menu-icon-svg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </el-icon>
        <span class="menu-label">SQL审核</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/slow-sqls')"
        index="/slow-sqls"
        data-path="/slow-sqls"
        @click="navigate('/slow-sqls')"
      >
        <el-icon class="menu-icon-svg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </el-icon>
        <span class="menu-label">SQL巡检</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/sql-throttle/rules')"
        index="/sql-throttle/rules"
        data-path="/sql-throttle/rules"
        @click="navigate('/sql-throttle/rules')"
      >
        <el-icon class="menu-icon-svg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 5h16M4 12h16M4 19h10"/>
            <circle cx="18" cy="19" r="2"/>
          </svg>
        </el-icon>
        <span class="menu-label">SQL限流</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/archive-tasks')"
        index="/archive-tasks"
        data-path="/archive-tasks"
        @click="navigate('/archive-tasks')"
      >
        <el-icon class="menu-icon-svg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="21 8 21 21 3 21 3 8"/>
            <rect x="1" y="3" width="22" height="5"/>
            <line x1="10" y1="12" x2="14" y2="12"/>
          </svg>
        </el-icon>
        <span class="menu-label">归档任务</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/flashback-tasks')"
        index="/flashback-tasks"
        data-path="/flashback-tasks"
        @click="navigate('/flashback-tasks')"
      >
        <el-icon class="menu-icon-svg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
          </svg>
        </el-icon>
        <span class="menu-label">数据闪回</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/execution-logs')"
        index="/execution-logs"
        data-path="/execution-logs"
        @click="navigate('/execution-logs')"
      >
        <el-icon class="menu-icon-svg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
        </el-icon>
        <span class="menu-label">执行日志</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/connections')"
        index="/connections"
        data-path="/connections"
        @click="navigate('/connections')"
      >
        <el-icon class="menu-icon-svg">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </el-icon>
        <span class="menu-label">连接管理</span>
      </el-menu-item>

      <el-sub-menu v-if="showAdmin" index="admin">
        <template #title>
          <el-icon class="menu-icon-svg">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="16" rx="2"/>
              <path d="M8 8h8M8 12h5M8 16h3"/>
            </svg>
          </el-icon>
          <span class="menu-label">系统管理</span>
        </template>

        <el-menu-item
          v-if="hasMenu('/users')"
          index="/users"
          data-path="/users"
          @click="navigate('/users')"
        >
          <el-icon class="menu-icon-svg menu-icon-svg--sub">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21a8 8 0 0 0-16 0"/>
              <circle cx="12" cy="8" r="4"/>
            </svg>
          </el-icon>
          <span class="menu-label">用户管理</span>
        </el-menu-item>

        <el-menu-item
          v-if="hasMenu('/roles')"
          index="/roles"
          data-path="/roles"
          @click="navigate('/roles')"
        >
          <el-icon class="menu-icon-svg menu-icon-svg--sub">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="7" r="3"/>
              <path d="M5 21v-2a4 4 0 0 1 4-4h6a4 4 0 0 1 4 4v2"/>
              <path d="M4 11h3M17 11h3"/>
            </svg>
          </el-icon>
          <span class="menu-label">角色管理</span>
        </el-menu-item>

        <el-menu-item
          v-if="hasMenu('/permissions')"
          index="/permissions"
          data-path="/permissions"
          @click="navigate('/permissions')"
        >
          <el-icon class="menu-icon-svg menu-icon-svg--sub">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 3l7 4v5c0 5-3.5 8-7 9-3.5-1-7-4-7-9V7l7-4z"/>
              <path d="M9 12l2 2 4-4"/>
            </svg>
          </el-icon>
          <span class="menu-label">权限管理</span>
        </el-menu-item>
      </el-sub-menu>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useLayoutStore } from '@/stores/layout'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const layoutStore = useLayoutStore()
const menuRef = ref<{ close?: (index: string) => void } | null>(null)
let suppressAutoOpenUntil = 0

const activeMenu = computed(() => {
  if (route.path.startsWith('/optimization-tasks')) return '/optimization-tasks'
  if (route.path.startsWith('/sql-audit')) return '/sql-audit'
  if (route.path.startsWith('/slow-sql')) return '/slow-sqls'
  if (route.path.startsWith('/archive-tasks')) return '/archive-tasks'
  if (route.path.startsWith('/sql-throttle')) return '/sql-throttle/rules'
  if (route.path.startsWith('/flashback-tasks')) return '/flashback-tasks'
  if (route.path.startsWith('/users')) return '/users'
  if (route.path.startsWith('/roles')) return '/roles'
  if (route.path.startsWith('/permissions')) return '/permissions'
  return route.path
})

const visiblePaths = computed(() => new Set(authStore.menus.map((item) => item.path)))

const showAdmin = computed(() => hasMenu('/users') || hasMenu('/roles') || hasMenu('/permissions'))

function hasMenu(path: string) {
  return visiblePaths.value.has(path)
}

function navigate(path: string) {
  router.push(path)
}

watch(
  () => layoutStore.collapsed,
  async (collapsed) => {
    if (collapsed) return
    suppressAutoOpenUntil = Date.now() + 400
    await nextTick()
    layoutStore.setOpenedMenus([])
    menuRef.value?.close?.('admin')
    setTimeout(() => {
      menuRef.value?.close?.('admin')
    }, 220)
  }
)

function handleMenuOpen(index: string) {
  if (Date.now() < suppressAutoOpenUntil) {
    menuRef.value?.close?.(index)
    return
  }
  layoutStore.setOpenedMenus([...layoutStore.openedMenus, index])
}

function handleMenuClose(index: string) {
  layoutStore.setOpenedMenus(layoutStore.openedMenus.filter((item) => item !== index))
}
</script>

<style scoped>
.sidebar {
  min-height: 100vh;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
}

.sidebar-menu {
  border: none;
  border-right: none;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 100%;
}

/* 图标 */
.menu-icon-svg {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.menu-icon-svg svg {
  width: 18px;
  height: 18px;
  stroke-width: 1.8;
}

.menu-icon-svg--sub {
  width: 16px;
  height: 16px;
}

.menu-icon-svg--sub svg {
  width: 16px;
  height: 16px;
}

.menu-label {
  margin-left: 10px;
}

/* Element Plus 菜单样式覆盖 */
.sidebar-menu :deep(.el-menu-item),
.sidebar-menu :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  margin: 2px 8px;
  border-radius: 6px;
}

.sidebar-menu :deep(.el-menu-item) {
  color: #475569;
}

.sidebar-menu :deep(.el-menu-item:hover),
.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background: #f1f5f9;
  color: #1e293b;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
  position: relative;
}

.sidebar-menu :deep(.el-menu-item.is-active::before) {
  content: '';
  position: absolute;
  left: -8px;
  top: 10px;
  bottom: 10px;
  width: 3px;
  background: #3b82f6;
  border-radius: 0 2px 2px 0;
}

/* 收起状态下隐藏左侧指示器 */
.sidebar-menu.el-menu--collapse :deep(.el-menu-item.is-active::before) {
  display: none;
}

/* 收起状态仅显示图标 */
.sidebar-menu.el-menu--collapse :deep(.menu-label) {
  display: none;
}
</style>
