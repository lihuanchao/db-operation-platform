import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
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
