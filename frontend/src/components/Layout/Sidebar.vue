<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h5>数据库运维</h5>
      <div class="user-line">
        <span>{{ authStore.user?.real_name || '未登录' }}</span>
        <el-button link type="primary" @click="handleLogout">退出</el-button>
      </div>
    </div>

    <el-menu
      :default-active="activeMenu"
      :default-openeds="['archive', 'admin']"
      class="sidebar-menu"
      background-color="#343a40"
      text-color="#fff"
      active-text-color="#fff"
    >
      <el-menu-item v-if="hasMenu('/optimization-tasks')" index="/optimization-tasks" @click="navigate('/optimization-tasks')">
        <el-icon><MagicStick /></el-icon>
        <span>SQL优化建议</span>
      </el-menu-item>

      <el-menu-item v-if="hasMenu('/slow-sqls')" index="/slow-sqls" @click="navigate('/slow-sqls')">
        <el-icon><DataLine /></el-icon>
        <span>慢SQL列表</span>
      </el-menu-item>

      <el-menu-item v-if="hasMenu('/connections')" index="/connections" @click="navigate('/connections')">
        <el-icon><Setting /></el-icon>
        <span>连接管理</span>
      </el-menu-item>

      <el-sub-menu v-if="showArchive" index="archive">
        <template #title>
          <el-icon><FolderOpened /></el-icon>
          <span>归档管理</span>
        </template>
        <el-menu-item v-if="hasMenu('/archive-tasks')" index="/archive-tasks" @click="navigate('/archive-tasks')">
          <el-icon><List /></el-icon>
          <span>归档任务</span>
        </el-menu-item>
        <el-menu-item v-if="hasMenu('/execution-logs')" index="/execution-logs" @click="navigate('/execution-logs')">
          <el-icon><Document /></el-icon>
          <span>执行日志</span>
        </el-menu-item>
      </el-sub-menu>

      <el-sub-menu v-if="showAdmin" index="admin">
        <template #title>
          <el-icon><UserFilled /></el-icon>
          <span>系统管理</span>
        </template>
        <el-menu-item v-if="hasMenu('/users')" index="/users" @click="navigate('/users')">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item v-if="hasMenu('/roles')" index="/roles" @click="navigate('/roles')">
          <el-icon><Management /></el-icon>
          <span>角色管理</span>
        </el-menu-item>
        <el-menu-item v-if="hasMenu('/permissions')" index="/permissions" @click="navigate('/permissions')">
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
  UserFilled
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

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

async function handleLogout() {
  await authStore.logout()
  router.replace('/login')
}
</script>

<style scoped>
.sidebar {
  min-height: 100vh;
  background-color: #343a40;
  padding-top: 20px;
}

.sidebar-header {
  padding: 0 20px 12px;
}

.sidebar-header h5 {
  color: #fff;
  margin: 0;
}

.user-line {
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #c9d3df;
  font-size: 12px;
}

.sidebar-menu {
  border: none;
}
</style>
