import request from './request'
import type { DbConnection, DbConnectionListResponse, ApiResponse } from '@/types'

export const getConnectionList = (params?: {
  page?: number
  per_page?: number
  connection_name?: string
  host?: string
}) => {
  return request.get<DbConnectionListResponse, ApiResponse<DbConnectionListResponse>>('/connections', { params })
}

export const getConnection = (id: number) => {
  return request.get<DbConnection, ApiResponse<DbConnection>>(`/connections/${id}`)
}

export const createConnection = (data: Omit<DbConnection, 'id' | 'created_at' | 'updated_at'>) => {
  return request.post<DbConnection, ApiResponse<DbConnection>>('/connections', data)
}

export const updateConnection = (id: number, data: Partial<Omit<DbConnection, 'id' | 'created_at' | 'updated_at'>>) => {
  return request.put<DbConnection, ApiResponse<DbConnection>>(`/connections/${id}`, data)
}

export const deleteConnection = (id: number) => {
  return request.delete<{ id: number }, ApiResponse<{ id: number }>>(`/connections/${id}`)
}

export const testConnection = (id: number) => {
  return request.post<{ success: boolean; message: string }, ApiResponse<{ success: boolean; message: string }>>(`/connections/${id}/test`)
}

export const testConnectionDirect = (data: {
  host: string
  port: number
  username: string
  password: string
}) => {
  return request.post<{ success: boolean; message: string }, ApiResponse<{ success: boolean; message: string }>>('/connections/test-direct', data)
}
