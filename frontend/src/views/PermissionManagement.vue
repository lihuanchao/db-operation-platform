<template>
  <AppLayout>
    <div class="permission-page">
      <div class="page-header">
        <h2>权限管理</h2>
      </div>

      <div class="permission-shell">
        <el-card shadow="never" class="panel-card">
          <div class="panel-body">
            <div class="panel-head">
              <div>
                <h3>用户列表</h3>
              </div>
              <el-input
                v-model="userKeyword"
                placeholder="搜索姓名/工号"
                clearable
                class="panel-search"
              />
            </div>

            <div v-if="userStore.loading" v-loading="true" class="user-list user-list--loading"></div>
            <div v-else-if="filteredUsers.length === 0" class="panel-empty panel-empty--stretch">
              {{ userEmptyText }}
            </div>
            <div v-else class="user-list" role="list">
              <div class="list-head list-head--user">
                <span>用户名</span>
                <span>工号</span>
                <span>部门</span>
              </div>
              <button
                v-for="user in filteredUsers"
                :key="user.id"
                type="button"
                class="user-card"
                :class="{ 'is-active': user.id === currentUserId, 'is-admin': user.role_code === 'admin' }"
                @click="handleSelectUser(user)"
              >
                <span class="list-cell user-card__name">{{ user.real_name }}</span>
                <span class="list-cell">{{ user.employee_no }}</span>
                <span class="list-cell">{{ user.department }}</span>
              </button>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card">
          <div class="panel-body">
            <div class="panel-head">
              <div>
                <h3>连接授权</h3>
                <p>{{ filteredConnections.length }} 项匹配结果</p>
              </div>
              <div class="panel-head-actions">
                <el-input
                  v-model="connectionKeyword"
                  placeholder="搜索连接名称/主机地址"
                  clearable
                  class="panel-search"
                />
                <el-button
                  type="primary"
                  class="permission-save"
                  :disabled="!canSave"
                  :loading="saveLoading"
                  @click="save"
                >
                  保存授权
                </el-button>
              </div>
            </div>

            <div v-if="!selectedUser" class="panel-empty panel-empty--stretch">
              请选择左侧普通用户进行授权
            </div>
            <template v-else>
              <div class="selection-summary">
                <div>
                  <p class="summary-label">当前用户</p>
                  <strong class="summary-name">{{ currentUserLabel }}</strong>
                </div>
                <span class="summary-count">已授权 {{ grantedCount }} 项</span>
              </div>

              <div v-if="filteredConnections.length === 0" class="panel-empty panel-empty--stretch">
                {{ connectionEmptyText }}
              </div>
              <div v-else class="connection-list" role="list">
                <div class="list-head list-head--connection">
                  <span>连接名称</span>
                  <span>主机地址</span>
                  <span>选择</span>
                </div>
                <div
                  v-for="connection in filteredConnections"
                  :key="connection.id"
                  class="connection-card"
                  :class="{ 'is-selected': isConnectionSelected(connection.id) }"
                  tabindex="0"
                  role="checkbox"
                  :aria-checked="isConnectionSelected(connection.id)"
                  @click="toggleConnection(connection.id)"
                  @keydown.enter.prevent="toggleConnection(connection.id)"
                  @keydown.space.prevent="toggleConnection(connection.id)"
                >
                  <span class="list-cell connection-card__title">{{ connection.connection_name }}</span>
                  <span class="list-cell connection-card__host">{{ connection.host || '-' }}</span>
                  <span class="connection-card__marker" aria-hidden="true"></span>
                </div>
              </div>
            </template>
          </div>
        </el-card>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import AppLayout from '@/components/Layout/AppLayout.vue'
import { usePermissionAdminStore } from '@/stores/permissionAdmin'
import { useUserAdminStore } from '@/stores/userAdmin'
import type { SysUser } from '@/types'

