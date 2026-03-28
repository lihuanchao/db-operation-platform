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
      console.log('开始下载日志，ID:', id)
      const response = await downloadExecutionLog(id)
      console.log('下载响应:', response)

      // 检查响应是否成功
      if (response && (response.status === 200 || response.status === 304)) {
        // 创建下载链接
        const blob = new Blob([response.data], { type: 'text/plain' })
        console.log('Blob创建成功，大小:', blob.size)
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `execution_log_${id}.log`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
        ElMessage.success('日志下载成功')
      } else {
        console.error('响应状态码错误:', response?.status)
        ElMessage.error('下载失败')
      }
    } catch (error: any) {
      console.error('下载出错:', error)
      // 尝试解析错误响应
      if (error.response?.data) {
        try {
          const reader = new FileReader()
          reader.onload = (e) => {
            try {
              const errorObj = JSON.parse(e.target?.result as string)
              ElMessage.error(errorObj.error || '下载失败')
            } catch {
              ElMessage.error('下载失败')
            }
          }
          reader.readAsText(error.response.data)
        } catch {
          ElMessage.error('下载失败')
        }
      } else {
        ElMessage.error(error.message || '下载失败')
      }
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
