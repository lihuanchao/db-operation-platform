<template>
  <AppLayout>
    <div class="placeholder-shell">
      <div class="placeholder-card">
        <h2>SQL审核</h2>
        <p>功能建设中，后续将提供 SQL 审核规则与结果管理能力。</p>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import AppLayout from '@/components/Layout/AppLayout.vue'
</script>

<style scoped>
.placeholder-shell {
  height: 100%;
  min-height: 0;
  display: flex;
}

.placeholder-card {
  width: 100%;
  min-height: 100%;
  padding: 16px;
  border: 1px solid #d9e4ef;
  background: #fff;
}

.placeholder-card h2 {
  margin: 0 0 8px;
  color: #173556;
  font-size: 16px;
}

.placeholder-card p {
  margin: 0;
  color: #5f7084;
  font-size: 13px;
}
</style>
