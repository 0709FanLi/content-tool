// API相关类型定义

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

// 用户相关
export interface User {
  id: number
  username: string
  email: string
  avatar?: string
  createdAt: string
  updatedAt: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  user: User
  accessToken: string
  refreshToken: string
}

// 项目相关
export interface Project {
  id: number
  name: string
  description?: string
  status: 'draft' | 'processing' | 'completed'
  createdAt: string
  updatedAt: string
  userId: number
}

export interface CreateProjectRequest {
  name: string
  description?: string
}

// 脚本相关
export interface Script {
  id: number
  projectId: number
  content: string
  style?: string
  duration?: number
  segments: ScriptSegment[]
  createdAt: string
  updatedAt: string
}

export interface ScriptSegment {
  id: string
  timeStart: number
  timeEnd: number
  content: string
  scene?: string
  presenter?: string
  subtitle?: string
}

export interface GenerateScriptRequest {
  inspiration: string
  style: string
  totalDuration: number
  segmentDuration: number
  projectId?: number
}

// 关键帧相关
export interface Keyframe {
  id: number
  scriptId: number
  segmentId: string
  imageUrl?: string
  prompt?: string
  status: 'pending' | 'generating' | 'completed' | 'failed'
  errorMessage?: string
  createdAt: string
  updatedAt: string
}

export interface GenerateKeyframesResponse {
  keyframes: Keyframe[]
  totalCount: number
}

export interface GenerateKeyframeRequest {
  scriptId: number
  model: string
  aspectRatio: string
  quality: string
}

// 视频相关
export interface VideoSegment {
  id: number
  scriptId: number
  segmentIndex: number
  firstFrameUrl?: string
  lastFrameUrl?: string
  prompt?: string
  videoUrl?: string
  model?: string
  aspectRatio?: string
  status: 'pending' | 'generating' | 'completed' | 'failed'
  duration: number
  errorMessage?: string
  createdAt: string
  updatedAt: string
}

export interface GenerateVideoRequest {
  scriptId: number
  model?: string
  aspectRatio?: string
  duration?: number
}

// 文件相关
export interface FileUploadResponse {
  fileId: number
  fileName: string
  fileUrl: string
  fileSize: number
  mimeType: string
}
