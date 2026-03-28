<template>
  <div class="app-layout">
    <el-container class="full-height">
      <el-aside width="220px" class="full-height">
        <Sidebar />
      </el-aside>
      <el-main class="full-height">
        <div class="main-content">
          <slot />
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import Sidebar from './Sidebar.vue'
</script>

<style scoped>
.app-layout {
  width: 100%;
  height: 100%;
  min-height: 100vh;
}

.full-height {
  height: 100%;
  min-height: 100vh;
}

.el-container {
  width: 100%;
  height: 100%;
}

.el-aside {
  background-color: #343a40;
  overflow: hidden;
  height: 100%;
}

.el-main {
  background-color: #f8f9fa;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.main-content {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  min-height: calc(100vh - 40px);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}
</style>
