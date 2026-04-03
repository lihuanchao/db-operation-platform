import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getConnectionList } from '@/api/dbConnection'
import { getRoles, getUserConnectionPermissions, saveUserConnectionPermissions } from '@/api/permissionAdmin'
import type { DbConnection, RoleSpec } from '@/types'

export const usePermissionAdminStore = defineStore('permissionAdmin', () => {
  const roles = ref<RoleSpec[]>([])
  const connections = ref<DbConnection[]>([])
  const selectedConnectionIds = ref<number[]>([])

  async function fetchRoles() {
    const res = await getRoles()
    roles.value = res.data ?? []
  }

  async function fetchConnections() {
    const res = await getConnectionList({ page: 1, per_page: 1000 })
    connections.value = (res.data?.items ?? []).filter((item) => item.is_enabled)
  }

  async function loadUserPermissions(userId: number) {
    const res = await getUserConnectionPermissions(userId)
    selectedConnectionIds.value = res.data?.connection_ids ?? []
  }

  async function saveUserPermissions(userId: number) {
    await saveUserConnectionPermissions(userId, selectedConnectionIds.value)
  }

  return {
    roles,
    connections,
    selectedConnectionIds,
    fetchRoles,
    fetchConnections,
    loadUserPermissions,
    saveUserPermissions
  }
})
