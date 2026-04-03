import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

const request: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 120000,
  withCredentials: true
})

// Request interceptor
request.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
request.interceptors.response.use(
  (response: AxiosResponse) => {
    // 对于 blob 类型的响应，直接返回 response
    if (response.config.responseType === 'blob') {
      return response
    }
    // 对于普通 JSON 响应
    const res = response.data
    if (!res.success) {
      ElMessage.error(res.error || '请求失败')
      return Promise.reject(new Error(res.error || '请求失败'))
    }
    return res
  },
  (error) => {
    if (error.response?.status === 401) {
      Promise.all([import('@/stores'), import('@/stores/auth')]).then(([{ pinia }, authModule]) => {
        authModule.useAuthStore(pinia).clear()
      }).catch(() => {
        // ignore dynamic import errors, redirect is enough
      })
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    // Try to get custom error message from server response
    let errorMessage = error.message || '网络错误'
    if (error.response && error.response.data && error.response.data.error) {
      errorMessage = error.response.data.error
    }
    ElMessage.error(errorMessage)
    return Promise.reject(error)
  }
)

export default request
