<template>
  <AppLayout>
    <div class="page-header">
      <h2>权限管理</h2>
      <p>为普通用户分配可访问的数据库连接</p>
    </div>

    <div class="permission-shell">
      <el-card shadow="never" class="panel-card">
        <div class="panel-body">
          <div class="panel-head">
            <div>
              <h3>用户列表</h3>
              <p>{{ filteredUsers.length }} 位可见用户</p>
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
            <button
              v-for="user in filteredUsers"
              :key="user.id"
              type="button"
              class="user-card"
              :class="{ 'is-active': user.id === currentUserId, 'is-admin': user.role_code === 'admin' }"
              @click="handleSelectUser(user)"
            >
              <span class="user-card__copy">
                <strong class="user-card__name">{{ user.real_name }}</strong>
                <span class="user-card__meta">{{ user.employee_no }} · {{ user.department }}</span>
              </span>
              <span
                class="user-card__badge"
                :class="{ 'is-admin': user.role_code === 'admin', 'is-user': user.role_code !== 'admin' }"
              >
                {{ user.role_code === 'admin' ? '管理员' : '普通用户' }}
              </span>
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
            <el-input
              v-model="connectionKeyword"
              placeholder="搜索连接名/IP"
              clearable
              class="panel-search"
            />
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

            <div class="toolbar">
              <span class="toolbar-copy">点击卡片即可勾选或取消授权</span>
              <div class="toolbar-actions">
                <el-button
                  text
                  class="toolbar-button"
                  :disabled="filteredConnectionIds.length === 0"
                  @click="selectFilteredConnections"
                >
                  全选当前结果
                </el-button>
                <el-button
                  text
                  class="toolbar-button"
                  :disabled="filteredConnectionIds.length === 0"
                  @click="clearFilteredConnections"
                >
                  清空当前结果
                </el-button>
              </div>
            </div>

            <div v-if="filteredConnections.length === 0" class="panel-empty panel-empty--stretch">
              {{ connectionEmptyText }}
            </div>
            <div v-else class="connection-list" role="list">
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
                <div class="connection-card__copy">
                  <strong class="connection-card__title">{{ connection.connection_name }}</strong>
                  <span class="connection-card__meta">
                    {{ connection.manage_host || connection.host }}
                  </span>
                </div>
                <span class="connection-card__marker" aria-hidden="true"></span>
              </div>
            </div>
          </template>

          <div class="panel-footer">
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
      </el-card>
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
    `${item.connection_name} ${item.manage_host || item.host || ''}`.toLowerCase().includes(text)
  )
})

const filteredConnectionIds = computed(() =>
  filteredConnections.value
    .map((item) => item.id)
    .filter((id): id is number => typeof id === 'number')
)

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

function selectFilteredConnections() {
  if (!canSave.value) return
  setSelectedConnectionIds([...permissionStore.selectedConnectionIds, ...filteredConnectionIds.value])
}

function clearFilteredConnections() {
  if (!canSave.value) return

  const filteredIdSet = new Set(filteredConnectionIds.value)
  setSelectedConnectionIds(
    permissionStore.selectedConnectionIds.filter((item) => !filteredIdSet.has(item))
  )
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
.page-header {
  margin-bottom: 18px;
}

.page-header h2 {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #0f2a3d;
}

.page-header p {
  margin: 6px 0 0;
  color: #5f7287;
  font-size: 14px;
}

.permission-shell {
  display: grid;
  grid-template-columns: minmax(260px, 0.92fr) minmax(360px, 1.28fr);
  gap: 18px;
  align-items: stretch;
}

.panel-card {
  border: 1px solid #d9e6f2;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(15, 42, 61, 0.06);
}

.panel-body {
  display: flex;
  flex-direction: column;
  min-height: 620px;
  padding: 22px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.panel-head h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #0f2a3d;
}

.panel-head p {
  margin: 4px 0 0;
  color: #6b7c8f;
  font-size: 13px;
}

.panel-search {
  width: 220px;
  flex-shrink: 0;
}

.user-list,
.connection-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}

.user-list--loading {
  min-height: 220px;
}

.user-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 16px 18px;
  border: 1px solid #d9e6f2;
  border-radius: 16px;
  background: #f9fbfd;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease;
}

.user-card:hover {
  border-color: #bfd7ea;
  background: #ffffff;
  transform: translateY(-1px);
}

.user-card:focus-visible {
  outline: none;
  border-color: #0369a1;
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.16);
}

.user-card.is-active {
  border-color: #7dd3fc;
  background: #f0f7ff;
  box-shadow: 0 12px 30px rgba(14, 165, 233, 0.12);
}

.user-card.is-admin {
  background: #f7f9fc;
}

.user-card__copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.user-card__name {
  color: #0f2a3d;
  font-size: 15px;
  font-weight: 700;
}

.user-card__meta {
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}

.user-card__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.user-card__badge.is-user {
  background: #e0f2fe;
  color: #075985;
}

.user-card__badge.is-admin {
  background: #e2e8f0;
  color: #475569;
}

.panel-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  border: 1px dashed #d9e6f2;
  border-radius: 16px;
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
  gap: 16px;
  margin-bottom: 14px;
  padding: 16px 18px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: #f0f7ff;
}

.summary-label {
  margin: 0 0 6px;
  color: #5f7287;
  font-size: 12px;
}

.summary-name {
  color: #0f2a3d;
  font-size: 16px;
  font-weight: 700;
}

.summary-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  padding: 8px 12px;
  border-radius: 999px;
  background: #ffffff;
  color: #0369a1;
  font-size: 13px;
  font-weight: 700;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.toolbar-copy {
  color: #5f7287;
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.toolbar-button.el-button {
  margin: 0;
  color: #0369a1;
}

.connection-list {
  flex: 1;
  margin-bottom: 16px;
}

.connection-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid #d9e6f2;
  border-radius: 16px;
  background: #ffffff;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease;
}

.connection-card:hover {
  border-color: #bfd7ea;
  transform: translateY(-1px);
}

.connection-card:focus-visible {
  outline: none;
  border-color: #0369a1;
  box-shadow: 0 0 0 3px rgba(3, 105, 161, 0.16);
}

.connection-card.is-selected {
  border-color: #7dd3fc;
  background: #f0f9ff;
  box-shadow: 0 10px 24px rgba(14, 165, 233, 0.12);
}

.connection-card__copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.connection-card__title {
  color: #0f2a3d;
  font-size: 15px;
  font-weight: 700;
}

.connection-card__meta {
  color: #64748b;
  font-size: 13px;
  word-break: break-all;
}

.connection-card__marker {
  position: relative;
  flex-shrink: 0;
  width: 18px;
  height: 18px;
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

.panel-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, #ffffff 24%);
}

.permission-save.el-button {
  min-width: 112px;
}

@media (max-width: 992px) {
  .permission-shell {
    grid-template-columns: 1fr;
  }

  .panel-body {
    min-height: unset;
  }
}

@media (max-width: 768px) {
  .panel-body {
    padding: 18px;
  }

  .panel-head,
  .toolbar,
  .selection-summary {
    align-items: stretch;
    flex-direction: column;
  }

  .panel-search {
    width: 100%;
  }

  .toolbar-actions {
    width: 100%;
  }

  .toolbar-button.el-button {
    flex: 1;
  }

  .panel-footer {
    position: static;
    background: #ffffff;
  }
}
</style>
