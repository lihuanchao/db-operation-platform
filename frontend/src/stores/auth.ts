import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { AuthMenuItem, AuthUser, DbConnection, LoginPayload, RoleCode } from '@/types'
import { getAuthorizedConnections, getCurrentUser, login as loginApi, logout as logoutApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const menus = ref<AuthMenuItem[]>([])
  const initialized = ref(false)
  const authorizedConnections = ref<DbConnection[]>([])

  const isAuthenticated = computed(() => !!user.value)
  const roleCode = computed<RoleCode>(() => user.value?.role_code ?? 'user')
  const homePath = computed(() => '/optimization-tasks')

  async function login(payload: LoginPayload) {
    const res = await loginApi(payload)
    if (res.data) {
      user.value = res.data.user
      menus.value = res.data.menus
      initialized.value = true
    }
  }

  async function restore() {
    try {
      const res = await getCurrentUser()
      if (res.data) {
        user.value = res.data.user
        menus.value = res.data.menus
      } else {
        user.value = null
        menus.value = []
      }
    } catch {
      user.value = null
      menus.value = []
    } finally {
      initialized.value = true
    }
  }

  async function fetchAuthorizedConnections() {
    const res = await getAuthorizedConnections()
    authorizedConnections.value = res.data?.items ?? []
  }

  async function logout() {
    try {
      await logoutApi()
    } finally {
      clear()
    }
  }

  function clear() {
    user.value = null
    menus.value = []
    authorizedConnections.value = []
    initialized.value = true
  }

  return {
    user,
    menus,
    initialized,
    authorizedConnections,
    isAuthenticated,
    roleCode,
    homePath,
    login,
    restore,
    fetchAuthorizedConnections,
    logout,
    clear
  }
})
