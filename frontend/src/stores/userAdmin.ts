import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createUser,
  deleteUser,
  getUserList,
  resetUserPassword,
  updateUser,
  updateUserStatus
} from '@/api/userAdmin'
import type { SysUser } from '@/types'

interface UserPayload {
  employee_no: string
  password: string
  real_name: string
  department: string
  role_code: 'admin' | 'user'
  status: 'enabled' | 'disabled'
}

interface UserUpdatePayload {
  real_name: string
  department: string
  role_code: 'admin' | 'user'
  status: 'enabled' | 'disabled'
}

export const useUserAdminStore = defineStore('userAdmin', () => {
  const list = ref<SysUser[]>([])
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const res = await getUserList()
      list.value = res.data?.items ?? []
    } finally {
      loading.value = false
    }
  }

  async function addUser(payload: UserPayload) {
    await createUser(payload)
    await fetchList()
  }

  async function editUser(id: number, payload: UserUpdatePayload) {
    await updateUser(id, payload)
    await fetchList()
  }

  async function setUserStatus(id: number, status: 'enabled' | 'disabled') {
    await updateUserStatus(id, status)
    await fetchList()
  }

  async function updatePassword(id: number, password: string) {
    await resetUserPassword(id, password)
  }

  async function removeUser(id: number) {
    await deleteUser(id)
    await fetchList()
  }

  return {
    list,
    loading,
    fetchList,
    addUser,
    editUser,
    setUserStatus,
    updatePassword,
    removeUser
  }
})
