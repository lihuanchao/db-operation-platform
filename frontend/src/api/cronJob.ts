import request from './request'
import type { CronJob, CronJobListResponse, ApiResponse } from '@/types'

export const getCronJobList = (params?: {
  page?: number
  per_page?: number
  task_id?: number
}) => {
  return request.get<CronJobListResponse, ApiResponse<CronJobListResponse>>('/cron-jobs', { params })
}

export const getCronJob = (id: number) => {
  return request.get<CronJob, ApiResponse<CronJob>>(`/cron-jobs/${id}`)
}

export const createCronJob = (data: Omit<CronJob, 'id' | 'created_at' | 'updated_at' | 'next_run_time' | 'last_run_time'>) => {
  return request.post<CronJob, ApiResponse<CronJob>>('/cron-jobs', data)
}

export const updateCronJob = (id: number, data: Partial<Omit<CronJob, 'id' | 'created_at' | 'updated_at'>>) => {
  return request.put<CronJob, ApiResponse<CronJob>>(`/cron-jobs/${id}`, data)
}

export const deleteCronJob = (id: number) => {
  return request.delete<{ id: number }, ApiResponse<{ id: number }>>(`/cron-jobs/${id}`)
}

export const toggleCronJob = (id: number) => {
  return request.post<CronJob, ApiResponse<CronJob>>(`/cron-jobs/${id}/toggle`)
}
