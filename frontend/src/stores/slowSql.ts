import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getSlowSQLList, getSlowSQLDetail, optimizeSlowSQL, batchOptimizeSlowSQLs } from '@/api/slowSql'
import type { SlowSQL, FilterParams, PaginationInfo } from '@/types'

export const useSlowSqlStore = defineStore('slowSql', () => {
  // State
  const list = ref<SlowSQL[]>([])
  const currentDetail = ref<SlowSQL | null>(null)
  const pagination = ref<PaginationInfo>({
    page: 1,
    per_page: 10,
    total: 0,
    total_pages: 1,
    has_prev: false,
    has_next: false,
    prev_num: null,
    next_num: null
  })
  const filters = ref<FilterParams>({
    database_name: '',
    host: '',
    is_optimized: '',
    time_range: '',
    ts_min: '',
    ts_max: '',
    page: 1,
    per_page: 10
  })
  const loading = ref(false)
  const detailLoading = ref(false)
  const optimizeLoading = ref(false)

  // Getters
  const hasSelected = computed(() => list.value.some(item => item._selected))
  const selectedIds = computed(() => list.value.filter(item => item._selected).map(item => item.checksum))

  // Actions
  async function fetchList() {
    loading.value = true
    try {
      const res = await getSlowSQLList(filters.value)
      if (res.data) {
        list.value = res.data.items.map(item => ({ ...item, _selected: false }))
        pagination.value = res.data.pagination
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(checksum: string) {
    detailLoading.value = true
    try {
      const res = await getSlowSQLDetail(checksum)
      if (res.data) {
        currentDetail.value = res.data
      }
    } finally {
      detailLoading.value = false
    }
  }

  async function optimize(checksum: string) {
    optimizeLoading.value = true
    try {
      const res = await optimizeSlowSQL(checksum)
      if (res.data && currentDetail.value?.checksum === checksum) {
        currentDetail.value.optimized_suggestion = res.data.suggestion
        currentDetail.value.is_optimized = 1
      }
      // Also update in list
      const item = list.value.find(i => i.checksum === checksum)
      if (item) {
        item.is_optimized = 1
      }
      return res
    } finally {
      optimizeLoading.value = false
    }
  }

  async function batchOptimize(ids: string[]) {
    optimizeLoading.value = true
    try {
      const res = await batchOptimizeSlowSQLs(ids)
      // Update list items
      if (res.data?.results) {
        res.data.results.forEach(r => {
          if (r.success) {
            const item = list.value.find(i => i.checksum === r.id)
            if (item) {
              item.is_optimized = 1
            }
          }
        })
      }
      return res
    } finally {
      optimizeLoading.value = false
    }
  }

  function setFilters(newFilters: Partial<FilterParams>) {
    filters.value = { ...filters.value, ...newFilters, page: newFilters.page || 1 }
  }

  function resetFilters() {
    filters.value = {
      database_name: '',
      host: '',
      is_optimized: '',
      time_range: '',
      ts_min: '',
      ts_max: '',
      page: 1,
      per_page: 10
    }
  }

  function toggleSelect(checksum: string) {
    const item = list.value.find(i => i.checksum === checksum)
    if (item) {
      item._selected = !item._selected
    }
  }

  function toggleSelectAll(checked: boolean) {
    list.value.forEach(item => {
      item._selected = checked
    })
  }

  function goToPage(page: number) {
    filters.value.page = page
    fetchList()
  }

  return {
    // State
    list,
    currentDetail,
    pagination,
    filters,
    loading,
    detailLoading,
    optimizeLoading,
    // Getters
    hasSelected,
    selectedIds,
    // Actions
    fetchList,
    fetchDetail,
    optimize,
    batchOptimize,
    setFilters,
    resetFilters,
    toggleSelect,
    toggleSelectAll,
    goToPage
  }
})
