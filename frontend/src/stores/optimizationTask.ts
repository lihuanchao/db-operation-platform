import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getOptimizationTaskList,
  getOptimizationTaskDetail,
  createSqlOptimizationTask,
  createMyBatisOptimizationTask
} from '@/api/optimizationTask'
import type {
  OptimizationTask,
  OptimizationTaskType,
  CreateSqlOptimizationTaskPayload,
  CreateMyBatisOptimizationTaskPayload
} from '@/types'

export const useOptimizationTaskStore = defineStore('optimizationTask', () => {
  const list = ref<OptimizationTask[]>([])
  const loading = ref(false)
  const detailLoading = ref(false)
  const submitLoading = ref(false)
  const currentTask = ref<OptimizationTask | null>(null)
  const page = ref(1)
  const perPage = ref(10)
  const total = ref(0)
  const taskType = ref<OptimizationTaskType | ''>('')

  async function fetchList() {
    loading.value = true
    try {
      const res = await getOptimizationTaskList({
        page: page.value,
        per_page: perPage.value,
        task_type: taskType.value
      })
      if (res.data) {
        list.value = res.data.items
        total.value = res.data.total
        page.value = res.data.page
        perPage.value = res.data.per_page
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    detailLoading.value = true
    try {
      const res = await getOptimizationTaskDetail(id)
      if (res.data) {
        currentTask.value = res.data
        return res.data
      }
    } finally {
      detailLoading.value = false
    }
    return null
  }

  async function createSqlTask(payload: CreateSqlOptimizationTaskPayload) {
    submitLoading.value = true
    try {
      const res = await createSqlOptimizationTask(payload)
      if (res.success && res.data) {
        ElMessage.success('SQL优化任务已加入后台执行')
        return res.data
      }
    } finally {
      submitLoading.value = false
    }
    return null
  }

  async function createMyBatisTask(payload: CreateMyBatisOptimizationTaskPayload) {
    submitLoading.value = true
    try {
      const res = await createMyBatisOptimizationTask(payload)
      if (res.success && res.data) {
        ElMessage.success('MyBatis优化任务已加入后台执行')
        return res.data
      }
    } finally {
      submitLoading.value = false
    }
    return null
  }

  function setPage(newPage: number) {
    page.value = newPage
  }

  function setPerPage(newSize: number) {
    perPage.value = newSize
    page.value = 1
  }

  function setTaskType(newType: OptimizationTaskType | '') {
    taskType.value = newType
    page.value = 1
  }

  return {
    list,
    loading,
    detailLoading,
    submitLoading,
    currentTask,
    page,
    perPage,
    total,
    taskType,
    fetchList,
    fetchDetail,
    createSqlTask,
    createMyBatisTask,
    setPage,
    setPerPage,
    setTaskType
  }
})
