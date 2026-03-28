import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getExecutionLogList,
  getExecutionLog,
  downloadExecutionLog
} from '@/api/executionLog'
import type { ExecutionLog } from '@/types'

export const useExecutionLogStore = defineStore('executionLog', () => {
  // State
  const list = ref<ExecutionLog[]>([])
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(10)
  const filters = ref({
    task_id: undefined as number | undefined,
    status: undefined as number | undefined
  })

  // Getters
  const hasSelected = computed(() => list.value.some(item => item._selected))
  const selectedIds = computed(() => list.value.filter(item => item._selected).map(item => item.id))

  // Actions
  async function fetchList() {
    loading.value = true
    try {
      const res = await getExecutionLogList({
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
      const res = await getExecutionLog(id)
      if (res.data) {
        return res.data
      }
    } finally {
      loading.value = false
    }
    return null
  }

  async function downloadLog(id: number) {
    loading.value = true
    try {
      const response = await downloadExecutionLog(id)
      // 创建下载链接
      const blob = new Blob([response as unknown as BlobPart], { type: 'text/plain' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `execution_log_${id}.log`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      ElMessage.success('日志下载成功')
    } catch (error: any) {
      ElMessage.error(error.response?.data?.error || '下载失败')
    } finally {
      loading.value = false
    }
  }

  function setFilters(newFilters: Partial<typeof filters.value>) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
  }

  function resetFilters() {
    filters.value = {
      task_id: undefined,
      status: undefined
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
    downloadLog,
    setFilters,
    resetFilters,
    toggleSelect,
    toggleSelectAll,
    goToPage,
    setPageSize
  }
})
