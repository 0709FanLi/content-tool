// 项目状态管理

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Project, Script, Keyframe, VideoSegment, ProjectState } from '@/types'

export const useProjectStore = defineStore('project', () => {
  // 状态
  const currentProject = ref<Project | null>(null)
  const projects = ref<Project[]>([])
  const recentProjects = ref<Project[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const isProjectCompleted = computed(() => {
    return currentProject.value?.status === 'completed'
  })

  const currentScript = computed(() => currentProject.value?.script)
  const currentKeyframes = computed(() => currentProject.value?.keyframes || [])
  const currentVideoSegments = computed(() => currentProject.value?.videoSegments || [])

  const keyframesCompleted = computed(() => {
    const keyframes = currentKeyframes.value
    return keyframes.length > 0 && keyframes.every(k => k.status === 'completed')
  })

  const videosCompleted = computed(() => {
    const videos = currentVideoSegments.value
    return videos.length > 0 && videos.every(v => v.status === 'completed')
  })

  // 动作
  const setCurrentProject = (project: Project | null) => {
    currentProject.value = project
    error.value = null
  }

  const updateCurrentProject = (updates: Partial<Project>) => {
    if (currentProject.value) {
      currentProject.value = { ...currentProject.value, ...updates }
    }
  }

  const setProjects = (projectList: Project[]) => {
    projects.value = projectList
    // 同时更新最近项目列表（显示全部，支持滚动）
    recentProjects.value = projectList
  }

  const addProject = (project: Project) => {
    // 检查项目是否已存在
    const existingIndex = projects.value.findIndex(p => p.id === project.id)
    if (existingIndex !== -1) {
      // 如果已存在，更新并移到最前面
      projects.value.splice(existingIndex, 1)
    }
    projects.value.unshift(project)
    recentProjects.value = projects.value
  }
  
  const loadRecentProjects = async () => {
    try {
      const { projectApi } = await import('@/api')
      const response = await projectApi.getProjects({ page: 1, pageSize: 10 })
      setProjects(response.items || [])
    } catch (error) {
      console.error('加载最近项目失败:', error)
    }
  }

  const updateProject = (projectId: number, updates: Partial<Project>) => {
    const index = projects.value.findIndex(p => p.id === projectId)
    if (index !== -1) {
      projects.value[index] = { ...projects.value[index], ...updates }
    }

    if (currentProject.value?.id === projectId) {
      updateCurrentProject(updates)
    }

    // 更新最近项目列表（显示全部，支持滚动）
    recentProjects.value = projects.value
  }

  const removeProject = (projectId: number) => {
    projects.value = projects.value.filter(p => p.id !== projectId)
    recentProjects.value = projects.value

    if (currentProject.value?.id === projectId) {
      currentProject.value = null
    }
  }

  const setLoading = (value: boolean) => {
    loading.value = value
  }

  const setError = (message: string | null) => {
    error.value = message
  }

  const updateScript = (script: Script) => {
    if (currentProject.value) {
      // 使用展开运算符确保响应式更新
      currentProject.value = {
        ...currentProject.value,
        script: script,
        status: 'script_generated'
      }
      // 确保脚本正确设置
    } else {
      console.error('updateScript - 当前项目不存在')
    }
  }

  const updateKeyframes = (keyframes: Keyframe[]) => {
    if (currentProject.value) {
      currentProject.value.keyframes = keyframes
      const allCompleted = keyframes.every(k => k.status === 'completed')
      if (allCompleted) {
        currentProject.value.status = 'keyframes_completed'
      } else if (keyframes.some(k => k.status === 'generating')) {
        currentProject.value.status = 'keyframes_generating'
      }
    }
  }

  const updateKeyframe = (keyframeId: number, updates: Partial<Keyframe>) => {
    if (currentProject.value?.keyframes) {
      const index = currentProject.value.keyframes.findIndex(k => k.id === keyframeId)
      if (index !== -1) {
        currentProject.value.keyframes[index] = {
          ...currentProject.value.keyframes[index],
          ...updates
        }
        updateKeyframes(currentProject.value.keyframes)
      }
    }
  }

  const updateVideoSegments = (videos: VideoSegment[]) => {
    if (currentProject.value) {
      currentProject.value.videoSegments = videos
      const allCompleted = videos.every(v => v.status === 'completed')
      if (allCompleted) {
        currentProject.value.status = 'completed'
      } else if (videos.some(v => v.status === 'generating')) {
        currentProject.value.status = 'video_generating'
      }
    }
  }

  const updateVideoSegment = (videoId: number, updates: Partial<VideoSegment>) => {
    if (currentProject.value?.videoSegments) {
      const index = currentProject.value.videoSegments.findIndex(v => v.id === videoId)
      if (index !== -1) {
        currentProject.value.videoSegments[index] = {
          ...currentProject.value.videoSegments[index],
          ...updates
        }
        updateVideoSegments(currentProject.value.videoSegments)
      }
    }
  }

  const resetProject = () => {
    currentProject.value = null
    error.value = null
  }

  return {
    // 状态
    currentProject,
    projects,
    recentProjects,
    loading,
    error,

    // 计算属性
    isProjectCompleted,
    currentScript,
    currentKeyframes,
    currentVideoSegments,
    keyframesCompleted,
    videosCompleted,

    // 动作
    setCurrentProject,
    updateCurrentProject,
    setProjects,
    addProject,
    updateProject,
    removeProject,
    setLoading,
    setError,
    updateScript,
    updateKeyframes,
    updateKeyframe,
    updateVideoSegments,
    updateVideoSegment,
    resetProject,
    loadRecentProjects
  }
})
