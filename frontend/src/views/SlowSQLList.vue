<template>
  <AppLayout>
    <div class="slow-sql-page">
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
    </div>
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
.slow-sql-page {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
