<template>
  <div class="sidebar" :class="{ 'is-collapsed': layoutStore.collapsed }">
    <el-menu
      ref="menuRef"
      :collapse="layoutStore.collapsed"
      :default-active="activeMenu"
      :default-openeds="layoutStore.openedMenus"
      class="sidebar-menu"
      background-color="#343a40"
      text-color="#fff"
      active-text-color="#fff"
      @open="handleMenuOpen"
      @close="handleMenuClose"
    >
      <el-menu-item
        v-if="hasMenu('/optimization-tasks')"
        index="/optimization-tasks"
        data-path="/optimization-tasks"
        @click="navigate('/optimization-tasks')"
      >
        <el-icon><Opportunity /></el-icon>
        <span>SQL智能建议</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/slow-sqls')"
        index="/slow-sqls"
        data-path="/slow-sqls"
        @click="navigate('/slow-sqls')"
      >
        <el-icon><TrendCharts /></el-icon>
        <span>慢SQL管理</span>
      </el-menu-item>

      <el-menu-item
        v-if="hasMenu('/archive-tasks')"
        index="/archive-tasks"
        data-path="/archive-tasks"
        @click="navigate('/archive-tasks')"
      >
        <el-icon><Tickets /></el-icon>
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

      <el-menu-item
        v-if="hasMenu('/flashback-tasks')"
        index="/flashback-tasks"
        data-path="/flashback-tasks"
        @click="navigate('/flashback-tasks')"
      >
        <el-icon><Refresh /></el-icon>
        <span>数据闪回</span>
      </el-menu-item>

      <el-sub-menu v-if="showAdmin" index="admin">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </template>
        <el-menu-item
          v-if="hasMenu('/users')"
          index="/users"
          data-path="/users"
          @click="navigate('/users')"
        >
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item
          v-if="hasMenu('/roles')"
          index="/roles"
          data-path="/roles"
          @click="navigate('/roles')"
        >
          <el-icon><Key /></el-icon>
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

      <el-menu-item
        v-if="hasMenu('/connections')"
        index="/connections"
        data-path="/connections"
        @click="navigate('/connections')"
      >
        <el-icon><Connection /></el-icon>
        <span>连接管理</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Connection,
  Key,
  Opportunity,
  Setting,
  Document,
  Lock,
  Refresh,
  Tickets,
  TrendCharts,
  User,
} from '@element-plus/icons-vue'
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
  if (route.path.startsWith('/slow-sql')) return '/slow-sqls'
  if (route.path.startsWith('/archive-tasks')) return '/archive-tasks'
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
  background-color: #343a40;
  padding-top: 10px;
}

.sidebar-menu {
  border: none;
}
</style>
