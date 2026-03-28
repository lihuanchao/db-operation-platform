<template>
  <AppLayout>
    <div class="page-header">
      <h2>慢SQL优化管理</h2>
    </div>

    <FilterBar
      :filters="store.filters"
      @search="handleSearch"
      @reset="handleReset"
    />

    <SQLTable
      :list="store.list"
      :loading="store.loading"
      :pagination="store.pagination"
      @page-change="handlePageChange"
    />
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import AppLayout from '@/components/Layout/AppLayout.vue'
import FilterBar from '@/components/SlowSQL/FilterBar.vue'
import SQLTable from '@/components/SlowSQL/SQLTable.vue'
import { useSlowSqlStore } from '@/stores/slowSql'

const store = useSlowSqlStore()

onMounted(() => {
  store.fetchList()
})

function handleSearch(filters: any) {
  store.setFilters(filters)
  store.fetchList()
}

function handleReset() {
  store.resetFilters()
  store.fetchList()
}

function handlePageChange(page: number, perPage: number) {
  store.setFilters({ page, per_page: perPage })
  store.fetchList()
}
</script>

<style scoped>
.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #1e3a5f;
}
</style>
