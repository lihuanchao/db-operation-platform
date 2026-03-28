<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <h5>数据库运维</h5>
    </div>
    <el-menu
      :default-active="activeMenu"
      :default-openeds="['archive']"
      class="sidebar-menu"
      background-color="#343a40"
      text-color="#fff"
      active-text-color="#fff"
    >
      <el-menu-item index="/" @click="navigate('/')">
        <el-icon><DataLine /></el-icon>
        <span>慢SQL列表</span>
      </el-menu-item>
      <el-menu-item index="/connections" @click="navigate('/connections')">
        <el-icon><Setting /></el-icon>
        <span>连接管理</span>
      </el-menu-item>
      <el-sub-menu index="archive">
        <template #title>
          <el-icon><FolderOpened /></el-icon>
          <span>归档管理</span>
        </template>
        <el-menu-item index="/archive-tasks" @click="navigate('/archive-tasks')">
          <el-icon><List /></el-icon>
          <span>归档任务</span>
        </el-menu-item>
        <el-menu-item index="/execution-logs" @click="navigate('/execution-logs')">
          <el-icon><Document /></el-icon>
          <span>执行日志</span>
        </el-menu-item>
      </el-sub-menu>
      <el-menu-item index="/flashback" disabled>
        <el-icon><RefreshLeft /></el-icon>
        <span>数据闪回</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataLine, RefreshLeft, Setting, FolderOpened, Document, List, Clock } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)

function navigate(path: string) {
  router.push(path)
}
</script>

<style scoped>
.sidebar {
  min-height: 100vh;
  background-color: #343a40;
  padding-top: 20px;
}

.sidebar-header {
  padding: 0 20px 20px;
}

.sidebar-header h5 {
  color: #fff;
  margin: 0;
}

.sidebar-menu {
  border: none;
}
</style>
