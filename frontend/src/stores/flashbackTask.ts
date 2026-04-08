import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createFlashbackTask,
  downloadFlashbackTaskArtifact,
  downloadFlashbackTaskLog,
  getFlashbackTask,
  getFlashbackTaskArtifacts,
  getFlashbackTaskList
} from '@/api/flashbackTask'
import type {
  CreateFlashbackTaskPayload,
  FlashbackTask,
  FlashbackTaskArtifact,
  FlashbackTaskStatus,
  FlashbackSqlType,
  FlashbackWorkType,
  PaginationInfo
} from '@/types'

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
    ElMessage.success('下载成功')
    return response
  } finally {
    window.URL.revokeObjectURL(url)
    if (anchor.parentNode) {
      anchor.parentNode.removeChild(anchor)
    }
  }
}

export const useFlashbackTaskStore = defineStore('flashbackTask', () => {
  const list = ref<FlashbackTask[]>([])
  const currentTask = ref<FlashbackTask | null>(null)
  const artifacts = ref<FlashbackTaskArtifact[]>([])
  const loading = ref(false)
  const formLoading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(10)
  const pagination = ref<PaginationInfo | null>(null)
  const filters = ref({
    database_name: '',
    table_name: '',
    status: '' as FlashbackTaskStatus | '',
    sql_type: '' as FlashbackSqlType | '',
    work_type: '' as FlashbackWorkType | ''
  })

  const hasSelected = computed(() => list.value.some(item => item._selected))
  const selectedIds = computed(() => list.value.filter(item => item._selected).map(item => item.id))

  async function fetchList() {
    loading.value = true
    try {
      const res = await getFlashbackTaskList({
        page: page.value,
        per_page: perPage.value,
        ...filters.value
      })
      if (res.data) {
        list.value = res.data.items.map(item => ({ ...item, _selected: false }))
        pagination.value = res.data.pagination
        total.value = res.data.pagination.total
        page.value = res.data.pagination.page
        perPage.value = res.data.pagination.per_page
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    loading.value = true
    try {
      const res = await getFlashbackTask(id)
      if (res.data) {
        currentTask.value = { ...res.data, _selected: false }
        artifacts.value = res.data.artifacts ?? []
        return currentTask.value
      }
    } finally {
      loading.value = false
    }
    return null
  }

  async function fetchArtifacts(id: number) {
    loading.value = true
    try {
      const res = await getFlashbackTaskArtifacts(id)
      if (res.data) {
        artifacts.value = res.data.items
        return artifacts.value
      }
    } finally {
      loading.value = false
    }
    return []
  }

  async function createTask(data: CreateFlashbackTaskPayload) {
    formLoading.value = true
    try {
      const res = await createFlashbackTask(data)
      if (res.data) {
        const created = { ...res.data, _selected: false }
        currentTask.value = created
        artifacts.value = created.artifacts ?? []
        ElMessage.success('任务创建成功')
        await fetchList()
        return created
      }
      ElMessage.error(res.error || '创建失败')
    } finally {
      formLoading.value = false
    }
    return null
  }

  async function downloadArtifact(taskId: number, artifactId: string) {
    loading.value = true
    try {
      const response = await downloadFlashbackTaskArtifact(taskId, artifactId)
      const artifact = artifacts.value.find(item => item.id === artifactId)
        ?? currentTask.value?.artifacts.find(item => item.id === artifactId)
      return await saveDownloadResponse(response, artifact?.name || artifactId)
    } finally {
      loading.value = false
    }
  }

  async function downloadLog(taskId: number) {
    loading.value = true
    try {
      const response = await downloadFlashbackTaskLog(taskId)
      return await saveDownloadResponse(response, `flashback_task_${taskId}.log`)
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
      database_name: '',
      table_name: '',
      status: '',
      sql_type: '',
      work_type: ''
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
    currentTask,
    artifacts,
    loading,
    formLoading,
    total,
    page,
    perPage,
    pagination,
    filters,
    hasSelected,
    selectedIds,
    fetchList,
    fetchDetail,
    fetchArtifacts,
    createTask,
    downloadArtifact,
    downloadLog,
    setFilters,
    resetFilters,
    toggleSelect,
    toggleSelectAll,
    goToPage,
    setPageSize
  }
})