const permissionStore = usePermissionAdminStore()
const userStore = useUserAdminStore()
const currentUserId = ref<number | null>(null)
const saveLoading = ref(false)
const userKeyword = ref('')
const connectionKeyword = ref('')

const filteredUsers = computed(() => {
  const text = userKeyword.value.trim().toLowerCase()
  if (!text) return userStore.list

  return userStore.list.filter((item) =>
    `${item.real_name} ${item.employee_no}`.toLowerCase().includes(text)
  )
})

const filteredConnections = computed(() => {
  const text = connectionKeyword.value.trim().toLowerCase()
  if (!text) return permissionStore.connections

  return permissionStore.connections.filter((item) =>
    `${item.connection_name} ${item.host || ''}`.toLowerCase().includes(text)
  )
})

const selectedUser = computed(
  () => userStore.list.find((item) => item.id === currentUserId.value) ?? null
)

const currentUserLabel = computed(() =>
  selectedUser.value ? `${selectedUser.value.real_name}（${selectedUser.value.employee_no}）` : ''
)

const selectedConnectionSet = computed(() => new Set(permissionStore.selectedConnectionIds))
const grantedCount = computed(() => permissionStore.selectedConnectionIds.length)
const canSave = computed(() => currentUserId.value !== null)

const userEmptyText = computed(() =>
  userKeyword.value.trim() ? '未匹配到用户，请调整搜索条件' : '暂无可授权用户'
)

const connectionEmptyText = computed(() =>
  connectionKeyword.value.trim() ? '未匹配到连接，请调整搜索条件' : '当前没有可授权的数据库连接'
)

onMounted(async () => {
  await userStore.fetchList()
  await permissionStore.fetchConnections()
})

async function handleSelectUser(row: SysUser) {
  if (row.role_code === 'admin') {
    currentUserId.value = null
    permissionStore.selectedConnectionIds = []
    ElMessage.info('管理员默认拥有全部权限，无需单独授权')
    return
  }

  currentUserId.value = row.id
  await permissionStore.loadUserPermissions(row.id)
}

function setSelectedConnectionIds(nextIds: number[]) {
  permissionStore.selectedConnectionIds = Array.from(new Set(nextIds))
}

function isConnectionSelected(connectionId?: number) {
  if (typeof connectionId !== 'number') return false
  return selectedConnectionSet.value.has(connectionId)
}

function toggleConnection(connectionId?: number) {
  if (!canSave.value || typeof connectionId !== 'number') return

  if (selectedConnectionSet.value.has(connectionId)) {
    setSelectedConnectionIds(
      permissionStore.selectedConnectionIds.filter((item) => item !== connectionId)
    )
    return
  }

  setSelectedConnectionIds([...permissionStore.selectedConnectionIds, connectionId])
}

async function save() {
  if (!currentUserId.value) return

  saveLoading.value = true
  try {
    await permissionStore.saveUserPermissions(currentUserId.value)
    ElMessage.success('授权已保存')
  } finally {
    saveLoading.value = false
  }
}
</script>

<style scoped>
.permission-page {
  height: calc(100dvh - 86px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  margin-bottom: 6px;
  flex-shrink: 0;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f2a3d;
}

.permission-shell {
  display: grid;
  grid-template-columns: minmax(260px, 0.92fr) minmax(360px, 1.28fr);
  gap: 12px;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}

.panel-card {
  height: 100%;
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 42, 61, 0.06);
}

.panel-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 16px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  padding: 9px 10px;
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #f8fbfd;
}

.panel-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #0f2a3d;
}

.panel-head p {
  margin: 2px 0 0;
  color: #6b7c8f;
  font-size: 12px;
}

.panel-search {
  width: 200px;
  flex-shrink: 0;
}

