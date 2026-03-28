import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getCronJobList,
  getCronJob,
  createCronJob,
  updateCronJob,
  deleteCronJob,
  toggleCronJob
} from '@/api/cronJob'
import type { CronJob } from '@/types'

export const useCronJobStore = defineStore('cronJob', () => {
  // State
  const list = ref<CronJob[]>([])
  const loading = ref(false)
  const formLoading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(10)
  const filters = ref({
    task_id: undefined as number | undefined
  })

  // Getters
  const hasSelected = computed(() => list.value.some(item => item._selected))
  const selectedIds = computed(() => list.value.filter(item => item._selected).map(item => item.id))

  // Actions
  async function fetchList() {
    loading.value = true
    try {
      const res = await getCronJobList({
        page: page.value,
        per_page: perPage.value,
        ...filters.value
      })
      if (res.data) {
        list.value = res.data.items.map(item => ({ ...item, _selected: false }))
        total.value = res.data.total
        page.value = res.data.page
        perPage.value = res.data.per_page
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    loading.value = true
    try {
      const res = await getCronJob(id)
      if (res.data) {
        return res.data
      }
    } finally {
      loading.value = false
    }
    return null
  }

  async function addJob(data: Omit<CronJob, 'id' | 'created_at' | 'updated_at' | 'next_run_time' | 'last_run_time'>) {
    formLoading.value = true
    try {
      const res = await createCronJob(data)
      if (res.success) {
        ElMessage.success('定时任务创建成功')
        await fetchList()
        return res.data
      } else {
        ElMessage.error(res.error || '创建失败')
      }
    } finally {
      formLoading.value = false
    }
    return null
  }

  async function editJob(id: number, data: Partial<Omit<CronJob, 'id' | 'created_at' | 'updated_at'>>) {
    formLoading.value = true
    try {
      const res = await updateCronJob(id, data)
      if (res.success) {
        ElMessage.success('定时任务更新成功')
        await fetchList()
        return res.data
      } else {
        ElMessage.error(res.error || '更新失败')
      }
    } finally {
      formLoading.value = false
    }
    return null
  }

  async function removeJob(id: number) {
    loading.value = true
    try {
      const res = await deleteCronJob(id)
      if (res.success) {
        ElMessage.success('定时任务删除成功')
        await fetchList()
      } else {
        ElMessage.error(res.error || '删除失败')
      }
    } finally {
      loading.value = false
    }
  }

  async function toggleJobStatus(id: number) {
    loading.value = true
    try {
      const res = await toggleCronJob(id)
      if (res.success && res.data) {
        ElMessage.success(res.data.is_active ? '定时任务已激活' : '定时任务已暂停')
        await fetchList()
        return res.data
      } else {
        ElMessage.error(res.error || '操作失败')
      }
    } finally {
      loading.value = false
    }
    return null
  }

  function setFilters(newFilters: Partial<typeof filters.value>) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
  }

  function resetFilters() {
    filters.value = {
      task_id: undefined
    }
    page.value = 1
  }

  function toggleSelect(id: number) {
    const item = list.value.find(i => i.id === id)
    if (item) {
      item._selected = !item._selected
    }
  }

  function toggleSelectAll(checked: boolean) {
    list.value.forEach(item => {
      item._selected = checked
    })
  }

  function goToPage(pageNum: number) {
    page.value = pageNum
    fetchList()
  }

  function setPageSize(size: number) {
    perPage.value = size
    page.value = 1
    fetchList()
  }

  return {
    // State
    list,
    loading,
    formLoading,
    total,
    page,
    perPage,
    filters,
    // Getters
    hasSelected,
    selectedIds,
    // Actions
    fetchList,
    fetchDetail,
    addJob,
    editJob,
    removeJob,
    toggleJobStatus,
    setFilters,
    resetFilters,
    toggleSelect,
    toggleSelectAll,
    goToPage,
    setPageSize
  }
})
