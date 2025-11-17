// API接口统一出口

import request from '@/utils/request'
import type {
  LoginRequest,
  LoginResponse,
  Project,
  CreateProjectRequest,
  Script,
  GenerateScriptRequest,
  Keyframe,
  GenerateKeyframeRequest,
  GenerateKeyframesResponse,
  VideoSegment,
  GenerateVideoRequest,
  FileUploadResponse
} from '@/types'

// 认证相关API
export const authApi = {
  register: (data: { username: string; email: string; password: string }): Promise<any> =>
    request.post('/auth/register', data),

  login: (data: LoginRequest): Promise<LoginResponse> =>
    request.post('/auth/login', data),

  refreshToken: (): Promise<{ accessToken: string }> =>
    request.post('/auth/refresh'),

  logout: (): Promise<void> =>
    request.post('/auth/logout'),

  getCurrentUser: (): Promise<any> =>
    request.get('/auth/me')
}

// 项目管理API
export const projectApi = {
  getProjects: (params?: { page?: number; pageSize?: number }): Promise<{ items: Project[]; total: number }> =>
    request.get('/projects', { params }),

  getProject: (id: number): Promise<Project> =>
    request.get(`/projects/${id}`),

  createProject: (data: CreateProjectRequest): Promise<Project> =>
    request.post('/projects', data),

  updateProject: (id: number, data: Partial<Project>): Promise<Project> =>
    request.put(`/projects/${id}`, data),

  deleteProject: (id: number): Promise<void> =>
    request.delete(`/projects/${id}`),

  getRecentProjects: (): Promise<{ items: Project[]; total: number }> =>
    request.get('/projects', { params: { page: 1, pageSize: 10 } })
}

// 脚本管理API
export const scriptApi = {
  generateScript: (data: GenerateScriptRequest, model?: string): Promise<Script> => {
    const url = model ? `/scripts/generate?model=${encodeURIComponent(model)}` : '/scripts/generate'
    return request.post(url, data)
  },

  optimizeScript: (scriptId: number, optimization: string, model?: string): Promise<Script> => {
    const url = model ? `/scripts/${scriptId}/optimize?model=${encodeURIComponent(model)}` : `/scripts/${scriptId}/optimize`
    return request.post(url, { optimization })
  },

  getScript: (id: number): Promise<Script> =>
    request.get(`/scripts/${id}`),

  updateScript: (id: number, data: Partial<Script>): Promise<Script> =>
    request.put(`/scripts/${id}`, data)
}

// 关键帧管理API
export const keyframeApi = {
  generateKeyframes: (data: GenerateKeyframeRequest): Promise<{ keyframes: Keyframe[]; totalCount: number }> =>
    request.post('/keyframes/generate', data),

  getKeyframesByScript: (scriptId: number): Promise<{ keyframes: Keyframe[]; totalCount: number }> =>
    request.get(`/keyframes/script/${scriptId}`),

  getKeyframe: (id: number): Promise<Keyframe> =>
    request.get(`/keyframes/${id}`),

  regenerateKeyframe: (id: number, model?: string, aspectRatio?: string, quality?: string): Promise<Keyframe> => {
    const data: any = {}
    if (model) data.model = model
    if (aspectRatio) data.aspectRatio = aspectRatio
    if (quality) data.quality = quality
    return request.post(`/keyframes/${id}/regenerate`, Object.keys(data).length > 0 ? data : {})
  },

  updateKeyframe: (id: number, data: Partial<Keyframe>): Promise<Keyframe> =>
    request.put(`/keyframes/${id}`, data),

  uploadKeyframeImage: (id: number, file: File): Promise<Keyframe> =>
    request.upload(`/keyframes/${id}/upload`, file)
}

// 视频管理API
export const videoApi = {
  getVideoModels: (): Promise<{ models: Array<{ id: string; name: string; description: string; supportsFirstLastFrame: boolean }> }> =>
    request.get('/videos/models'),

  generateVideos: (data: GenerateVideoRequest): Promise<{ videoSegments: VideoSegment[]; totalCount: number }> =>
    request.post('/videos/generate', data),

  getVideoSegmentsByScript: (scriptId: number): Promise<{ videoSegments: VideoSegment[]; totalCount: number }> =>
    request.get(`/videos/script/${scriptId}`),

  getVideoSegment: (id: number): Promise<VideoSegment> =>
    request.get(`/videos/${id}`),

  regenerateVideoSegment: (id: number, model?: string): Promise<VideoSegment> => {
    const data: any = {}
    if (model) data.model = model
    return request.post(`/videos/${id}/regenerate`, data)
  },

  exportVideos: (scriptId: number): Promise<{ downloadUrl: string; expiresIn: number }> =>
    request.post('/videos/export', { scriptId })
}

// 文件管理API
export const fileApi = {
  uploadFile: (file: File, type?: string): Promise<FileUploadResponse> =>
    request.upload('/files/upload', file, {
      params: { type }
    }),

  getFileUrl: (fileId: number): Promise<{ url: string }> =>
    request.get(`/files/${fileId}/url`),

  deleteFile: (fileId: number): Promise<void> =>
    request.delete(`/files/${fileId}`)
}

// AI模型配置API
export const modelApi = {
  getScriptModels: (): Promise<{ code: number; message: string; data: { id: string; name: string }[] }> =>
    request.get('/models/script'),

  getScriptStyles: (): Promise<{ code: number; message: string; data: { id: string; name: string; description: string }[] }> =>
    request.get('/models/script-styles'),

  getVideoModels: (): Promise<{ id: string; name: string; aspectRatios: string[]; qualities: string[] }[]> =>
    request.get('/models/video'),

  getImageModels: (): Promise<{
    code: number;
    message: string;
    data: {
      id: string;
      name: string;
      description: string;
      aspect_ratios: string[];
      qualities: string[];
      has_quality_selector: boolean;
      supports_reference: boolean;
    }[]
  }> =>
    request.get('/models/image'),

  getSegmentDurations: (): Promise<{ value: number; label: string }[]> =>
    request.get('/models/segment-durations')
}
