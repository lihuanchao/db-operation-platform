import request from './request'
import type { ExecutionLog, ExecutionLogListResponse, ApiResponse } from '@/types'

export const getExecutionLogList = (params?: {
  page?: number
  per_page?: number
  task_id?: number
  status?: number
}) => {
  return request.get<ExecutionLogListResponse, ApiResponse<ExecutionLogListResponse>>('/execution-logs', { params })
}

export const getExecutionLog = (id: number) => {
  return request.get<ExecutionLog, ApiResponse<ExecutionLog>>(`/execution-logs/${id}`)
}

export const downloadExecutionLog = (id: number) => {
  return request.get<Blob, Blob>(`/execution-logs/${id}/download`, {
    responseType: 'blob'
  })
}

export const getLogContent = (id: number) => {
  return request.get<{ content: string; has_file: boolean }, ApiResponse<{ content: string; has_file: boolean }>>(`/execution-logs/${id}/log-content`)
}
