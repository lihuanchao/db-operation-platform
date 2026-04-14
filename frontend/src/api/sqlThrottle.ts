import request from './request'
import type {
  ApiResponse,
  SqlThrottleKillLog,
  SqlThrottleRule,
  SqlThrottleRuleListResponse,
  SqlThrottleRun,
  SqlThrottleRunListResponse
} from '@/types'

export interface SqlThrottleRulePayload {
  rule_name: string
  db_connection_id: number
  enabled: boolean
  slow_sql_seconds: number
  fingerprint_concurrency_threshold: number
  poll_interval_seconds: number
  max_kill_per_round: number
  consecutive_hit_times: number
  dry_run: boolean
  target_db_pattern?: string
  target_user_pattern?: string
  exclude_users?: string[]
  exclude_hosts?: string[]
  exclude_dbs?: string[]
  exclude_fingerprints?: string[]
}

export const getSqlThrottleRuleList = (params?: {
  page?: number
  per_page?: number
  rule_name?: string
  enabled?: boolean
  db_connection_id?: number
}) => {
  return request.get<SqlThrottleRuleListResponse, ApiResponse<SqlThrottleRuleListResponse>>('/sql-throttle-rules', { params })
}

export const createSqlThrottleRule = (payload: SqlThrottleRulePayload) => {
  return request.post<SqlThrottleRule, ApiResponse<SqlThrottleRule>>('/sql-throttle-rules', payload)
}

export const getSqlThrottleRule = (id: number) => {
  return request.get<SqlThrottleRule, ApiResponse<SqlThrottleRule>>(`/sql-throttle-rules/${id}`)
}

export const updateSqlThrottleRule = (id: number, payload: Partial<SqlThrottleRulePayload>) => {
  return request.put<SqlThrottleRule, ApiResponse<SqlThrottleRule>>(`/sql-throttle-rules/${id}`, payload)
}

export const deleteSqlThrottleRule = (id: number) => {
  return request.delete<{ id: number }, ApiResponse<{ id: number }>>(`/sql-throttle-rules/${id}`)
}

export const enableSqlThrottleRule = (id: number) => {
  return request.post<SqlThrottleRule, ApiResponse<SqlThrottleRule>>(`/sql-throttle-rules/${id}/enable`)
}

export const disableSqlThrottleRule = (id: number) => {
  return request.post<SqlThrottleRule, ApiResponse<SqlThrottleRule>>(`/sql-throttle-rules/${id}/disable`)
}

export const runOnceSqlThrottleRule = (id: number) => {
  return request.post<SqlThrottleRun, ApiResponse<SqlThrottleRun>>(`/sql-throttle-rules/${id}/run-once`)
}

export const getSqlThrottleRunList = (params?: {
  page?: number
  per_page?: number
  rule_name?: string
  is_hit?: boolean
  status?: string
}) => {
  return request.get<SqlThrottleRunListResponse, ApiResponse<SqlThrottleRunListResponse>>('/sql-throttle-runs', { params })
}

export const getSqlThrottleRun = (id: number) => {
  return request.get<SqlThrottleRun, ApiResponse<SqlThrottleRun>>(`/sql-throttle-runs/${id}`)
}

export const getSqlThrottleRunKillLogs = (id: number) => {
  return request.get<{ items: SqlThrottleKillLog[] }, ApiResponse<{ items: SqlThrottleKillLog[] }>>(
    `/sql-throttle-runs/${id}/kill-logs`
  )
}

export const getSqlThrottleRunSnapshot = (id: number) => {
  return request.get<{ snapshot: Record<string, unknown> }, ApiResponse<{ snapshot: Record<string, unknown> }>>(
    `/sql-throttle-runs/${id}/snapshot`
  )
}
