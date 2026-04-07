<template>
  <div class="app-layout">
    <header class="layout-topbar">
      <div class="topbar-left">
        <div class="brand">
          <img
            :src="sinotrukLogo"
            alt="中国重汽"
            class="brand-logo"
            data-testid="brand-logo"
          >
          <span class="brand-title" data-testid="brand-title">中国重汽数据库运维平台</span>
        </div>
        <button
          type="button"
          class="collapse-toggle"
          data-testid="collapse-toggle"
          :aria-label="layoutStore.collapsed ? '展开侧边栏' : '收起侧边栏'"
          @click="layoutStore.toggleCollapsed()"
        >
          <span>{{ layoutStore.collapsed ? '展开' : '收起' }}</span>
        </button>
      </div>

      <div class="user-dropdown">
        <button
          type="button"
          class="user-trigger"
          :aria-expanded="userMenuOpen"
          @click="userMenuOpen = !userMenuOpen"
        >
          <span class="user-name" data-testid="user-name">{{ userName }}</span>
          <span class="user-caret">▾</span>
        </button>
        <div v-if="userMenuOpen" class="user-menu">
          <button type="button" class="user-menu-item" @click="handleLogout">
            退出
          </button>
        </div>
      </div>
    </header>

    <aside
      class="layout-aside"
      :style="{ width: asideWidth }"
    >
      <Sidebar />
    </aside>

    <div
      class="layout-main"
      :style="{ marginLeft: asideWidth }"
    >
      <div class="layout-tabs" :style="{ left: asideWidth }">
        <div
          v-for="tab in layoutStore.tabs"
          :key="tab.path"
          class="layout-tab"
          :class="{ 'is-active': layoutStore.activePath === tab.path }"
          role="button"
          tabindex="0"
          :data-tab-path="tab.path"
          @click="openTab(tab.path)"
          @keydown.enter.prevent="openTab(tab.path)"
          @keydown.space.prevent="openTab(tab.path)"
        >
          <span class="layout-tab-title">{{ tab.title }}</span>
          <button
            v-if="tab.closable"
            type="button"
            class="layout-tab-close"
            :data-close-path="tab.path"
            :aria-label="`关闭${tab.title}`"
            @click.stop="closeTab(tab.path)"
            @keydown.enter.stop.prevent="closeTab(tab.path)"
            @keydown.space.stop.prevent="closeTab(tab.path)"
          >
            ×
          </button>
        </div>
      </div>

      <main class="layout-content">
        <div class="main-content">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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

const userMenuOpen = ref(false)

const asideWidth = computed(() => (layoutStore.collapsed ? '64px' : '220px'))
const userName = computed(() => authStore.user?.real_name || '未登录')

function resolveTabTitle(path: string) {
  const matchedMenu = MENU_ITEMS.find((item) => {
    if (item.path === path) {
      return true
    }

    return item.matchPrefixes.some((prefix) => path === prefix || path.startsWith(prefix))
  })

  return matchedMenu?.label ?? path
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
  userMenuOpen.value = false
  layoutStore.resetToHomeTab()
  await authStore.logout()
  await router.replace('/login')
}

watch(
  () => route.path,
  (path) => {
    layoutStore.syncByRoute(path, resolveTabTitle(path))
  },
  { immediate: true }
)
</script>

<style scoped>
.app-layout {
  width: 100%;
  min-height: 100vh;
  background:
    linear-gradient(180deg, #eef3f8 0%, #f6f8fb 100%);
}

.layout-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 30;
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid #d8e0ea;
  backdrop-filter: blur(10px);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  width: 36px;
  height: 36px;
  object-fit: contain;
}

.brand-title {
  font-size: 18px;
  font-weight: 700;
  color: #1a2a3a;
  letter-spacing: 0.02em;
}

.collapse-toggle,
.user-trigger,
.user-menu-item,
.layout-tab-close {
  border: none;
  background: transparent;
  cursor: pointer;
}

.collapse-toggle {
  height: 36px;
  padding: 0 14px;
  border-radius: 10px;
  background: #eef4fb;
  color: #204872;
  font-size: 13px;
  font-weight: 600;
}

.user-dropdown {
  position: relative;
}

.user-trigger {
  min-width: 112px;
  height: 40px;
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-radius: 12px;
  background: #f4f7fb;
  color: #1a2a3a;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
}

.user-caret {
  color: #5f7084;
}

.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 120px;
  padding: 8px;
  border: 1px solid #d8e0ea;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 12px 24px rgba(16, 42, 67, 0.12);
}

.user-menu-item {
  width: 100%;
  height: 36px;
  border-radius: 8px;
  color: #a63a3a;
}

.layout-aside {
  position: fixed;
  top: 64px;
  left: 0;
  bottom: 0;
  z-index: 20;
  overflow: hidden;
  background: #343a40;
  transition: width 0.2s ease;
}

.layout-main {
  min-height: 100vh;
  padding-top: 112px;
  transition: margin-left 0.2s ease;
}

.layout-tabs {
  position: fixed;
  top: 64px;
  right: 0;
  z-index: 25;
  height: 48px;
  padding: 8px 20px 8px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  overflow-x: auto;
  background: rgba(248, 250, 252, 0.96);
  border-bottom: 1px solid #d8e0ea;
  transition: left 0.2s ease;
}

.layout-tab {
  min-width: 0;
  max-width: 240px;
  height: 32px;
  padding: 0 8px 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: #e5edf7;
  color: #4a5d73;
  cursor: pointer;
  user-select: none;
}

.layout-tab.is-active {
  background: #fff;
  border-color: #bfd1e6;
  color: #173556;
  box-shadow: 0 6px 18px rgba(23, 53, 86, 0.08);
}

.layout-tab-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 600;
}

.layout-tab-close {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: inherit;
  font-size: 16px;
  line-height: 1;
}

.layout-content {
  padding: 24px;
}

.main-content {
  min-height: calc(100vh - 136px);
  padding: 24px;
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 35, 58, 0.08);
}

@media (max-width: 960px) {
  .layout-topbar {
    padding: 0 16px;
  }

  .brand-title {
    font-size: 16px;
  }

  .layout-tabs {
    padding-right: 12px;
  }

  .layout-content {
    padding: 16px;
  }

  .main-content {
    padding: 16px;
  }
}
</style>
