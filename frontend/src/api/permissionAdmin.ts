import type { ApiResponse, RoleSpec } from '@/types'
import request from './request'

export const getRoles = () =>
  request.get<RoleSpec[], ApiResponse<RoleSpec[]>>('/admin/roles')

export const getUserConnectionPermissions = (userId: number) =>
  request.get<{ connection_ids: number[] }, ApiResponse<{ connection_ids: number[] }>>(`/admin/user-connection-permissions/${userId}`)

export const saveUserConnectionPermissions = (userId: number, connectionIds: number[]) =>
  request.put<{ connection_ids: number[] }, ApiResponse<{ connection_ids: number[] }>>(
    `/admin/user-connection-permissions/${userId}`,
    { connection_ids: connectionIds }
  )
