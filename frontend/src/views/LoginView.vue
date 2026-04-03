<template>
  <div class="login-page">
    <div class="login-bg" />
    <div class="login-glow login-glow-left" />
    <div class="login-glow login-glow-right" />
    <el-card class="login-card" shadow="hover">
      <div class="login-title">
        <h2>数据库运维平台</h2>
        <p>工号 + 密码登录</p>
      </div>
      <el-form class="login-form" @submit.prevent="handleSubmit">
        <el-form-item label="工号" required>
          <el-input v-model="form.employee_no" placeholder="请输入工号" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-button type="primary" :loading="loading" :disabled="loading" class="submit-btn" @click="handleSubmit">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = reactive({
  employee_no: '',
  password: ''
})

async function handleSubmit() {
  if (!form.employee_no.trim() && !form.password.trim()) {
    ElMessage.warning('请输入工号和密码')
    return
  }
  if (!form.employee_no.trim()) {
    ElMessage.warning('请输入工号')
    return
  }
  if (!form.password.trim()) {
    ElMessage.warning('请输入密码')
    return
  }
  loading.value = true
  try {
    await authStore.login({
      employee_no: form.employee_no.trim(),
      password: form.password
    })
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

.login-glow {
  position: absolute;
  width: 360px;
  height: 360px;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.45;
}

.login-glow-left {
  top: -80px;
  left: -120px;
  background: rgba(59, 130, 246, 0.4);
}

.login-glow-right {
  right: -120px;
  bottom: -90px;
  background: rgba(34, 197, 94, 0.38);
}

.login-card {
  width: 420px;
  max-width: calc(100vw - 32px);
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  backdrop-filter: blur(3px);
  z-index: 1;
}

.login-title h2 {
  margin: 0;
  color: #1f2d3d;
}

.login-title p {
  margin: 6px 0 0;
  color: #607089;
  font-size: 13px;
}

.login-form {
  margin-top: 18px;
}

.submit-btn {
  width: 100%;
  height: 40px;
  border-radius: 10px;
  font-weight: 600;
}
</style>
