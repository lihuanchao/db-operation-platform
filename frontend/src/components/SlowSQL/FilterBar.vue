<template>
  <el-card class="filter-card" shadow="never">
    <el-form :model="localFilters" inline class="filter-form">
      <el-form-item label="主机">
        <el-input
          v-model="localFilters.host"
          placeholder="筛选主机"
          clearable
          style="width: 180px"
        />
      </el-form-item>
      <el-form-item label="数据库">
        <el-input
          v-model="localFilters.database_name"
          placeholder="筛选数据库"
          clearable
          style="width: 180px"
        />
      </el-form-item>
      <el-form-item label="优化状态">
        <el-select v-model="localFilters.is_optimized" placeholder="全部" clearable style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="已优化" value="1" />
          <el-option label="待优化" value="0" />
        </el-select>
      </el-form-item>
      <el-form-item label="时间范围">
        <el-select v-model="localFilters.time_range" placeholder="不限" clearable style="width: 140px" @change="handleTimeRangeChange">
          <el-option label="不限" value="" />
          <el-option label="最近1小时" value="1h" />
          <el-option label="今天" value="today" />
          <el-option label="最近7天" value="7d" />
          <el-option label="最近30天" value="30d" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </el-form-item>
      <el-form-item v-if="showCustomTime" label="开始时间">
        <el-date-picker
          v-model="localFilters.ts_min"
          type="datetime"
          placeholder="选择开始时间"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DDTHH:mm"
        />
      </el-form-item>
      <el-form-item v-if="showCustomTime" label="结束时间">
        <el-date-picker
          v-model="localFilters.ts_max"
          type="datetime"
          placeholder="选择结束时间"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DDTHH:mm"
        />
      </el-form-item>
      <el-form-item class="filter-actions">
        <el-button type="primary" @click="handleSearch">
          <el-icon><Search /></el-icon>
          筛选
        </el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import type { FilterParams } from '@/types'

interface Props {
  filters: FilterParams
}

interface Emits {
  (e: 'search', filters: FilterParams): void
  (e: 'reset'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const localFilters = ref<FilterParams>({ ...props.filters })

const showCustomTime = computed(() => localFilters.value.time_range === 'custom')

watch(() => props.filters, (newFilters) => {
  localFilters.value = { ...newFilters }
}, { deep: true })

function handleTimeRangeChange(value: string) {
  if (value !== 'custom') {
    localFilters.value.ts_min = ''
    localFilters.value.ts_max = ''
  }
}

function handleSearch() {
  emit('search', { ...localFilters.value })
}

function handleReset() {
  emit('reset')
}
</script>

<style scoped>
.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  margin-bottom: 0;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.filter-form :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
  flex-shrink: 0;
}

.filter-actions {
  margin-left: auto;
}
</style>
