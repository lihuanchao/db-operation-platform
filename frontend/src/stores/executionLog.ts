import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  downloadExecutionLog,
  getExecutionLog,
  getExecutionLogList
} from '@/api/executionLog'
import type { ExecutionLog, ExecutionLogFilterType, ExecutionLogRouteType } from '@/types'

function canTriggerBrowserDownload() {
  return typeof window !== 'undefined'
    && typeof window.URL?.createObjectURL === 'function'
    && typeof document !== 'undefined'
}

async function saveDownloadResponse(response: any, fileName: string) {
  if (!response || (response.status !== 200 && response.status !== 304)) {
    ElMessage.error('下载失败')
    return null
  }

  if (!canTriggerBrowserDownload()) {
    return response
  }

  const blob = response.data instanceof Blob
    ? response.data
    : new Blob([response.data], { type: 'application/octet-stream' })
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')

  try {
    anchor.href = url
    anchor.download = fileName
    document.body.appendChild(anchor)
    anchor.click()
    ElMessage.success('日志下载成功')
    return response
  } finally {
    window.URL.revokeObjectURL(url)
    if (anchor.parentNode) {
      anchor.parentNode.removeChild(anchor)
    }
  }
}

function resolveDownloadContext(
  list: ExecutionLog[],
  currentLog: ExecutionLog | null,
  logTypeOrId: ExecutionLogRouteType | number,
  maybeId?: number
): { logType: ExecutionLogRouteType; id?: number } {
  if (typeof logTypeOrId === 'number') {
    const existing = list.find(item => item.id === logTypeOrId)
    if (existing) {
      return {
        logType: existing.log_type ?? 'archive',
        id: logTypeOrId
      }
    }

    if (currentLog?.id === logTypeOrId) {
      return {
        logType: currentLog.log_type ?? 'archive',
        id: logTypeOrId
      }
    }

    return {
      logType: 'archive',
      id: logTypeOrId
    }
  }

  return {
    logType: logTypeOrId,
    id: maybeId
  }
}

export const useExecutionLogStore = defineStore('executionLog', () => {
  const list = ref<ExecutionLog[]>([])
  const currentLog = ref<ExecutionLog | null>(null)
  const loading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(10)
  const filters = ref({
    task_id: undefined as number | undefined,
    task_name: '',
    status: undefined as number | undefined,
    log_type: '' as ExecutionLogFilterType | ''
  })

  const hasSelected = computed(() => list.value.some(item => item._selected))
  const selectedIds = computed(() => list.value.filter(item => item._selected).map(item => item.id))

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
        currentLog.value = { ...res.data, _selected: false }
        return currentLog.value
      }
    } finally {
      loading.value = false
    }
    return null
  }

  async function downloadLog(logTypeOrId: ExecutionLogRouteType | number, maybeId?: number) {
    loading.value = true
    try {
      const { logType, id } = resolveDownloadContext(list.value, currentLog.value, logTypeOrId, maybeId)
      if (typeof id !== 'number') {
        ElMessage.error('下载失败')
        return null
      }

      try {
        const response = await downloadExecutionLog(logType, id)
        return await saveDownloadResponse(response, `${logType}_execution_log_${id}.log`)
      } catch (error: any) {
        const message = error?.response?.data?.error || error?.message || '下载失败'
        ElMessage.error(message)
        return null
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
      task_name: '',
      status: undefined,
      log_type: ''
    }
    page.value = 1
  }

  function toggleSelect(id: number) {
    const item = list.value.find(entry => entry.id === id)
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
    list,
    currentLog,
    loading,
    total,
    page,
    perPage,
    filters,
    hasSelected,
    selectedIds,
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
