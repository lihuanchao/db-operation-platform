import type { ApiResponse, SysUser } from '@/types'
import request from './request'

export const getUserList = () =>
  request.get<{ items: SysUser[] }, ApiResponse<{ items: SysUser[] }>>('/admin/users')

export const createUser = (data: {
  employee_no: string
  password: string
  real_name: string
  department: string
  role_code: 'admin' | 'user'
  status: 'enabled' | 'disabled'
}) =>
  request.post<SysUser, ApiResponse<SysUser>>('/admin/users', data)

export const updateUser = (id: number, data: {
  real_name: string
  department: string
  role_code: 'admin' | 'user'
  status: 'enabled' | 'disabled'
}) =>
  request.put<SysUser, ApiResponse<SysUser>>(`/admin/users/${id}`, data)

export const updateUserStatus = (id: number, status: 'enabled' | 'disabled') =>
  request.put<SysUser, ApiResponse<SysUser>>(`/admin/users/${id}/status`, { status })

export const resetUserPassword = (id: number, password: string) =>
  request.put<SysUser, ApiResponse<SysUser>>(`/admin/users/${id}/reset-password`, { password })

export const deleteUser = (id: number) =>
  request.delete<{ deleted: boolean }, ApiResponse<{ deleted: boolean }>>(`/admin/users/${id}`)
