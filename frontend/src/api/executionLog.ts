import axios from 'axios'
import request from './request'
import type {
  ApiResponse,
  ExecutionLog,
  ExecutionLogListResponse,
  ExecutionLogType
} from '@/types'

const downloadHeaders = {
  'Cache-Control': 'no-cache, no-store, must-revalidate',
  Pragma: 'no-cache',
  Expires: '0'
}

export const getExecutionLogList = (params?: {
  page?: number
  per_page?: number
  task_id?: number
  task_name?: string
  status?: number
  log_type?: ExecutionLogType | ''
}) => {
  return request.get<ExecutionLogListResponse, ApiResponse<ExecutionLogListResponse>>('/execution-logs', { params })
}

export const getExecutionLog = (id: number) => {
  return request.get<ExecutionLog, ApiResponse<ExecutionLog>>(`/execution-logs/${id}`)
}

export function downloadExecutionLog(id: number): Promise<any>
export function downloadExecutionLog(logType: ExecutionLogType, id: number, options?: { artifactId?: string }): Promise<any>
export function downloadExecutionLog(
  logTypeOrId: ExecutionLogType | number,
  idOrOptions?: number | { artifactId?: string },
  options?: { artifactId?: string }
) {
  if (typeof logTypeOrId === 'number') {
    return axios.get(`/api/execution-logs/${logTypeOrId}/download`, {
      responseType: 'blob',
      headers: downloadHeaders
    })
  }

  const id = typeof idOrOptions === 'number' ? idOrOptions : undefined
  const artifactId = typeof idOrOptions === 'object' ? idOrOptions?.artifactId : options?.artifactId
  if (!id) {
    return Promise.reject(new Error('id is required'))
  }

  return axios.get(`/api/execution-logs/${logTypeOrId}/${id}/download`, {
    responseType: 'blob',
    params: artifactId ? { artifact_id: artifactId } : undefined,
    headers: {
      ...downloadHeaders
    }
  })
}

export function getLogContent(id: number): Promise<ApiResponse<{ content: string; has_file: boolean }>>
export function getLogContent(logType: ExecutionLogType, id: number): Promise<ApiResponse<{ content: string; has_file: boolean }>>
export function getLogContent(logTypeOrId: ExecutionLogType | number, id?: number) {
  if (typeof logTypeOrId === 'number') {
    return request.get<{ content: string; has_file: boolean }, ApiResponse<{ content: string; has_file: boolean }>>(
      `/execution-logs/${logTypeOrId}/log-content`
    )
  }

  if (!id) {
    return Promise.reject(new Error('id is required'))
  }

  return request.get<{ content: string; has_file: boolean }, ApiResponse<{ content: string; has_file: boolean }>>(
    `/execution-logs/${logTypeOrId}/${id}/log-content`
  )
}
