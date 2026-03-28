import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

const request: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 120000
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
    const res = response.data
    if (!res.success) {
      ElMessage.error(res.error || '请求失败')
      return Promise.reject(new Error(res.error || '请求失败'))
    }
    return res
  },
  (error) => {
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
