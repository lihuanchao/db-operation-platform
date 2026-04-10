import request from './request'
import { ElMessage } from 'element-plus'
import type { SlowSQL, SlowSQLListResponse, FilterParams, OptimizeResult, ApiResponse } from '@/types'

export const getSlowSQLList = (params: Partial<FilterParams>) => {
  return request.get<SlowSQLListResponse, ApiResponse<SlowSQLListResponse>>('/slow-sqls', { params })
}

export const getSlowSQLDetail = (checksum: string) => {
  return request.get<SlowSQL, ApiResponse<SlowSQL>>(`/slow-sqls/${checksum}`)
}

export const optimizeSlowSQL = (checksum: string) => {
  return request.post<{
    suggestion: string
    writing_optimization?: string
    index_recommendation?: string
    optimized_content?: string | null
    matched_rules?: string
  }, ApiResponse<{
    suggestion: string
    writing_optimization?: string
    index_recommendation?: string
    optimized_content?: string | null
    matched_rules?: string
  }>>(`/slow-sqls/${checksum}/optimize`)
}

export const batchOptimizeSlowSQLs = (ids: string[]) => {
  return request.post<{ results: OptimizeResult[] }, ApiResponse<{ results: OptimizeResult[] }>>('/slow-sqls/batch-optimize', { ids })
}

export const downloadSlowSQL = async (checksum: string) => {
  try {
    const response = await fetch(`/api/slow-sqls/${checksum}/download`, {
      method: 'GET'
    })

    if (!response.ok) {
      let message = '下载失败，请稍后重试'
      try {
        const data = await response.json()
        if (data?.error) {
          message = data.error
        }
      } catch {
        // ignore json parse error and keep fallback message
      }
      throw new Error(message)
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url

    const contentDisposition = response.headers.get('Content-Disposition')
    let fileName = `slow_sql_${checksum}_optimization.md`
    if (contentDisposition) {
      const matches = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (matches != null && matches[1]) {
        fileName = decodeURIComponent(matches[1].replace(/['"]/g, ''))
      }
    }

    a.download = fileName
    document.body.appendChild(a)
    a.click()

    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    ElMessage.success('下载成功')
  } catch (error) {
    console.error('下载错误:', error)
    ElMessage.error(error instanceof Error ? error.message : '下载失败，请稍后重试')
  }
}

export const batchDownloadSlowSQLs = (ids: string[]) => {
  // 使用 Fetch API 发送 POST 请求下载
  fetch('/api/slow-sqls/batch-download', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ ids })
  })
  .then(response => {
    if (!response.ok) {
      throw new Error('下载失败')
    }
    // 保存 response 对象以便在下一步访问 headers
    return Promise.all([response.blob(), response])
  })
  .then(([blob, response]) => {
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url

    // 从响应头获取文件名
    const contentDisposition = response.headers.get('Content-Disposition')
    let fileName = 'slow_sql_batch.csv'
    if (contentDisposition) {
      const matches = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (matches != null && matches[1]) {
        fileName = decodeURIComponent(matches[1].replace(/['"]/g, ''))
      }
    }

    a.download = fileName
    document.body.appendChild(a)
    a.click()

    // 清理
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
    ElMessage.success('下载成功')
  })
  .catch(error => {
    console.error('下载错误:', error)
    ElMessage.error('下载失败，请稍后重试')
  })
}
