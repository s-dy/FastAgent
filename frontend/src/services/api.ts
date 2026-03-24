import axios from 'axios'
import type {
  TripPlanRequest,
  TripPlanResponse,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  User,
  UpdateProfileRequest,
  ChangePasswordRequest
} from '@/types'

// SSE 进度事件类型
export interface TripPlanProgressEvent {
  stage: string
  message: string
  progress: number
  result?: TripPlanResponse & { id: string; created_at: string }
}

// SSE 流式规划的回调类型
export interface TripPlanStreamCallbacks {
  onProgress: (event: TripPlanProgressEvent) => void
  onDone: (result: TripPlanResponse & { id: string; created_at: string }) => void
  onError: (message: string) => void
}

// 创建axios实例
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 300000, // 5分钟超时，为复杂的行程规划留足时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 自动添加认证令牌
apiClient.interceptors.request.use(
  (config) => {
    // 从localStorage获取token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 标志，防止多次登出操作
let isLoggingOut = false

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    // 阻止重复的登出操作
    if (isLoggingOut) {
      return Promise.reject(error)
    }
    
    // 如果是401错误，清除本地存储的认证信息
    if (error.response?.status === 401) {
      console.error('认证失败 (401):', {
        url: error.config?.url,
        method: error.config?.method,
        message: error.response?.data?.detail || '未授权访问',
        timestamp: new Date().toISOString()
      })
      
      // 检查是否是访问auth相关的API，如果是则不清除认证（可能是密码错误等）
      const isAuthAPI = error.config?.url?.includes('/auth/')
      
      if (!isAuthAPI) {
        isLoggingOut = true
        localStorage.removeItem('access_token')
        localStorage.removeItem('user_info')
        console.warn('由于认证失败，已清除本地认证状态')
        
        // 延迟重定向，避免在错误处理中立即跳转
        setTimeout(() => {
          window.location.href = '/login'
          isLoggingOut = false
        }, 100)
      }
    }
    
    const errorMessage = error.response?.data?.detail || error.message || '请求失败'
    console.error('API请求失败:', {
      url: error.config?.url,
      status: error.response?.status,
      message: errorMessage,
      timestamp: new Date().toISOString()
    })
    
    return Promise.reject(new Error(errorMessage))
  }
)

// 认证API服务
export const authApi = {
  /**
   * 用户登录
   */
  async login(data: LoginRequest): Promise<AuthResponse> {
    return apiClient.post('/api/v1/auth/login', data)
  },

  /**
   * 用户注册
   */
  async register(data: RegisterRequest): Promise<AuthResponse> {
    return apiClient.post('/api/v1/auth/register', data)
  },

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    return apiClient.get('/api/v1/auth/me')
  },

  /**
   * 更新用户资料
   */
  async updateProfile(data: UpdateProfileRequest): Promise<User> {
    return apiClient.put('/api/v1/auth/me', data)
  },

  /**
   * 修改密码
   */
  async changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
    return apiClient.post('/api/v1/auth/change-password', data)
  },

  /**
   * 上传头像
   */
  async uploadAvatar(file: File): Promise<{ url: string }> {
    const formData = new FormData()
    formData.append('file', file)
    
    // 使用原始的axios而不使用apiClient，以避免拦截器干扰FormData
    const token = localStorage.getItem('access_token')
    return apiClient.post('/api/v1/auth/upload-avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          console.log(`上传进度: ${percentCompleted}%`)
        }
      }
    })
  },

  /**
   * 退出登录
   */
  async logout(): Promise<{ message: string }> {
    return apiClient.post('/api/v1/auth/logout')
  },

  /**
   * 创建访客会话
   */
  async createGuestSession(): Promise<{ user_id: string; message: string }> {
    return apiClient.post('/api/v1/auth/guest')
  }
}

// 行程规划API服务
export const tripApi = {
  /**
   * 创建行程规划
   * @param request 行程规划请求数据
   * @param cancelToken 可选的取消令牌
   */
  async createTripPlan(
    request: TripPlanRequest,
    cancelToken?: any
  ): Promise<TripPlanResponse> {
    return apiClient.post('/api/v1/trips/plan', request, {
      cancelToken
    })
  },

  /**
   * 使用 SSE 流式接口创建行程规划，实时接收进度事件
   * 因为需要 POST + 自定义 Authorization Header，使用 fetch 而非 EventSource
   * @param request 行程规划请求数据
   * @param callbacks 进度/完成/错误回调
   * @returns 返回一个 abort 函数，调用后可中止请求
   */
  createTripPlanStream(
    request: TripPlanRequest,
    callbacks: TripPlanStreamCallbacks
  ): () => void {
    const abortController = new AbortController()
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const token = localStorage.getItem('access_token')

    fetch(`${baseUrl}/api/v1/trips/plan/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify(request),
      signal: abortController.signal
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        if (!response.body) {
          throw new Error('响应体为空，服务器不支持流式传输')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // 按 SSE 格式解析：每个事件以 \n\n 分隔
          const lines = buffer.split('\n\n')
          // 最后一个可能是不完整的，保留到下次
          buffer = lines.pop() ?? ''

          for (const chunk of lines) {
            const dataLine = chunk.split('\n').find((line) => line.startsWith('data: '))
            if (!dataLine) continue

            const jsonStr = dataLine.slice(6).trim()
            if (!jsonStr) continue

            try {
              const event: TripPlanProgressEvent = JSON.parse(jsonStr)

              if (event.stage === 'done' && event.result) {
                callbacks.onDone(event.result)
              } else if (event.stage === 'error') {
                callbacks.onError(event.message || '规划失败')
              } else {
                callbacks.onProgress(event)
              }
            } catch {
              // 忽略心跳等非 JSON 行
            }
          }
        }
      })
      .catch((error: Error) => {
        if (error.name === 'AbortError') return
        callbacks.onError(error.message || '网络请求失败')
      })

    return () => abortController.abort()
  },

  /**
   * 获取用户所有行程列表
   */
  async getTripsList(): Promise<TripPlanResponse[]> {
    return apiClient.get('/api/v1/trips/list')
  },

  /**
   * 获取指定行程详情
   * @param tripId 行程ID
   */
  async getTripDetail(tripId: string): Promise<TripPlanResponse> {
    return apiClient.get(`/api/v1/trips/${tripId}`)
  },

  /**
   * 删除指定行程
   * @param tripId 行程ID
   */
  async deleteTrip(tripId: string): Promise<{ message: string }> {
    return apiClient.delete(`/api/v1/trips/${tripId}`)
  },

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{ status: string }> {
    return apiClient.get('/health')
  }
}

export default apiClient
