import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'SlowSQLList',
    component: () => import('@/views/SlowSQLList.vue')
  },
  {
    path: '/detail/:checksum',
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
    path: '/execution-logs',
    name: 'ExecutionLogList',
    component: () => import('@/views/ExecutionLogList.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
