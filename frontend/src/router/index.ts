import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { canAccessPath } from '@/auth/access'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    redirect: '/optimization-tasks'
  },
  {
    path: '/optimization-tasks',
    name: 'OptimizationTaskList',
    component: () => import('@/views/OptimizationTaskList.vue')
  },
  {
    path: '/optimization-tasks/create/sql',
    name: 'OptimizationTaskCreateSql',
    component: () => import('@/views/OptimizationTaskCreateSql.vue')
  },
  {
    path: '/optimization-tasks/create/mybatis',
    name: 'OptimizationTaskCreateMyBatis',
    component: () => import('@/views/OptimizationTaskCreateMyBatis.vue')
  },
  {
    path: '/optimization-tasks/:id',
    name: 'OptimizationTaskDetail',
    component: () => import('@/views/OptimizationTaskDetail.vue')
  },
  {
    path: '/sql-audit',
    name: 'SqlAudit',
    component: () => import('@/views/SqlAuditPlaceholder.vue')
  },
  {
    path: '/slow-sqls',
    name: 'SlowSQLList',
    component: () => import('@/views/SlowSQLList.vue')
  },
  {
    path: '/slow-sql/:checksum',
    name: 'SlowSQLDetail',
    component: () => import('@/views/SlowSQLDetail.vue')
  },
  {
    path: '/connections',
    name: 'ConnectionList',
    component: () => import('@/views/ConnectionList.vue')
  },
  {
    path: '/archive-tasks',
    name: 'ArchiveTaskWithCron',
    component: () => import('@/views/ArchiveTaskWithCron.vue')
  },
  {
    path: '/archive-tasks/:id',
    name: 'ArchiveTaskDetail',
    component: () => import('@/views/ArchiveTaskWithCron.vue')
  },
  {
    path: '/sql-throttle/rules',
    name: 'SqlThrottleRuleList',
    component: () => import('@/views/SqlThrottleRuleList.vue')
  },
  {
    path: '/sql-throttle/runs',
    name: 'SqlThrottleRunList',
    component: () => import('@/views/SqlThrottleRunList.vue')
  },
  {
    path: '/sql-throttle/runs/:id',
    name: 'SqlThrottleRunDetail',
    component: () => import('@/views/SqlThrottleRunDetail.vue')
  },
  {
    path: '/execution-logs',
    name: 'ExecutionLogList',
    component: () => import('@/views/ExecutionLogList.vue')
  },
  {
    path: '/flashback-tasks',
    name: 'FlashbackTaskList',
    component: () => import('@/views/FlashbackTaskList.vue')
  },
  {
    path: '/flashback-tasks/create',
    name: 'FlashbackTaskCreate',
    component: () => import('@/views/FlashbackTaskCreate.vue')
  },
  {
    path: '/flashback-tasks/:id',
    name: 'FlashbackTaskDetail',
    component: () => import('@/views/FlashbackTaskDetail.vue')
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('@/views/UserManagement.vue')
  },
  {
    path: '/roles',
    name: 'RoleManagement',
    component: () => import('@/views/RoleManagement.vue')
  },
  {
    path: '/permissions',
    name: 'PermissionManagement',
    component: () => import('@/views/PermissionManagement.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)

  if (!authStore.initialized) {
    await authStore.restore()
  }

  if (to.meta.public) {
    if (authStore.isAuthenticated) {
      return authStore.homePath
    }
    return true
  }

  if (!authStore.isAuthenticated) {
    return '/login'
  }

  if (!canAccessPath(authStore.roleCode, to.path)) {
    return authStore.homePath
  }

  return true
})

export default router
