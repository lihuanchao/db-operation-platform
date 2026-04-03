import type { ApiResponse, AuthPayload, DbConnection, LoginPayload } from '@/types'
import request from './request'

export const login = (data: LoginPayload) =>
  request.post<AuthPayload, ApiResponse<AuthPayload>>('/auth/login', data)

export const logout = () =>
  request.post<{ logged_out: boolean }, ApiResponse<{ logged_out: boolean }>>('/auth/logout')

export const getCurrentUser = () =>
  request.get<AuthPayload, ApiResponse<AuthPayload>>('/auth/me')

export const getAuthorizedConnections = () =>
  request.get<{ items: DbConnection[] }, ApiResponse<{ items: DbConnection[] }>>('/auth/connections')
