import request from './request'
import type { ArchiveTask, ArchiveTaskListResponse, ApiResponse } from '@/types'

export const getArchiveTaskList = (params?: {
  page?: number
  per_page?: number
  task_name?: string
  source_connection_id?: number
}) => {
  return request.get<ArchiveTaskListResponse, ApiResponse<ArchiveTaskListResponse>>('/archive-tasks', { params })
}

export const getArchiveTask = (id: number) => {
  return request.get<ArchiveTask, ApiResponse<ArchiveTask>>(`/archive-tasks/${id}`)
}

export const createArchiveTask = (data: Omit<ArchiveTask, 'id' | 'created_at' | 'updated_at' | 'source_connection' | 'dest_connection'>) => {
  return request.post<ArchiveTask, ApiResponse<ArchiveTask>>('/archive-tasks', data)
}

export const updateArchiveTask = (id: number, data: Partial<Omit<ArchiveTask, 'id' | 'created_at' | 'updated_at' | 'source_connection' | 'dest_connection'>>) => {
  return request.put<ArchiveTask, ApiResponse<ArchiveTask>>(`/archive-tasks/${id}`, data)
}

export const deleteArchiveTask = (id: number) => {
  return request.delete<{ id: number }, ApiResponse<{ id: number }>>(`/archive-tasks/${id}`)
}

export const executeArchiveTask = (id: number) => {
  return request.post<
    { log_id: number; log_file?: string; success?: boolean; message?: string; status?: string },
    ApiResponse<{ log_id: number; log_file?: string; success?: boolean; message?: string; status?: string }>
  >(`/archive-tasks/${id}/execute`)
}
