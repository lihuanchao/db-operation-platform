import axios from 'axios'
import request from './request'
import { downloadExecutionLog, getLogContent } from './executionLog'
import type {
  ApiResponse,
  CreateFlashbackTaskPayload,
  FlashbackTask,
  FlashbackTaskArtifact,
  FlashbackTaskListQuery,
  FlashbackTaskListResponse
} from '@/types'

const downloadHeaders = {
  'Cache-Control': 'no-cache, no-store, must-revalidate',
  Pragma: 'no-cache',
  Expires: '0'
}

export const getFlashbackTaskList = (params?: Partial<FlashbackTaskListQuery>) => {
  return request.get<FlashbackTaskListResponse, ApiResponse<FlashbackTaskListResponse>>('/flashback-tasks', { params })
}

export const createFlashbackTask = (data: CreateFlashbackTaskPayload) => {
  return request.post<FlashbackTask, ApiResponse<FlashbackTask>>('/flashback-tasks', data)
}

export const getFlashbackTask = (id: number) => {
  return request.get<FlashbackTask, ApiResponse<FlashbackTask>>(`/flashback-tasks/${id}`)
}

export const getFlashbackTaskArtifacts = (id: number) => {
  return request.get<{ items: FlashbackTaskArtifact[] }, ApiResponse<{ items: FlashbackTaskArtifact[] }>>(
    `/flashback-tasks/${id}/artifacts`
  )
}

export const downloadFlashbackTaskArtifact = (id: number, artifactId: string) => {
  return axios.get(`/api/flashback-tasks/${id}/artifacts/${artifactId}/download`, {
    responseType: 'blob',
    headers: downloadHeaders
  })
}

export const getFlashbackTaskLogContent = (id: number) => {
  return getLogContent('flashback', id)
}

export const downloadFlashbackTaskLog = (id: number) => {
  return downloadExecutionLog('flashback', id)
}
