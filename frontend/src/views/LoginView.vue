<template>
  <div class="login-page">
    <div class="login-bg" />
    <el-card class="login-card" shadow="hover">
      <h2>数据库运维平台</h2>
      <p>使用工号和密码登录</p>
      <el-form @submit.prevent="handleSubmit">
        <el-form-item label="工号">
          <el-input v-model="form.employee_no" placeholder="请输入工号" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="handleSubmit">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = reactive({
  employee_no: '',
  password: ''
})

async function handleSubmit() {
  if (!form.employee_no || !form.password) {
    return
  }
  loading.value = true
  try {
    await authStore.login(form)
    await authStore.fetchAuthorizedConnections()
    router.replace(authStore.homePath)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(145deg, #e6eef9 0%, #f6fafc 100%);
}

.login-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(550px 240px at 10% 10%, rgba(37, 99, 235, 0.12), transparent 60%),
    radial-gradient(640px 300px at 90% 85%, rgba(16, 185, 129, 0.12), transparent 58%);
}

.login-card {
  width: 420px;
  max-width: calc(100vw - 32px);
  border-radius: 14px;
  z-index: 1;
}

.login-card h2 {
  margin: 0;
  color: #1f2d3d;
}

.login-card p {
  margin: 6px 0 18px;
  color: #6b778c;
  font-size: 13px;
}
</style>
