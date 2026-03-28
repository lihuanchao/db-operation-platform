export interface SlowSQL {
  checksum: string
  host: string
  database_name: string
  user_max?: string
  sample: string
  last_seen: string | Date
  execution_count: number
  avg_time: number
  max_time?: number
  min_time?: number
  total_time?: number
  optimized_suggestion?: string | null
  is_optimized: number
  _selected?: boolean
}

export interface PaginationInfo {
  page: number
  per_page: number
  total: number
  total_pages: number
  has_prev: boolean
  has_next: boolean
  prev_num: number | null
  next_num: number | null
}

export interface SlowSQLListResponse {
  items: SlowSQL[]
  pagination: PaginationInfo
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
}

export interface FilterParams {
  database_name: string
  host: string
  is_optimized: string
  time_range: string
  ts_min: string
  ts_max: string
  page: number
  per_page: number
}

export interface OptimizeResult {
  id: string
  success: boolean
  suggestion?: string
  error?: string
}

export interface DbConnection {
  id?: number
  connection_name: string
  host: string
  manage_host?: string
  port: number
  username: string
  password?: string
  is_enabled: boolean
  created_at?: string
  updated_at?: string
  _selected?: boolean
}

export interface DbConnectionListResponse {
  items: DbConnection[]
  total: number
  page: number
  per_page: number
}

export interface ArchiveTask {
  id?: number
  task_name: string
  source_connection_id: number
  source_database: string
  source_table: string
  dest_connection_id?: number
  dest_database?: string
  dest_table?: string
  where_condition: string
  is_enabled: boolean
  created_at?: string
  updated_at?: string
  source_connection?: DbConnection
  dest_connection?: DbConnection
  _selected?: boolean
}

export interface ArchiveTaskListResponse {
  items: ArchiveTask[]
  total: number
  page: number
  per_page: number
}

export interface CronJob {
  id?: number
  task_id: number
  cron_expression: string
  next_run_time?: string
  last_run_time?: string
  is_active: boolean
  created_at?: string
  updated_at?: string
  _selected?: boolean
}

export interface CronJobListResponse {
  items: CronJob[]
  total: number
  page: number
  per_page: number
}

export interface ExecutionLog {
  id?: number
  task_id: number
  cron_job_id?: number
  start_time: string
  end_time?: string
  status: number
  log_file?: string
  error_message?: string
  created_at?: string
  _selected?: boolean
}

export interface ExecutionLogListResponse {
  items: ExecutionLog[]
  total: number
  page: number
  per_page: number
}
