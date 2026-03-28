import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getConnectionList,
  getConnection,
  createConnection,
  updateConnection,
  deleteConnection,
  testConnection,
  testConnectionDirect
} from '@/api/dbConnection'
import type { DbConnection } from '@/types'

export const useDbConnectionStore = defineStore('dbConnection', () => {
  // State
  const list = ref<DbConnection[]>([])
  const loading = ref(false)
  const formLoading = ref(false)
  const testLoading = ref(false)
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(10)
  const filters = ref({
    connection_name: '',
    host: ''
  })

  // Getters
  const hasSelected = computed(() => list.value.some(item => item._selected))
  const selectedIds = computed(() => list.value.filter(item => item._selected).map(item => item.id))

  // Actions
  async function fetchList() {
    loading.value = true
    try {
      const res = await getConnectionList({
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
      const res = await getConnection(id)
      if (res.data) {
        return res.data
      }
    } finally {
      loading.value = false
    }
    return null
  }

  async function addConnection(data: Omit<DbConnection, 'id' | 'created_at' | 'updated_at'>) {
    formLoading.value = true
    try {
      const res = await createConnection(data)
      if (res.success) {
        ElMessage.success('连接创建成功')
        await fetchList()
        return res.data
      } else {
        ElMessage.error(res.error || '创建失败')
      }
    } finally {
      formLoading.value = false
    }
  }

  async function editConnection(id: number, data: Partial<DbConnection>) {
    formLoading.value = true
    try {
      const res = await updateConnection(id, data)
      if (res.success) {
        ElMessage.success('连接更新成功')
        await fetchList()
        return res.data
      } else {
        ElMessage.error(res.error || '更新失败')
      }
    } finally {
      formLoading.value = false
    }
  }

  async function removeConnection(id: number) {
    loading.value = true
    try {
      const res = await deleteConnection(id)
      if (res.success) {
        ElMessage.success('连接删除成功')
        await fetchList()
      } else {
        ElMessage.error(res.error || '删除失败')
      }
    } finally {
      loading.value = false
    }
  }

  async function testConnectionAction(id: number) {
    testLoading.value = true
    try {
      const res = await testConnection(id)
      if (res.success) {
        ElMessage.success('连接测试成功')
        return true
      } else {
        ElMessage.error(res.error || '连接测试失败')
        return false
      }
    } finally {
      testLoading.value = false
    }
  }

  async function testConnectionDirectAction(data: {
    host: string
    port: number
    username: string
    password: string
  }) {
    testLoading.value = true
    try {
      const res = await testConnectionDirect(data)
      if (res.success) {
        ElMessage.success('连接测试成功')
        return true
      } else {
        ElMessage.error(res.error || '连接测试失败')
        return false
      }
    } finally {
      testLoading.value = false
    }
  }

  function setFilters(newFilters: Partial<typeof filters.value>) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
  }

  function resetFilters() {
    filters.value = {
      connection_name: '',
      host: ''
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
    testLoading,
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
    addConnection,
    editConnection,
    removeConnection,
    testConnectionAction,
    testConnectionDirectAction,
    setFilters,
    resetFilters,
    toggleSelect,
    toggleSelectAll,
    goToPage,
    setPageSize
  }
})
