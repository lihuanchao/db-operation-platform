import request from './request'
import type {
  ApiResponse,
  OptimizationTask,
  OptimizationTaskListResponse,
  OptimizationTaskListQuery,
  CreateSqlOptimizationTaskPayload,
  CreateMyBatisOptimizationTaskPayload
} from '@/types'

export const getOptimizationTaskList = (params: OptimizationTaskListQuery) => {
  return request.get<OptimizationTaskListResponse, ApiResponse<OptimizationTaskListResponse>>('/optimization-tasks', { params })
}

export const getOptimizationTaskDetail = (id: number) => {
  return request.get<OptimizationTask, ApiResponse<OptimizationTask>>(`/optimization-tasks/${id}`)
}

export const createSqlOptimizationTask = (data: CreateSqlOptimizationTaskPayload) => {
  return request.post<OptimizationTask, ApiResponse<OptimizationTask>>('/optimization-tasks/sql', data)
}

export const createMyBatisOptimizationTask = (data: CreateMyBatisOptimizationTaskPayload) => {
  return request.post<OptimizationTask, ApiResponse<OptimizationTask>>('/optimization-tasks/mybatis', data)
}