.panel-head-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.user-list,
.connection-list {
  display: flex;
  flex-direction: column;
  border: 1px solid #d9e6f2;
  border-radius: 8px;
  background: #ffffff;
  gap: 0;
  min-height: 0;
  overflow: auto;
  padding-right: 0;
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.user-list::-webkit-scrollbar,
.connection-list::-webkit-scrollbar {
  display: none;
}

.user-list--loading {
  min-height: 220px;
}

.list-head {
  position: sticky;
  top: 0;
  z-index: 2;
  display: grid;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fbfd;
  color: #5f7287;
  font-size: 12px;
  font-weight: 700;
}

.list-head--user,
.user-card {
  grid-template-columns: minmax(96px, 1fr) minmax(84px, 0.95fr) minmax(96px, 1fr);
}

.list-head--connection,
.connection-card {
  grid-template-columns: minmax(0, 1fr) minmax(110px, 0.9fr) 24px;
}

.list-cell {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.user-card {
  display: grid;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-height: 42px;
  padding: 0 12px;
  border: none;
  border-bottom: 1px solid #edf2f7;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease;
}

.user-card:hover {
  background: #f8fbff;
  transform: none;
}

.user-card:focus-visible {
  outline: none;
  border-color: #0369a1;
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.16);
}

.user-card.is-active {
  background: #eef6ff;
  box-shadow: inset 3px 0 0 #0284c7;
}

.user-card.is-admin {
  background: #fbfcfe;
}

.user-card__name {
  color: #0f2a3d;
  font-size: 13px;
  font-weight: 700;
}

.panel-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  border: 1px dashed #d9e6f2;
  border-radius: 8px;
  background: #f8fbfd;
  color: #6b7c8f;
  text-align: center;
  line-height: 1.6;
}

.panel-empty--stretch {
  flex: 1;
  min-height: 220px;
}

.selection-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f0f7ff;
}

.summary-label {
  margin: 0 0 2px;
  color: #5f7287;
  font-size: 11px;
}

.summary-name {
  color: #0f2a3d;
  font-size: 14px;
  font-weight: 700;
}

.summary-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  padding: 6px 8px;
  border-radius: 8px;
  background: #ffffff;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
}

.connection-list {
  flex: 1;
  margin-bottom: 10px;
}

.connection-card {
  display: grid;
  align-items: center;
  gap: 6px;
  min-height: 42px;
  padding: 0 12px;
  border: none;
  border-bottom: 1px solid #edf2f7;
  background: #ffffff;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease;
}

.connection-card:hover {
  background: #f8fbff;
  transform: none;
}

.connection-card:focus-visible {
  outline: none;
  border-color: #0369a1;
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.16);
}

.connection-card.is-selected {
  background: #eef6ff;
  box-shadow: inset 3px 0 0 #0284c7;
}

.connection-card__title {
  color: #0f2a3d;
  font-size: 13px;
  font-weight: 700;
}

.connection-card__host {
  color: #64748b;
  font-size: 12px;
}

.connection-card__marker {
  position: relative;
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border: 2px solid #94a3b8;
  border-radius: 999px;
  background: #ffffff;
}

.connection-card.is-selected .connection-card__marker {
  border-color: #0369a1;
  background: #0369a1;
}

.connection-card.is-selected .connection-card__marker::after {
  content: '';
  position: absolute;
  inset: 4px;
  border-radius: 999px;
  background: #ffffff;
}

.user-card:last-child,
.connection-card:last-child {
  border-bottom: none;
}

.permission-save.el-button {
  min-width: 112px;
}

@media (max-width: 992px) {
  .permission-page {
    height: calc(100dvh - 82px);
  }

  .permission-shell {
    grid-template-columns: 1fr;
  }

  .panel-body {
    min-height: unset;
  }
}

@media (max-width: 768px) {
  .permission-page {
    height: calc(100dvh - 78px);
  }

  .panel-body {
    padding: 12px;
  }

  .panel-head,
  .selection-summary {
    align-items: stretch;
    flex-direction: column;
  }

  .panel-search {
    width: 100%;
  }

  .panel-head-actions {
    display: flex;
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
