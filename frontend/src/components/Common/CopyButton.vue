<template>
  <el-button
    :type="copied ? 'success' : 'default'"
    size="small"
    @click="handleCopy"
  >
    <el-icon v-if="!copied"><DocumentCopy /></el-icon>
    <el-icon v-else><Check /></el-icon>
    <span>{{ copied ? '已复制' : '复制' }}</span>
  </el-button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { DocumentCopy, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

interface Props {
  text: string
}

const props = defineProps<Props>()
const copied = ref(false)

async function handleCopy() {
  try {
    await navigator.clipboard.writeText(props.text)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>
