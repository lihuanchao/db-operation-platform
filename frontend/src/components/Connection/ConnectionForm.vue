<template>
  <el-form
    ref="formRef"
    class="connection-form"
    :model="form"
    :rules="rules"
    label-width="88px"
    autocomplete="off"
  >
    <el-form-item label="连接名称" prop="connection_name">
      <el-input v-model="form.connection_name" placeholder="请输入连接名称" autocomplete="off" />
    </el-form-item>

    <el-form-item label="主机地址" prop="host">
      <el-input v-model="form.host" placeholder="请输入主机地址" autocomplete="off" />
    </el-form-item>

    <el-form-item label="管理IP" prop="manage_host">
      <el-input v-model="form.manage_host" placeholder="请输入管理IP（可选）" autocomplete="off" />
    </el-form-item>

    <el-form-item label="端口" prop="port">
      <el-input-number
        v-model="form.port"
        :min="1"
        :max="65535"
        placeholder="请输入端口"
        style="width: 100%"
      />
    </el-form-item>

    <el-form-item label="用户名" prop="username">
      <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="off" />
    </el-form-item>

    <el-form-item label="密码" prop="password">
      <el-input
        v-model="form.password"
        type="password"
        placeholder="请输入密码"
        autocomplete="new-password"
        show-password
      />
    </el-form-item>

    <el-form-item label="状态" prop="is_enabled">
      <el-switch v-model="form.is_enabled" active-text="启用" inactive-text="禁用" />
    </el-form-item>

    <el-form-item>
      <el-button type="primary" :loading="loading" @click="handleTest">
        <el-icon><Connection /></el-icon>
        测试连接
      </el-button>
    </el-form-item>

    <el-form-item>
      <el-button type="primary" :loading="loading" @click="handleSave">
        保存
      </el-button>
      <el-button @click="$emit('cancel')">
        取消
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection } from '@element-plus/icons-vue'
import { useDbConnectionStore } from '@/stores/dbConnection'
import type { DbConnection } from '@/types'

const store = useDbConnectionStore()

interface Props {
  connection?: DbConnection | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'saved'): void
  (e: 'cancel'): void
}>()

const formRef = ref()
const loading = ref(false)
const testLoading = ref(false)

const form = reactive<Omit<DbConnection, 'id' | 'created_at' | 'updated_at'>>({
  connection_name: '',
  host: '',
  manage_host: '',
  port: 3306,
  username: '',
  password: '',
  is_enabled: true
})

// Store original values to track changes
const originalForm = ref<Partial<Omit<DbConnection, 'id' | 'created_at' | 'updated_at'>>>({})

const rules = {
  connection_name: [{ required: true, message: '请输入连接名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    {
      required: computed(() => !props.connection),
      message: '请输入密码',
      trigger: 'blur'
    }
  ]
}

const connection = computed(() => props.connection)

// Initialize form and store original values
function initForm() {
  if (connection.value) {
    form.connection_name = connection.value.connection_name
    form.host = connection.value.host
    form.manage_host = connection.value.manage_host || ''
    form.port = connection.value.port
    form.username = connection.value.username
    form.is_enabled = connection.value.is_enabled
    form.password = ''

    // Store original values for change tracking
    originalForm.value = {
      connection_name: connection.value.connection_name,
      host: connection.value.host,
      manage_host: connection.value.manage_host || '',
      port: connection.value.port,
      username: connection.value.username,
      is_enabled: connection.value.is_enabled
    }
  } else {
    // Reset form for new connection
    form.connection_name = ''
    form.host = ''
    form.manage_host = ''
    form.port = 3306
    form.username = ''
    form.password = ''
    form.is_enabled = true
    originalForm.value = {}
  }
}

// Get only changed fields for update
function getChangedFields(): Partial<Omit<DbConnection, 'id' | 'created_at' | 'updated_at'>> {
  if (!connection.value) {
    // For new connections, return all fields
    return { ...form }
  }

  const changes: Partial<Omit<DbConnection, 'id' | 'created_at' | 'updated_at'>> = {}

  // Check each field for changes
  if (form.connection_name !== originalForm.value.connection_name) {
    changes.connection_name = form.connection_name
  }
  if (form.host !== originalForm.value.host) {
    changes.host = form.host
  }
  if (form.manage_host !== originalForm.value.manage_host) {
    changes.manage_host = form.manage_host
  }
  if (form.port !== originalForm.value.port) {
    changes.port = form.port
  }
  if (form.username !== originalForm.value.username) {
    changes.username = form.username
  }
  if (form.password) {
    // Only include password if it's not empty
    changes.password = form.password
  }
  if (form.is_enabled !== originalForm.value.is_enabled) {
    changes.is_enabled = form.is_enabled
  }

  return changes
}

// Initialize form on mount and when connection prop changes
watch(() => props.connection, initForm, { immediate: true })

async function handleTest() {
  // 先验证表单
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  if (!form.connection_name || !form.host || !form.username) {
    ElMessage.warning('请填写完整的连接信息')
    return
  }

  // 如果是编辑模式且没有填写密码，需要提示用户先填写密码
  if (connection.value && !form.password) {
    ElMessage.warning('测试连接需要填写密码')
    return
  }

  if (!connection.value && !form.password) {
    ElMessage.warning('测试连接需要填写密码')
    return
  }

  // 直接测试连接信息，不创建或保存连接
  testLoading.value = true
  try {
    // 编辑模式和新增模式都直接测试，不保存
    await store.testConnectionDirectAction({
      host: form.host,
      port: form.port,
      username: form.username,
      password: form.password || ''
    })
  } finally {
    testLoading.value = false
  }
}

async function handleSave() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    if (connection.value && connection.value.id) {
      // 编辑模式 - 只发送变更字段
      const changedFields = getChangedFields()
      await store.editConnection(connection.value.id, changedFields)
    } else {
      // 新增模式 - 发送所有字段
      await store.addConnection(form)
    }
    emit('saved')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.connection-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.connection-form :deep(.el-form-item__label) {
  line-height: 1.35;
  padding-bottom: 4px;
  color: #2a3d57;
  font-size: 12px;
  font-weight: 600;
}

.connection-form :deep(.el-input__wrapper),
.connection-form :deep(.el-input-number .el-input__wrapper) {
  min-height: 34px !important;
  padding: 0 10px;
}

.connection-form :deep(.el-input__inner),
.connection-form :deep(.el-input-number__input) {
  line-height: 1.35;
  font-size: 13px;
}

.connection-form :deep(.el-input__inner::placeholder),
.connection-form :deep(.el-input-number__input::placeholder) {
  color: #9aa4b2;
  opacity: 1;
}

.connection-form :deep(.el-form-item__error) {
  display: none;
}
</style>
