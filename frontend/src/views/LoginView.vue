<template>
  <div class="login-page">
    <main class="login-shell">
      <el-card class="login-card" shadow="hover">
        <div class="login-title">
          <h1>数据库运维平台</h1>
          <p>工号 + 密码登录</p>
        </div>
        <p class="sr-only" aria-live="polite">{{ errorMessage }}</p>
        <el-alert
          v-if="errorMessage"
          class="form-alert"
          type="error"
          :closable="false"
          show-icon
          :title="errorMessage"
        />
        <el-form class="login-form" @submit.prevent="handleSubmit">
          <el-form-item label="工号" required :error="fieldErrors.employee_no">
            <el-input
              v-model="form.employee_no"
              placeholder="请输入工号"
              clearable
              autocomplete="username"
              :prefix-icon="User"
              @keyup.enter="handleSubmit"
            />
            <p v-if="fieldErrors.employee_no" class="field-error" role="alert">{{ fieldErrors.employee_no }}</p>
          </el-form-item>
          <el-form-item label="密码" required :error="fieldErrors.password">
            <el-input
              v-model="form.password"
              type="password"
              show-password
              placeholder="请输入密码"
              autocomplete="current-password"
              :prefix-icon="Lock"
              @keydown="updateCapsLockState"
              @keyup="updateCapsLockState"
              @keyup.enter="handleSubmit"
            />
            <p v-if="fieldErrors.password" class="field-error" role="alert">{{ fieldErrors.password }}</p>
          </el-form-item>
          <p v-if="capsLockOn" class="caps-lock-hint">当前已开启大写锁定，请确认密码大小写。</p>
          <el-button type="primary" native-type="submit" :loading="loading" :disabled="loading" class="submit-btn">
            登录
          </el-button>
        </el-form>
        <p class="login-footer">如账号异常，请联系平台管理员处理权限或重置密码。</p>
      </el-card>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const errorMessage = ref('')
const capsLockOn = ref(false)
const form = reactive({
  employee_no: '',
  password: ''
})
const fieldErrors = reactive({
  employee_no: '',
  password: ''
})

watch(
  () => form.employee_no,
  () => {
    if (fieldErrors.employee_no) {
      fieldErrors.employee_no = ''
    }
    if (errorMessage.value) {
      errorMessage.value = ''
    }
  }
)

watch(
  () => form.password,
  () => {
    if (fieldErrors.password) {
      fieldErrors.password = ''
    }
    if (errorMessage.value) {
      errorMessage.value = ''
    }
  }
)

function validateForm() {
  fieldErrors.employee_no = ''
  fieldErrors.password = ''
  errorMessage.value = ''
  const employeeNo = form.employee_no.trim()
  const password = form.password.trim()
  if (!employeeNo) {
    fieldErrors.employee_no = '请输入工号'
  }
  if (!password) {
    fieldErrors.password = '请输入密码'
  }
  if (fieldErrors.employee_no || fieldErrors.password) {
    errorMessage.value = '请完善登录信息后重试'
    return null
  }
  return {
    employee_no: employeeNo,
    password: form.password
  }
}

function updateCapsLockState(event: KeyboardEvent) {
  if (!event.getModifierState) {
    return
  }
  capsLockOn.value = event.getModifierState('CapsLock')
}

async function handleSubmit() {
  if (loading.value) {
    return
  }
  const payload = validateForm()
  if (!payload) {
    ElMessage.warning('请输入工号和密码')
    return
  }
  loading.value = true
  try {
    await authStore.login(payload)
    await authStore.fetchAuthorizedConnections()
    router.replace(authStore.homePath)
  } catch (error: any) {
    if (error?.response?.status === 401) {
      fieldErrors.password = '请检查密码后重试'
      errorMessage.value = '您输入的用户名或密码错误，请重新输入'
      ElMessage.error(errorMessage.value)
      return
    }
    errorMessage.value = '登录失败，请稍后重试'
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  --login-color-primary: #0369a1;
  --login-color-secondary: #0ea5e9;
  --login-color-text: #0f2a3d;
  --login-color-muted: #4c6478;
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 24px 16px;
  background-color: #f3f7fb;
  font-family: 'Lexend', 'Source Sans 3', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(520px, calc(100vw - 28px));
}

.login-card {
  border-radius: 22px;
  border: 1px solid rgba(14, 116, 144, 0.25);
  background: #ffffff;
  box-shadow: 0 24px 54px rgba(12, 74, 110, 0.16);
  overflow: hidden;
  animation: card-enter 380ms ease-out;
}

:deep(.login-card .el-card__body) {
  padding: 28px 28px 24px;
}

.login-title h1 {
  margin: 8px 0 0;
  font-size: clamp(28px, 5vw, 32px);
  line-height: 1.2;
  color: var(--login-color-text);
}

.login-title p {
  margin: 12px 0 0;
  color: var(--login-color-muted);
  font-size: 14px;
  line-height: 1.7;
}

.form-alert {
  margin-top: 16px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  border: 0;
  padding: 0;
  clip: rect(0, 0, 0, 0);
  overflow: hidden;
}

.login-form {
  margin-top: 20px;
}

:deep(.el-form-item__label) {
  color: #17415b;
  font-weight: 600;
  font-size: 13px;
}

:deep(.el-input__wrapper) {
  border-radius: 12px;
  min-height: 42px;
  box-shadow: 0 0 0 1px rgba(14, 116, 144, 0.18) inset;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 2px rgba(14, 165, 233, 0.2),
    0 0 0 1px rgba(14, 116, 144, 0.42) inset;
}

.field-error {
  width: 100%;
  margin-top: 8px;
  color: #b42318;
  font-size: 12px;
  line-height: 1.4;
}

.caps-lock-hint {
  margin: 4px 0 12px;
  color: #b45309;
  font-size: 12px;
  line-height: 1.5;
}

.submit-btn {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 15px;
  letter-spacing: 0.02em;
  border: none;
  background: var(--login-color-primary);
  box-shadow: 0 12px 24px rgba(3, 105, 161, 0.26);
}

.submit-btn:hover {
  transform: translateY(-1px);
  background: #075985;
}

.submit-btn:focus-visible {
  outline: 2px solid rgba(3, 105, 161, 0.42);
  outline-offset: 2px;
}

.login-footer {
  margin-top: 14px;
  font-size: 12px;
  line-height: 1.6;
  color: #4c6478;
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-card,
  .submit-btn,
  :deep(.el-input__wrapper) {
    animation: none;
    transition: none;
  }
}

@media (max-width: 980px) {
  .login-shell {
    width: min(500px, calc(100vw - 24px));
  }
}

@media (max-width: 640px) {
  .login-page {
    padding: 14px;
  }

  .login-shell {
    width: 100%;
  }

  .login-card {
    border-radius: 16px;
  }

  :deep(.login-card .el-card__body) {
    padding: 22px 18px 18px;
  }

  .login-title h1 {
    font-size: 24px;
  }
}
</style>
