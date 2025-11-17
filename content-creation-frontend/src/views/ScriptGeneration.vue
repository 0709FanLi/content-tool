<template>
  <div class="script-generation">
    <div class="main-content">
      <div class="history-list">
      <div
        v-for="entry in timelineEntries"
        :key="entry.key"
        class="history-card history-card-conversation"
      >
        <!-- 用户输入 -->
        <div v-if="entry.payload.userInput" class="conversation-message user-message">
          <div class="message-label">你</div>
          <div class="message-content">
            {{ entry.payload.userInput }}
          </div>
        </div>
        
        <!-- AI回复 -->
        <div v-if="entry.payload.aiResponse" class="conversation-message ai-message">
          <div class="message-label">AI</div>
          <div class="message-content-wrapper">
            <!-- 可编辑的脚本内容 -->
            <textarea
              v-if="entry.payload.isEditable"
              v-model="scriptContent"
              ref="scriptTextareaRef"
              class="message-content script-content-editable"
              placeholder="脚本内容将显示在这里..."
              @blur="handleScriptBlur(entry.payload)"
              @input="handleScriptInput(entry.payload)"
            />
            <!-- 只读的脚本内容 -->
            <div 
              v-else 
              class="message-content script-content-readonly"
              @click="handleEditScript(entry.payload)"
            >
              {{ entry.payload.aiResponse }}
            </div>
          </div>
          
          <!-- 操作控件：每个AI回复下方都显示 -->
          <div class="action-controls conversation-action-controls">
            <el-select
              v-model="selectedModel"
              placeholder="选择模型"
              class="control-select"
              @change="handleModelChange"
            >
              <el-option
                v-for="model in imageModels"
                :key="model.id"
                :label="model.name"
                :value="model.id"
              />
            </el-select>

            <el-select
              v-model="selectedAspectRatio"
              placeholder="图像比例"
              class="control-select"
              :disabled="!selectedModel"
            >
              <el-option
                v-for="ratio in aspectRatios"
                :key="ratio"
                :label="ratio"
                :value="ratio"
              />
            </el-select>

            <el-select
              v-model="selectedQuality"
              placeholder="清晰度"
              class="control-select"
              :disabled="!selectedModel"
              v-if="selectedModel && imageModels.find(m => m.id === selectedModel)?.has_quality_selector"
            >
              <el-option
                v-for="quality in qualities"
                :key="quality"
                :label="quality"
                :value="quality"
              />
            </el-select>

            <el-button
              type="primary"
              class="generate-button"
              :disabled="!canGenerateKeyframes"
              @click="handleGenerateKeyframes"
            >
              生成关键帧
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="action-section">
      <div class="optimization-section">
        <div 
          class="optimization-input-wrapper"
          :class="{ 'has-focus': optimizationInputFocused }"
        >
          <el-input
            v-model="optimizationInput"
            type="textarea"
            placeholder="输入您的创意描述···"
            class="optimization-input"
            :rows="2"
            :maxlength="3000"
            @focus="optimizationInputFocused = true"
            @blur="optimizationInputFocused = false"
          />
          <ModelSelect
            v-model="selectedOptimizeModel"
            type="script"
            placeholder="选择模型"
            class="optimization-model-select"
            :disabled="optimizing"
            clearable
          />
          <el-button
            type="primary"
            class="optimization-button"
            :disabled="!optimizationInput.trim() || !selectedOptimizeModel || optimizing"
            :loading="optimizing"
            @click="handleOptimize"
          >
            <span v-if="!optimizing" class="arrow-up">↑</span>
          </el-button>
        </div>
      </div>
    </div>
    </div>

    <!-- 可拖动的分隔条 -->
    <div
      v-if="keyframes.length > 0"
      class="resizer"
      @mousedown="startResize"
    ></div>

    <!-- 右侧关键帧面板 -->
    <div
      v-if="keyframes.length > 0"
      class="keyframe-panel"
      :style="{ width: keyframePanelWidth + 'px' }"
    >
      <div class="panel-header">
        <h2 class="panel-title">{{ showVideoView ? '视频片段生成' : 'AI关键帧生成' }}</h2>
        <div class="header-controls" v-if="!showVideoView">
          <el-select
            v-model="selectedVideoModel"
            placeholder="选择视频模型"
            class="video-model-select"
            size="default"
            :disabled="videoModels.length === 0"
          >
            <el-option
              v-for="model in videoModels"
              :key="model.id"
              :label="model.name"
              :value="model.id"
            />
          </el-select>
          <el-button
            type="primary"
            class="confirm-video-btn"
            :disabled="!allKeyframesCompleted || videoModels.length === 0 || !selectedVideoModel"
            @click="handleConfirmVideo"
            :title="!allKeyframesCompleted ? '请等待所有关键帧生成完成' : (videoModels.length === 0 ? '视频模型加载中...' : (!selectedVideoModel ? '请选择视频模型' : ''))"
          >
            关键帧确认，生成视频
          </el-button>
          <el-button
            v-if="videoSegments.length > 0"
            type="default"
            class="next-step-btn"
            @click="handleGoToVideoView"
          >
            下一步
          </el-button>
        </div>
        <div class="header-controls" v-else>
          <el-button
            type="default"
            class="back-btn"
            @click="handleBackToKeyframes"
          >
            上一步
          </el-button>
          <el-button
            type="default"
            class="save-btn"
            @click="handleSaveVideos"
          >
            保存
          </el-button>
          <el-button
            type="primary"
            class="export-btn"
            :disabled="!allVideosCompleted"
            :loading="exporting"
            @click="handleExportVideos"
          >
            确认视频，导出（*zip）
          </el-button>
        </div>
      </div>

      <!-- 关键帧列表 -->
      <div class="keyframes-container" v-if="!showVideoView">
        <div class="keyframe-list">
          <div
            v-for="keyframe in sortedKeyframes"
            :key="keyframe.id"
            class="keyframe-card"
          >
            <div class="card-header">
              <h3 class="card-title">{{ keyframe.segmentId }}</h3>
              <div class="card-actions">
                <el-icon class="action-icon" @click="handleEditKeyframe(keyframe.id)">
                  <Edit />
                </el-icon>
                <el-icon class="action-icon" @click="handleRefreshKeyframe(keyframe.id)">
                  <Refresh />
                </el-icon>
              </div>
            </div>

            <div class="card-image-area">
              <div v-if="keyframe.imageUrl" class="image-container">
                <img
                  :src="keyframe.imageUrl"
                  :alt="keyframe.segmentId"
                  class="keyframe-image"
                />
                <el-button
                  class="upload-overlay-btn"
                  size="small"
                  @click="handleUploadImage(keyframe.id)"
                >
                  重新上传
                </el-button>
              </div>
              <div v-else class="image-placeholder">
                <div class="placeholder-icon">🖼️</div>
                <el-button
                  class="upload-btn"
                  size="small"
                  @click="handleUploadImage(keyframe.id)"
                >
                  重新上传
                </el-button>
              </div>
            </div>

            <div v-if="getKeyframeDescription(keyframe)" class="card-description">
              <p>{{ getKeyframeDescription(keyframe) }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 视频列表 -->
      <div class="videos-container" v-if="showVideoView">
        <div class="video-list">
          <div
            v-for="video in sortedVideos"
            :key="video.id"
            class="video-card"
          >
            <!-- 卡片标题 -->
            <div class="card-header">
              <h3 class="card-title">{{ getVideoSegmentTitle(video.segmentIndex) }}</h3>
              <div class="card-actions">
                <el-icon 
                  class="action-icon" 
                  @click="handleRefreshVideo(video.id)"
                  v-if="video.status !== 'generating'"
                >
                  <Refresh />
                </el-icon>
              </div>
            </div>

            <!-- 视频预览区域 -->
            <div class="card-video-area">
              <!-- 生成中 -->
              <div v-if="video.status === 'generating'" class="video-loading">
                <el-icon class="loading-icon is-loading"><Loading /></el-icon>
                <div class="loading-text">生成中...</div>
              </div>
              
              <!-- 已完成 -->
              <div
                v-else-if="video.videoUrl"
                class="video-container"
              >
                <video
                  :src="video.videoUrl"
                  controls
                  class="video-player"
                  preload="metadata"
                />
              </div>

              <!-- 失败 -->
              <div v-else-if="video.status === 'failed'" class="video-error">
                <div class="error-icon">⚠️</div>
                <div class="error-text">{{ video.errorMessage || '生成失败' }}</div>
                <el-button
                  class="retry-btn"
                  size="small"
                  @click="handleRefreshVideo(video.id)"
                >
                  重新生成
                </el-button>
              </div>

              <!-- 占位 -->
              <div v-else class="video-placeholder">
                <div class="placeholder-icon">🎬</div>
              </div>
            </div>

            <!-- 脚本描述 -->
            <div class="card-description">
              <p>{{ video.prompt }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <input
      ref="imageUploadRef"
      type="file"
      accept="image/*"
      style="display: none"
      @change="handleImageSelected"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, onUnmounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElButton, ElIcon } from 'element-plus'
import { Edit, Refresh, Loading } from '@element-plus/icons-vue'
import { modelApi, scriptApi, projectApi, keyframeApi, videoApi } from '@/api'
import { useProjectStore } from '@/stores'
import type { Script, Keyframe, VideoSegment } from '@/types'
import ModelSelect from '@/components/common/ModelSelect.vue'

const router = useRouter()
const route = useRoute()
const projectStore = useProjectStore()

// 从路由参数获取项目ID
const projectId = computed(() => {
  const id = route.params.projectId
  return id ? parseInt(id as string, 10) : null
})

// 对话历史记录（问答形式）
interface ConversationItem {
  userInput: string  // 用户输入的创意描述（初始脚本时为空）
  aiResponse: string // AI返回的脚本内容
  timestamp: number  // 时间戳
  isEditable?: boolean // 是否可编辑（最新的一条可编辑）
}

const conversationHistory = ref<ConversationItem[]>([])

// 当前可编辑的脚本内容（用于绑定到最新的AI回复）
const scriptContent = ref<string>('')

type TimelineEntry = {
  type: 'conversation'
  key: string
  payload: ConversationItem
}

const timelineEntries = computed<TimelineEntry[]>(() => {
  return conversationHistory.value.map((item, index) => ({
    type: 'conversation',
    key: `conversation-${index}`,
    payload: item
  }))
})

// 脚本输入框引用
const scriptTextareaRef = ref<HTMLTextAreaElement | HTMLTextAreaElement[] | null>(null)

const resolveScriptTextarea = (): HTMLTextAreaElement | null => {
  const textareaRef = scriptTextareaRef.value
  if (!textareaRef) {
    return null
  }
  if (Array.isArray(textareaRef)) {
    return textareaRef[0] ?? null
  }
  return textareaRef
}

// 创意输入框焦点状态
const optimizationInputFocused = ref<boolean>(false)

// 模型选择
const selectedModel = ref<string>('')
const imageModels = ref<{
  id: string;
  name: string;
  description: string;
  aspect_ratios: string[];
  qualities: string[];
  has_quality_selector: boolean;
  supports_reference: boolean;
}[]>([])

// 图像比例和清晰度
const selectedAspectRatio = ref<string>('')
const selectedQuality = ref<string>('')
const aspectRatios = ref<string[]>([])
const qualities = ref<string[]>([])

// 优化输入
const optimizationInput = ref<string>('')
const selectedOptimizeModel = ref<string>('')
const optimizing = ref<boolean>(false)

// 关键帧相关
const keyframes = ref<Keyframe[]>([])
const generating = ref<boolean>(false)
const imageUploadRef = ref<HTMLInputElement | null>(null)
const currentUploadKeyframeId = ref<number | null>(null)
let pollingTimer: ReturnType<typeof setInterval> | null = null

// 视频模型相关
const videoModels = ref<any[]>([
  { id: 'veo3.1-fast', name: 'Veo 3.1 Fast', description: '快速生成' },
  { id: 'veo3.1-pro', name: 'Veo 3.1 Pro', description: '专业质量' }
])
const selectedVideoModel = ref<string>('veo3.1-fast')

// 视频视图相关
const showVideoView = ref<boolean>(false)
const videoSegments = ref<VideoSegment[]>([])
const generatingVideos = ref<boolean>(false)
const exporting = ref<boolean>(false)

// 分隔条拖动
const keyframePanelWidth = ref<number>(460)
const isResizing = ref<boolean>(false)
const startX = ref<number>(0)
const startWidth = ref<number>(460)

// 计算属性：是否可以生成关键帧
const canGenerateKeyframes = computed(() => {
  // 检查基本必填项
  if (!selectedModel.value || !selectedAspectRatio.value || !scriptContent.value.trim()) {
    return false
  }
  
  // 检查清晰度：只有当模型有清晰度选项时才要求填写
  const currentModel = imageModels.value.find(m => m.id === selectedModel.value)
  if (currentModel?.has_quality_selector && !selectedQuality.value) {
    return false
  }
  
  return true
})

// 关键帧计算属性
const sortedKeyframes = computed(() => {
  return [...keyframes.value].sort((a, b) => {
    // 自定义排序逻辑：首帧 -> 段落
    const getOrder = (segmentId: string) => {
      if (segmentId.includes('_first_frame')) {
        // 首帧：返回最小值，确保排在最前面
        const segNum = parseInt(segmentId.match(/segment_(\d+)/)?.[1] || '0')
        return segNum * 1000 - 1000
      } else {
        // 普通段落：按段落编号排序
        const segNum = parseInt(segmentId.match(/segment_(\d+)/)?.[1] || '0')
        return segNum * 1000
      }
    }
    
    return getOrder(a.segmentId) - getOrder(b.segmentId)
  })
})

const allKeyframesCompleted = computed(() => {
  if (keyframes.value.length === 0) {
    return false
  }
  
  // 检查所有关键帧是否完成
  // 规则：
  // 1. 如果关键帧有图片URL，认为已完成
  // 2. 如果是首帧（_first_frame），即使没有图片也认为已完成（它可能不是必需的）
  // 3. 否则检查状态：completed 或 failed 都算完成
  const allCompleted = keyframes.value.every(k => {
    // 如果关键帧有图片URL，认为已完成
    if (k.imageUrl) {
      return true
    }
    // 如果是首帧，即使没有图片也认为已完成
    if (k.segmentId.includes('_first_frame')) {
      return true
    }
    // 否则检查状态：completed 或 failed 都算完成
    return k.status === 'completed' || k.status === 'failed'
  })
  
  if (!allCompleted) {
    const statusCounts = keyframes.value.reduce((acc, k) => {
      acc[k.status] = (acc[k.status] || 0) + 1
      return acc
    }, {} as Record<string, number>)
    const withImage = keyframes.value.filter(k => k.imageUrl).length
    const firstFrames = keyframes.value.filter(k => k.segmentId.includes('_first_frame'))
  }
  
  return allCompleted
})

// 加载图片模型列表
const loadImageModels = async () => {
  try {
    const response = await modelApi.getImageModels()
    const models = Array.isArray(response) ? response : (response?.data || [])
    imageModels.value = models

    // 如果有模型，设置第一个为默认值
    if (models.length > 0 && !selectedModel.value) {
      selectedModel.value = models[0].id
      await handleModelChange()
    }
  } catch (error) {
    console.error('加载图片模型列表失败:', error)
    ElMessage.error('加载模型列表失败')
  }
}


// 模型变化时加载对应的图像比例和清晰度选项
const handleModelChange = async () => {
  const modelId = selectedModel.value
  if (!modelId) {
    aspectRatios.value = []
    qualities.value = []
    selectedAspectRatio.value = ''
    selectedQuality.value = ''
    return
  }

  try {
    // 从已加载的模型列表中找到对应的模型配置
    const model = imageModels.value.find(m => m.id === modelId)
    if (!model) {
      console.error('未找到模型配置:', modelId)
      return
    }

    // 从模型配置中获取参数选项
    aspectRatios.value = model.aspect_ratios || []
    qualities.value = model.qualities || []

    // 清空当前选择并设置第一个选项为默认值
    if (aspectRatios.value.length > 0) {
      selectedAspectRatio.value = aspectRatios.value[0]
    } else {
      selectedAspectRatio.value = ''
    }

    if (qualities.value.length > 0) {
      selectedQuality.value = qualities.value[0]
    } else {
      selectedQuality.value = ''
    }
  } catch (error) {
    console.error('加载模型配置失败:', error)
    ElMessage.error('加载模型配置失败')
  }
}

// 编辑历史脚本
const handleEditScript = (item: ConversationItem) => {
  // 将之前的可编辑对话项设为不可编辑
  conversationHistory.value.forEach(historyItem => {
    if (historyItem.isEditable) {
      historyItem.isEditable = false
    }
  })
  
  // 将点击的对话项设为可编辑
  item.isEditable = true
  scriptContent.value = item.aiResponse
  
  // 调整文本域高度
  nextTick(() => {
    adjustTextareaHeight()
  })
}

// 脚本内容输入处理
const handleScriptInput = (item: ConversationItem) => {
  // 更新当前对话项的aiResponse
  item.aiResponse = scriptContent.value
  adjustTextareaHeight()
}

// 脚本内容失焦时自动保存
const handleScriptBlur = async (item: ConversationItem) => {
  if (!scriptContent.value.trim()) {
    return
  }

  // 更新当前对话项的aiResponse
  item.aiResponse = scriptContent.value

  try {
    // 如果有脚本ID，更新脚本内容
    if (projectStore.currentScript?.id) {
      await scriptApi.updateScript(projectStore.currentScript.id, {
        content: scriptContent.value
      })
      
      // 更新store中的脚本
      if (projectStore.currentScript) {
        projectStore.currentScript.content = scriptContent.value
      }
    }

    // 保存对话历史到项目
    const conversationContentJson = JSON.stringify(conversationHistory.value)
    if (projectStore.currentProject?.id) {
      await projectApi.updateProject(projectStore.currentProject.id, {
        conversationContent: conversationContentJson,
        imageModel: selectedModel.value,
        aspectRatio: selectedAspectRatio.value,
        quality: selectedQuality.value
      } as any)
      
      // 更新store中的项目对话内容
      projectStore.updateCurrentProject({
        conversationContent: conversationContentJson
      } as any)
    }
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  }
}

// 优化脚本
const handleOptimize = async () => {
  if (!optimizationInput.value.trim() || !selectedOptimizeModel.value) {
    ElMessage.warning('请选择模型并输入创意描述')
    return
  }

  if (!projectStore.currentScript?.id) {
    ElMessage.warning('请先创建脚本')
    return
  }

  optimizing.value = true

  try {
    // 将之前的可编辑对话项设为不可编辑
    conversationHistory.value.forEach(item => {
      if (item.isEditable) {
        item.isEditable = false
      }
    })
    
    const creativeText = optimizationInput.value
    
    // 先更新当前可编辑的脚本内容到数据库
    if (scriptContent.value && projectStore.currentScript?.id) {
      await scriptApi.updateScript(projectStore.currentScript.id, {
        content: scriptContent.value
      })
    }
    
    // 调用优化接口
    const response = await scriptApi.optimizeScript(
      projectStore.currentScript!.id,
      creativeText,
      selectedOptimizeModel.value
    )
    
    // 获取优化后的脚本内容
    const optimizedContent = response?.content || scriptContent.value
    
    // 创建新的对话项
    const newConversationItem: ConversationItem = {
      userInput: creativeText,
      aiResponse: optimizedContent,
      timestamp: Date.now(),
      isEditable: true // 最新的对话项可编辑
    }
    
    // 添加到对话历史
    conversationHistory.value.push(newConversationItem)
    
    // 更新scriptContent为最新的脚本内容
    scriptContent.value = optimizedContent
    
    // 更新store中的脚本
    if (projectStore.currentScript) {
      projectStore.currentScript.content = optimizedContent
    }
    
    // 保存对话历史到项目（序列化为JSON字符串）
    const conversationContentJson = JSON.stringify(conversationHistory.value)
    const currentProjectId = projectStore.currentProject?.id
    if (currentProjectId) {
      await projectApi.updateProject(currentProjectId, {
        conversationContent: conversationContentJson
      } as any)
      
      // 更新store中的项目对话内容
      projectStore.updateCurrentProject({
        conversationContent: conversationContentJson
      } as any)
      
      // 重新加载项目数据，确保获取最新的脚本信息
      try {
        const reloadedProject = await projectApi.getProject(currentProjectId)
        const projectWithScript = reloadedProject as any
        
        // 处理脚本数据：如果返回的是 scripts 数组，取最新的一个作为 script
        if (
          projectWithScript.scripts &&
          Array.isArray(projectWithScript.scripts) &&
          projectWithScript.scripts.length > 0
        ) {
          const sortedScripts = [...projectWithScript.scripts].sort((a: any, b: any) => {
            const timeA = new Date(a.createdAt || a.created_at || 0).getTime()
            const timeB = new Date(b.createdAt || b.created_at || 0).getTime()
            return timeB - timeA
          })
          projectWithScript.script = sortedScripts[0]
          
          // 更新store
          projectStore.setCurrentProject(projectWithScript)
          
          // 更新脚本内容
          if (projectWithScript.script) {
            scriptContent.value = projectWithScript.script.content || optimizedContent
            projectStore.updateScript(projectWithScript.script)
          }
        }
        
        // 刷新项目列表，确保项目列表显示最新的脚本信息
        await projectStore.loadRecentProjects()
      } catch (error) {
        console.error('[ScriptGeneration] handleOptimize 重新加载项目数据失败:', error)
        // 即使重新加载失败，也继续执行，使用已更新的数据
      }
    }
    
    // 清空输入框
    optimizationInput.value = ''
    
    // 确保视图更新
    await nextTick()
    adjustTextareaHeight()
    
    ElMessage.success('脚本优化成功')
    
    // 滚动到底部显示最新的对话
    await nextTick()
    setTimeout(() => {
      const historyList = document.querySelector('.history-list')
      if (historyList) {
        historyList.scrollTop = historyList.scrollHeight
      }
    }, 200)
  } catch (error: any) {
    const errorMsg = error?.response?.data?.detail || error?.response?.data?.message || error?.message || '优化失败，请重试'
    ElMessage.error(errorMsg)
  } finally {
    optimizing.value = false
  }
}

// 加载关键帧列表
const loadKeyframes = async () => {
  const scriptId = projectStore.currentScript?.id
  const currentProjectId = projectStore.currentProject?.id
  
  // 检查项目ID是否匹配路由参数
  if (projectId.value && currentProjectId !== projectId.value) {
    stopPolling()
    return
  }
  
  if (!scriptId) {
    // 如果没有脚本ID，停止轮询并清空关键帧
    keyframes.value = []
    stopPolling()
    return
  }

  try {
    const response = await keyframeApi.getKeyframesByScript(scriptId)
    keyframes.value = response.keyframes || []

    const hasGenerating = keyframes.value.some(k => k.status === 'generating')
    if (hasGenerating) {
      generating.value = true
      startPolling()
    } else {
      generating.value = false
      // 如果没有生成中的关键帧，停止轮询
      stopPolling()
    }
  } catch (error) {
    console.error('[ScriptGeneration] loadKeyframes 失败:', error)
    // 出错时也停止轮询
    stopPolling()
  }
}

// 轮询检查生成状态
const startPolling = () => {
  // 如果已经有轮询在运行，不重复启动
  if (pollingTimer) {
    return
  }

  const scriptId = projectStore.currentScript?.id
  if (!scriptId) {
    return
  }

  pollingTimer = setInterval(async () => {
    const currentScriptId = projectStore.currentScript?.id
    if (!currentScriptId || currentScriptId !== scriptId) {
      stopPolling()
      return
    }

    await loadKeyframes()

    const allFinished = keyframes.value.every(
      k => k.status === 'completed' || k.status === 'failed'
    )

    if (allFinished) {
      stopPolling()
      generating.value = false
    }
  }, 3000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

// 生成关键帧
const handleGenerateKeyframes = async () => {
  if (!canGenerateKeyframes.value) {
    ElMessage.warning('请完成所有必填项')
    return
  }

  // 检查脚本ID是否存在
  let scriptId = projectStore.currentScript?.id
  
  // 如果脚本ID不存在，尝试从项目数据中获取脚本ID
  if (!scriptId) {
    const project = projectStore.currentProject
    const projectId = project?.id
    
    if (!projectId) {
      ElMessage.warning('请先创建项目')
      return
    }

    try {
      // 首先尝试从当前项目数据中获取脚本
      if (project && (project as any).scripts && Array.isArray((project as any).scripts) && (project as any).scripts.length > 0) {
        // 按创建时间排序，取最新的脚本
        const sortedScripts = [...(project as any).scripts].sort((a: any, b: any) => {
          const timeA = new Date(a.createdAt || a.created_at || 0).getTime()
          const timeB = new Date(b.createdAt || b.created_at || 0).getTime()
          return timeB - timeA
        })
        scriptId = sortedScripts[0].id
        
        // 更新store中的脚本和项目
        projectStore.updateScript(sortedScripts[0])
        projectStore.setCurrentProject({
          ...project,
          script: sortedScripts[0]
        } as any)
      } else if (project && (project as any).script && (project as any).script.id) {
        // 如果项目直接有 script 字段
        scriptId = (project as any).script.id
      } else {
        // 如果项目数据中没有脚本，重新加载项目数据
        const reloadedProject = await projectApi.getProject(projectId)
        const projectWithScript = reloadedProject as any
        
        // 处理脚本数据：如果返回的是 scripts 数组，取最新的一个作为 script
        if (
          projectWithScript.scripts &&
          Array.isArray(projectWithScript.scripts) &&
          projectWithScript.scripts.length > 0
        ) {
          const sortedScripts = [...projectWithScript.scripts].sort((a: any, b: any) => {
            const timeA = new Date(a.createdAt || a.created_at || 0).getTime()
            const timeB = new Date(b.createdAt || b.created_at || 0).getTime()
            return timeB - timeA
          })
          projectWithScript.script = sortedScripts[0]
          scriptId = sortedScripts[0].id
          
          // 更新store
          projectStore.setCurrentProject(projectWithScript)
        } else if (projectWithScript.script && projectWithScript.script.id) {
          // 如果直接有 script 字段
          scriptId = projectWithScript.script.id
          projectStore.setCurrentProject(projectWithScript)
        }
      }
      
      // 如果脚本ID存在，确保脚本内容是最新的
      if (scriptId && scriptContent.value.trim()) {
        await scriptApi.updateScript(scriptId, {
          content: scriptContent.value
        })
      }
    } catch (error: any) {
      console.error('获取脚本ID失败:', error)
      ElMessage.error(error?.message || '获取脚本信息失败，请重试')
      return
    }
  }

  // 最终检查脚本ID是否存在
  if (!scriptId) {
    ElMessage.warning('请先创建脚本')
    return
  }

  generating.value = true

  try {
    // 先清空旧的关键帧数据（提升用户体验，立即看到变化）
    keyframes.value = []

    // 保存当前选择的模型配置到后端
    if (projectStore.currentProject?.id) {
      await projectApi.updateProject(projectStore.currentProject.id, {
        imageModel: selectedModel.value,
        aspectRatio: selectedAspectRatio.value,
        quality: selectedQuality.value
      } as any)
      
      // 更新store
      projectStore.updateCurrentProject({
        imageModel: selectedModel.value,
        aspectRatio: selectedAspectRatio.value,
        quality: selectedQuality.value
      } as any)
    }

    // 调用生成关键帧接口
    const request: any = {
      script_id: scriptId,
      model: selectedModel.value,
      aspect_ratio: selectedAspectRatio.value
    }
    
    // 只有当模型支持清晰度且用户选择了清晰度时，才传递quality参数
    if (selectedQuality.value) {
      request.quality = selectedQuality.value
    }

    const response = await keyframeApi.generateKeyframes(request)
    keyframes.value = response.keyframes || []

    ElMessage.success('开始生成关键帧')
    startPolling()
  } catch (error: any) {
    console.error('生成关键帧失败:', error)
    ElMessage.error(error?.message || '生成关键帧失败')
    generating.value = false
  }
}

// 刷新关键帧
const handleRefreshKeyframe = async (keyframeId: number) => {
  try {
    await keyframeApi.regenerateKeyframe(
      keyframeId,
      selectedModel.value,
      selectedAspectRatio.value,
      selectedQuality.value
    )

    ElMessage.success('已开始重新生成')
    await loadKeyframes()
    startPolling()
  } catch (error: any) {
    console.error('重新生成失败:', error)
    ElMessage.error(error?.message || '重新生成失败')
  }
}

// 编辑关键帧
const handleEditKeyframe = (keyframeId: number) => {
  ElMessage.info('编辑功能开发中...')
}

// 上传图片
const handleUploadImage = (keyframeId: number) => {
  currentUploadKeyframeId.value = keyframeId
  imageUploadRef.value?.click()
}

const handleImageSelected = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]

  if (!file || !currentUploadKeyframeId.value) {
    return
  }

  try {
    await keyframeApi.uploadKeyframeImage(currentUploadKeyframeId.value, file)
    ElMessage.success('图片上传成功')
    await loadKeyframes()
  } catch (error: any) {
    console.error('上传图片失败:', error)
    ElMessage.error(error?.message || '上传图片失败')
  } finally {
    currentUploadKeyframeId.value = null
    if (target) {
      target.value = ''
    }
  }
}

// 加载视频模型列表
const loadVideoModels = async () => {
  try {
    const response = await videoApi.getVideoModels()
    
    // 处理不同的响应格式
    let models: any[] = []
    if (Array.isArray(response)) {
      models = response
    } else if (response && typeof response === 'object' && 'models' in response) {
      models = Array.isArray((response as any).models) ? (response as any).models : []
    }
    
    videoModels.value = models.length > 0 ? models : [
      { id: 'veo3.1-fast', name: 'Veo 3.1 Fast', description: '快速生成' },
      { id: 'veo3.1-pro', name: 'Veo 3.1 Pro', description: '专业质量' }
    ]
    
    // 确保selectedVideoModel有值：如果为空或不在列表中，设置为第一个
    if (videoModels.value.length > 0) {
      const currentValue = selectedVideoModel.value
      const isValidValue = currentValue && videoModels.value.find(m => m.id === currentValue)
      
      if (!isValidValue) {
        selectedVideoModel.value = videoModels.value[0].id
      } else {
        // 即使值有效，也确保设置一次，确保响应式更新
        selectedVideoModel.value = currentValue
      }
    }
    
    
    // 强制触发一次更新，确保 el-select 正确显示值
    await nextTick()
  } catch (error) {
    console.error('加载视频模型失败:', error)
    // 确保即使API失败也有默认值
    videoModels.value = [
      { id: 'veo3.1-fast', name: 'Veo 3.1 Fast', description: '快速生成' },
      { id: 'veo3.1-pro', name: 'Veo 3.1 Pro', description: '专业质量' }
    ]
    // 设置默认选中值
    if (!selectedVideoModel.value) {
      selectedVideoModel.value = 'veo3.1-fast'
    }
  }
}

// 确认生成视频
const handleConfirmVideo = async () => {
  if (!allKeyframesCompleted.value) {
    ElMessage.warning('请等待所有关键帧生成完成')
    return
  }

  if (!selectedVideoModel.value) {
    ElMessage.warning('请选择视频模型')
    return
  }

  const scriptId = projectStore.currentScript?.id
  if (!scriptId) {
    ElMessage.error('脚本ID不存在')
    return
  }

  generatingVideos.value = true

  try {
    // 先清空旧的视频数据（提升用户体验，立即看到变化）
    videoSegments.value = []
    
    // 如果当前在视频视图，先切换到关键帧视图（确保UI刷新）
    if (showVideoView.value) {
      showVideoView.value = false
    }

    const response = await videoApi.generateVideos({
      scriptId,
      model: selectedVideoModel.value,
      aspectRatio: selectedAspectRatio.value || '16:9',
      duration: 6.0
    })

    videoSegments.value = response.videoSegments || []
    showVideoView.value = true

    ElMessage.success('开始生成视频')
    startVideoPolling()
  } catch (error: any) {
    console.error('生成视频失败:', error)
    ElMessage.error(error?.message || '生成视频失败')
    generatingVideos.value = false
  }
}

// 返回关键帧页面
const handleBackToKeyframes = () => {
  showVideoView.value = false
  stopVideoPolling()
}

// 进入视频视图
const handleGoToVideoView = () => {
  if (videoSegments.value.length > 0) {
    showVideoView.value = true
    // 如果有正在生成的视频，启动轮询
    const hasGenerating = videoSegments.value.some(v => v.status === 'generating')
    if (hasGenerating) {
      startVideoPolling()
    }
  }
}

// 保存视频
const handleSaveVideos = () => {
  ElMessage.success('视频已保存')
}

// 导出视频
const handleExportVideos = async () => {
  if (!allVideosCompleted.value) {
    ElMessage.warning('请等待所有视频生成完成')
    return
  }

  const scriptId = projectStore.currentScript?.id
  if (!scriptId) {
    ElMessage.error('脚本ID不存在')
    return
  }

  exporting.value = true

  try {
    const response = await videoApi.exportVideos(scriptId)
    
    // 创建下载链接
    const link = document.createElement('a')
    link.href = response.downloadUrl
    link.download = `videos_${Date.now()}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('视频导出成功')
  } catch (error: any) {
    console.error('导出视频失败:', error)
    ElMessage.error(error?.message || '导出视频失败')
  } finally {
    exporting.value = false
  }
}

// 重新生成视频
const handleRefreshVideo = async (videoId: number) => {
  try {
    await videoApi.regenerateVideoSegment(videoId, selectedVideoModel.value)
    ElMessage.success('已开始重新生成')
    await loadVideoSegments()
    startVideoPolling()
  } catch (error: any) {
    console.error('重新生成失败:', error)
    ElMessage.error(error?.message || '重新生成失败')
  }
}

// 加载视频片段列表
const loadVideoSegments = async () => {
  const scriptId = projectStore.currentScript?.id
  const currentProjectId = projectStore.currentProject?.id
  
  // 检查项目ID是否匹配路由参数
  if (projectId.value && currentProjectId !== projectId.value) {
    stopVideoPolling()
    showVideoView.value = false
    return
  }
  
  if (!scriptId) {
    stopVideoPolling()
    showVideoView.value = false
    return
  }

  try {
    const response = await videoApi.getVideoSegmentsByScript(scriptId)
    videoSegments.value = response.videoSegments || []

    // 如果有视频在生成中，自动切换到视频视图
    if (videoSegments.value.length > 0) {
      const hasGenerating = videoSegments.value.some(v => v.status === 'generating')
      if (hasGenerating) {
        showVideoView.value = true
        generatingVideos.value = true
        startVideoPolling()
      } else {
        generatingVideos.value = false
        stopVideoPolling()
        // 如果没有生成中的视频，保持当前视图状态
      }
    } else {
      stopVideoPolling()
      showVideoView.value = false
    }
  } catch (error) {
    console.error('[ScriptGeneration] loadVideoSegments 失败:', error)
    stopVideoPolling()
    showVideoView.value = false
  }
}

// 视频轮询
let videoPollingTimer: ReturnType<typeof setInterval> | null = null
let pollingScriptId: number | null = null // 记录轮询时的脚本ID

const startVideoPolling = () => {
  if (videoPollingTimer) {
    return
  }

  const scriptId = projectStore.currentScript?.id
  const currentProjectId = projectStore.currentProject?.id
  
  if (!scriptId || !currentProjectId) {
    return
  }
  
  // 检查项目ID是否匹配路由参数
  if (projectId.value && currentProjectId !== projectId.value) {
    return
  }

  pollingScriptId = scriptId

  videoPollingTimer = setInterval(async () => {
    const currentScriptId = projectStore.currentScript?.id
    const currentProjectId = projectStore.currentProject?.id
    
    // 检查脚本ID是否变化
    if (!currentScriptId || currentScriptId !== pollingScriptId) {
      stopVideoPolling()
      return
    }
    
    // 检查项目ID是否匹配路由参数
    if (projectId.value && currentProjectId !== projectId.value) {
      console.log('[ScriptGeneration] startVideoPolling 轮询停止：项目ID不匹配', {
        currentProjectId,
        routeProjectId: projectId.value
      })
      stopVideoPolling()
      return
    }

    await loadVideoSegments()

    const allFinished = videoSegments.value.every(
      v => v.status === 'completed' || v.status === 'failed'
    )

    if (allFinished) {
      stopVideoPolling()
      generatingVideos.value = false
    }
  }, 3000)
}

const stopVideoPolling = () => {
  if (videoPollingTimer) {
    clearInterval(videoPollingTimer)
    videoPollingTimer = null
    pollingScriptId = null
  }
}

// 获取视频片段标题
const getVideoSegmentTitle = (segmentIndex: number) => {
  return `(0:${segmentIndex * 6} - ${(segmentIndex + 1) * 6}s) 第${segmentIndex + 1}段`
}

// 视频相关计算属性
const allVideosCompleted = computed(() => {
  return (
    videoSegments.value.length > 0 &&
    videoSegments.value.every(v => v.status === 'completed')
  )
})

const sortedVideos = computed(() => {
  return [...videoSegments.value].sort((a, b) => {
    return a.segmentIndex - b.segmentIndex
  })
})

// 获取关键帧描述
const getKeyframeDescription = (keyframe: Keyframe) => {
  // 首帧不显示描述，只显示图片
  if (keyframe.segmentId.includes('_first_frame')) {
    return ''
  }
  
  // 直接返回prompt字段，它已经是该关键帧对应的内容
  // keyframe.prompt 在生成时已经被正确设置为对应段落的内容
  return keyframe.prompt || ''
}

// 分隔条拖动
const startResize = (e: MouseEvent) => {
  isResizing.value = true
  startX.value = e.clientX
  startWidth.value = keyframePanelWidth.value

  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
  
  // 防止文本选中
  e.preventDefault()
}

const handleResize = (e: MouseEvent) => {
  if (!isResizing.value) return

  const deltaX = startX.value - e.clientX
  const newWidth = startWidth.value + deltaX

  // 限制最小和最大宽度
  const minWidth = 360
  const maxWidth = 800

  if (newWidth >= minWidth && newWidth <= maxWidth) {
    keyframePanelWidth.value = newWidth
  }
}

const stopResize = () => {
  isResizing.value = false
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
}

// 初始化数据
const initData = () => {
  // 从store获取当前脚本和项目信息
  const script = projectStore.currentScript
  const project = projectStore.currentProject

  // 获取对话历史（从项目数据中获取）
  let hasConversationHistory = false
  if (project) {
    // 后端返回的是 conversation_content（下划线），前端类型定义可能是 conversationContent（驼峰）
    const savedContent = (project as any).conversation_content || (project as any).conversationContent || ''
    
    // 只有当 savedContent 是有效的非空字符串时才处理
    if (savedContent && typeof savedContent === 'string' && savedContent.trim()) {
      try {
        // 尝试解析JSON格式的对话历史
        const parsed = JSON.parse(savedContent)
        if (Array.isArray(parsed) && parsed.length > 0) {
          // 验证数组中的每一项都是有效的对话项
          const validItems = parsed.filter((item: any) => 
            item && typeof item === 'object' && item.aiResponse
          )
          if (validItems.length > 0) {
            conversationHistory.value = validItems.map((item: any) => ({
              userInput: item.userInput || '',
              aiResponse: item.aiResponse || '',
              timestamp: item.timestamp || Date.now(),
              isEditable: false
            }))
            hasConversationHistory = true
          } else {
            // 数组为空或没有有效项
            conversationHistory.value = []
          }
        } else {
          // 解析结果不是有效数组
          conversationHistory.value = []
        }
      } catch (e) {
        conversationHistory.value = []
      }
    } else {
      conversationHistory.value = []
    }
  } else {
    // 没有项目数据，清空对话历史
    conversationHistory.value = []
  }

  // 如果没有对话历史，但有脚本内容，创建初始对话项
  if (!hasConversationHistory && script) {
    // 确保脚本内容存在
    const scriptContentText = script.content || ''
    if (scriptContentText.trim()) {
      const initialConversation: ConversationItem = {
        userInput: '', // 初始脚本时用户输入为空
        aiResponse: scriptContentText,
        timestamp: script.createdAt ? new Date(script.createdAt).getTime() : Date.now(),
        isEditable: true // 最新的对话项可编辑
      }
      conversationHistory.value = [initialConversation]
      scriptContent.value = scriptContentText
    } else {
      scriptContent.value = ''
    }
  } else if (conversationHistory.value.length > 0) {
    // 如果有对话历史，设置最新的为可编辑，并同步scriptContent
    const lastItem = conversationHistory.value[conversationHistory.value.length - 1]
    lastItem.isEditable = true
    scriptContent.value = lastItem.aiResponse || ''
  } else {
    scriptContent.value = ''
  }

  // 恢复之前选择的模型配置
  if (project && (project as any).imageModel) {
    selectedModel.value = (project as any).imageModel
    selectedAspectRatio.value = (project as any).aspectRatio || ''
    selectedQuality.value = (project as any).quality || ''
  }
}

// 调整文本域高度以适应内容
const adjustTextareaHeight = () => {
  nextTick(() => {
    const textarea = resolveScriptTextarea()
    if (!textarea) {
      return
    }
    // 重置高度以获取正确的 scrollHeight
    textarea.style.height = 'auto'
    // 设置高度为内容高度，但保持最小高度
    const minHeight = 200 // 最小高度
    const contentHeight = textarea.scrollHeight
    textarea.style.height = `${Math.max(minHeight, contentHeight)}px`
  })
}

const loadProjectData = async (): Promise<void> => {
  const id = projectId.value
  
  if (!id) {
    // 没有路由参数时，从 store 读取当前项目和脚本
    if (projectStore.currentProject || projectStore.currentScript) {
      
      // 检查当前项目是否是新创建的（没有关键帧）
      // 如果是新创建的项目，不应该加载旧项目的关键帧
      const currentProjectId = projectStore.currentProject?.id
      const currentScriptId = projectStore.currentScript?.id
      
      await nextTick()
      initData()
      adjustTextareaHeight()
      
      // 只有当脚本ID存在且项目ID存在时，才加载关键帧和视频片段
      // 注意：新创建的脚本，关键帧应该为空，不应该加载旧数据
      if (currentScriptId && currentProjectId) {
        await loadKeyframes()
        await loadVideoSegments()
      } else {
        // 如果没有脚本ID或项目ID，清空关键帧和视频片段
        keyframes.value = []
        videoSegments.value = []
      }
    } else {
      scriptContent.value = ''
      conversationHistory.value = []
      keyframes.value = []
      videoSegments.value = []
    }
    return
  }

  // 检查 store 中的项目是否有脚本数据
  if (projectStore.currentProject?.id === id) {
    const hasScript = !!projectStore.currentScript
    
    // 如果有脚本数据，直接使用
    if (hasScript) {
      await nextTick()
      initData()
      adjustTextareaHeight()
      // 确保关键帧数据也更新（只在当前项目ID匹配时）
      const script = projectStore.currentScript
      if (script?.id && projectStore.currentProject?.id === id) {
        // 强制重新加载关键帧和视频数据，确保显示最新状态
        await loadKeyframes()
        await loadVideoSegments()
      }
      return
    }
  }

  try {
    const project = await projectApi.getProject(id)
    const projectWithScript = project as any

    // 处理脚本数据：如果返回的是 scripts 数组，取最新的一个作为 script
    if (
      projectWithScript.scripts &&
      Array.isArray(projectWithScript.scripts) &&
      projectWithScript.scripts.length > 0
    ) {
      // 按创建时间排序，取最新的脚本
      const sortedScripts = [...projectWithScript.scripts].sort((a, b) => {
        const timeA = new Date(a.createdAt || a.created_at || 0).getTime()
        const timeB = new Date(b.createdAt || b.created_at || 0).getTime()
        return timeB - timeA // 降序，最新的在前
      })
      projectWithScript.script = sortedScripts[0]
      
      // 如果选中的脚本有关联的关键帧和视频，也设置到项目数据中
      if (projectWithScript.script.keyframes) {
        projectWithScript.keyframes = projectWithScript.script.keyframes
      }
      if (projectWithScript.script.videoSegments || projectWithScript.script.video_segments) {
        projectWithScript.videoSegments = projectWithScript.script.videoSegments || projectWithScript.script.video_segments
      }
    } else if (projectWithScript.script) {
      // 如果直接有 script 字段，使用它
      // 确保脚本数据存在
    } else {
      // 如果没有脚本数据，确保 script 字段为 null
      projectWithScript.script = null
    }
    
    projectStore.setCurrentProject(projectWithScript)
    await projectStore.loadRecentProjects()

    await nextTick()
    // 等待一个额外的tick，确保store中的数据完全更新
    await new Promise(resolve => setTimeout(resolve, 50))

    // 再次检查项目ID是否匹配（防止在异步操作期间项目ID发生变化）
    if (projectId.value !== id) {
      // 停止所有轮询，避免使用旧数据
      stopPolling()
      stopVideoPolling()
      return
    }

    // 确保脚本数据被正确设置到store中
    // 如果项目有scripts数组但没有script字段，再次设置
    const currentProject = projectStore.currentProject
    
    if (currentProject && !projectStore.currentScript) {
      if ((currentProject as any).scripts && Array.isArray((currentProject as any).scripts) && (currentProject as any).scripts.length > 0) {
        const sortedScripts = [...(currentProject as any).scripts].sort((a: any, b: any) => {
          const timeA = new Date(a.createdAt || a.created_at || 0).getTime()
          const timeB = new Date(b.createdAt || b.created_at || 0).getTime()
          return timeB - timeA
        })
        projectStore.setCurrentProject({
          ...currentProject,
          script: sortedScripts[0]
        } as any)
      }
    }

    initData()
    adjustTextareaHeight()
    
    // 确保关键帧数据也更新（只在当前项目ID匹配时）
    const script = projectStore.currentScript
    if (script?.id && projectStore.currentProject?.id === id) {
      await loadKeyframes()
      await loadVideoSegments()
    }
    
  } catch (error) {
    console.error('[ScriptGeneration] loadProjectData 失败:', error)
    ElMessage.error('加载项目信息失败')
    scriptContent.value = ''
    conversationHistory.value = []
    // 停止所有轮询
    stopPolling()
    stopVideoPolling()
  }
}

// 监听脚本内容变化，自动调整高度
watch(
  () => scriptContent.value,
  () => {
    adjustTextareaHeight()
  }
)

// 防止重复加载的标志
const isLoadingData = ref(false)

// 监听路由参数变化，当项目ID变化时重新加载数据
watch(
  () => projectId.value,
  async (newId, oldId) => {
    if (newId !== oldId && !isLoadingData.value) {
      isLoadingData.value = true
      try {
        // 清空关键帧和视频片段列表，确保切换时显示正确
        keyframes.value = []
        videoSegments.value = []
        // 停止所有轮询
        stopPolling()
        stopVideoPolling()
        await loadProjectData()
      } finally {
        isLoadingData.value = false
      }
    }
  },
  { immediate: true }
)

// 监听 store 中项目变化，确保关键帧数据正确更新
watch(
  () => projectStore.currentProject?.id,
  async (newProjectId, oldProjectId) => {
    // 只有在路由参数匹配且不在加载中时才重新加载
    if (newProjectId !== oldProjectId && 
        oldProjectId !== undefined && 
        newProjectId === projectId.value &&
        !isLoadingData.value) {
      isLoadingData.value = true
      try {
        // 项目切换时，重新加载关键帧和视频片段
        // 停止所有轮询
        stopPolling()
        stopVideoPolling()
        await loadKeyframes()
        await loadVideoSegments()
      } finally {
        isLoadingData.value = false
      }
    }
  }
)

// 监听 store 中脚本变化，确保关键帧数据正确更新
watch(
  () => projectStore.currentScript?.id,
  async (newScriptId, oldScriptId) => {
    // 只有在不在加载中时才重新加载
    if (newScriptId !== oldScriptId && oldScriptId !== undefined && !isLoadingData.value) {
      isLoadingData.value = true
      try {
        // 脚本切换时，重新加载关键帧和视频片段
        // 停止所有轮询
        stopPolling()
        stopVideoPolling()
        keyframes.value = []
        videoSegments.value = []
        if (newScriptId && projectStore.currentProject?.id === projectId.value) {
          await loadKeyframes()
          await loadVideoSegments()
        }
      } finally {
        isLoadingData.value = false
      }
    }
  }
)

// 监听selectedVideoModel，确保始终有值
watch(
  selectedVideoModel,
  (newValue, oldValue) => {
    // 如果selectedVideoModel被清空，自动设置为第一个模型
    if (!newValue && videoModels.value.length > 0) {
      const firstModelId = videoModels.value[0].id
      selectedVideoModel.value = firstModelId
    }
  },
  { immediate: true }
)

// 监听videoModels，确保selectedVideoModel始终有效
watch(
  () => videoModels.value.length,
  (newLength) => {
    if (newLength > 0 && (!selectedVideoModel.value || !videoModels.value.find(m => m.id === selectedVideoModel.value))) {
      selectedVideoModel.value = videoModels.value[0].id
    }
  }
)

// 监听按钮禁用条件，用于调试
watch(
  [allKeyframesCompleted, () => videoModels.value.length, selectedVideoModel],
  ([completed, modelsCount, selectedModel]) => {
  },
  { immediate: true }
)


// 监听路由参数变化（当用户点击项目列表切换项目时）
watch(() => route.params.projectId, async (newProjectId, oldProjectId) => {
  console.log('[watch projectId] 路由参数变化:', {
    newProjectId,
    oldProjectId,
    isDifferent: newProjectId !== oldProjectId
  })
  
  // 只有当项目ID确实发生变化时才重新加载
  if (newProjectId && newProjectId !== oldProjectId) {
    console.log('[watch projectId] 项目ID变化，重新加载数据')
    // 停止所有轮询
    stopPolling()
    stopVideoPolling()
    
    // 重新加载项目数据
    await nextTick()
    await loadProjectData()
    
    // 只有在项目ID匹配时才加载关键帧和视频片段
    if (projectStore.currentProject?.id === Number(newProjectId)) {
      await loadKeyframes()
      await loadVideoSegments()
    }
  }
}, { immediate: false })

onMounted(async () => {
  console.log('[onMounted] 组件挂载，projectId:', projectId.value)
  
  // 先停止所有轮询，确保没有旧的轮询在运行
  stopPolling()
  stopVideoPolling()
  
  // 先加载模型列表
  loadImageModels()
  await loadVideoModels()
  
  // 确保selectedVideoModel有值
  if (!selectedVideoModel.value && videoModels.value.length > 0) {
    selectedVideoModel.value = videoModels.value[0].id
  }
  
  await loadProjectData()
  
  // 只有在项目ID匹配时才加载关键帧和视频片段
  if (projectStore.currentProject?.id === projectId.value) {
    await loadKeyframes()
    await loadVideoSegments()
  }
  
  // 再次确保selectedVideoModel有值（可能在loadProjectData后需要重置）
  await nextTick()
  if (!selectedVideoModel.value && videoModels.value.length > 0) {
    selectedVideoModel.value = videoModels.value[0].id
  }
})

// 路由激活时重新加载项目数据
onActivated(async () => {
  console.log('[onActivated] 组件激活，projectId:', projectId.value)
  
  // 先停止所有轮询
  stopPolling()
  stopVideoPolling()
  
  // 强制重新初始化数据（无论是否有项目ID）
  // 这样可以确保连续生成脚本时数据被正确刷新
  await nextTick()
  await loadProjectData()
  
})

onUnmounted(() => {
  stopPolling()
  stopVideoPolling()
})
</script>

<style>
.script-generation .el-textarea__inner{
  box-shadow: none !important;
}
</style>

<style scoped>
.script-generation {
  width: 100%;
  height: 100%;
  background-color: #3f3f3f;
  display: flex;
  gap: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.main-content {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow-y: auto;
}

/* 历史记录容器 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
}

.history-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  box-sizing: border-box;
}


.conversation-message {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-message {
  align-items: flex-end;
}

.ai-message {
  align-items: flex-start;
}

.message-label {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 12px;
  color: #999999;
  font-weight: 400;
  padding: 0 4px;
}

.user-message .message-label {
  color: #00aaaa;
}

.ai-message .message-label {
  color: #999999;
}

.message-content-wrapper {
  width: 100%;
  max-width: 100%;
}

.message-content {
  background-color: #ffffff;
  border: 1px solid #797979;
  border-radius: 10px;
  padding: 16px;
  max-width: 100%;
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 15px;
  line-height: 19px;
  color: #333333;
  word-wrap: break-word;
  text-align: justify;
  white-space: pre-wrap;
}

/* 可编辑的脚本内容 */
.script-content-editable {
  width: 100%;
  min-height: 200px;
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 15px;
  line-height: 19px;
  color: #333333;
  border: 1px solid #797979;
  border-radius: 10px;
  padding: 16px;
  outline: none;
  resize: none;
  background-color: #ffffff;
  box-sizing: border-box;
  overflow-y: auto;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.script-content-editable::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.script-content-editable::placeholder {
  color: #999999;
}

/* 只读的脚本内容 */
.script-content-readonly {
  background-color: #ffffff;
  border: 1px solid #797979;
  border-radius: 10px;
  padding: 16px;
  max-width: 100%;
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 15px;
  line-height: 19px;
  color: #333333;
  word-wrap: break-word;
  text-align: justify;
  white-space: pre-wrap;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}

.script-content-readonly:hover {
  border-color: #00aaaa;
  background-color: #f5f5f5;
}

.user-message .message-content {
  background-color: #e6f7f7;
  border-color: #00aaaa;
}

.ai-message .message-content {
  background-color: #ffffff;
  border-color: #797979;
}

.message-content.loading {
  color: #999999;
  font-style: italic;
}


/* 操作按钮区域 - 脚本框下方 */
.action-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: nowrap;
  width: 100%;
}

.conversation-action-controls {
  flex-wrap: wrap;
}

/* 底部输入区域 - 保持左右边距，为右侧对话区域留出空间 */
.action-section {
  width: 100%;
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 0;
  background: rgba(0, 170, 170, 0.12);
  border: 1px solid rgba(0, 170, 170, 0.35);
  border-radius: 16px;
}

.control-select {
  height: 32px;
  flex-shrink: 0;
}

.control-select:first-child {
  width: 200px;
}

.control-select:nth-of-type(2) {
  width: 120px;
}

.control-select:nth-of-type(3) {
  width: 120px;
}

.control-select :deep(.el-input__wrapper) {
  background-color: #ffffff;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  box-shadow: none;
  padding: 0 8px;
  height: 32px;
}

.control-select :deep(.el-input__wrapper.is-focus) {
  border-color: #00aaaa;
  box-shadow: none;
}

.control-select :deep(.el-input__inner) {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 12px;
  color: #333333;
  height: 32px;
  line-height: 32px;
}

.control-select :deep(.el-input__inner)::placeholder {
  color: #cccccc;
}

.control-select :deep(.el-input__suffix) {
  height: 32px;
  line-height: 32px;
}

.control-select :deep(.el-select__caret) {
  color: #cccccc;
  font-size: 12px;
}

.generate-button {
  height: 32px;
  width: 97px;
  background-color: #00aaaa;
  border: none;
  border-radius: 4px;
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 400;
  color: #ffffff;
  padding: 0 16px;
  margin-left: auto;
  transition: background-color 0.3s;
  flex-shrink: 0;
}

.generate-button:hover:not(:disabled) {
  background-color: #009999;
}

.generate-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 优化输入区域 - 最底部，保持左右边距 */
.optimization-section {
  width: 100%;
  padding: 0;
  box-sizing: border-box;
}

.optimization-input-wrapper {
  display: flex;
  gap: 0;
  align-items: flex-end;
  background-color: #ffffff;
  border: 1px solid #797979;
  border-radius: 10px;
  padding: 20px;
  min-height: 82px;
  box-sizing: border-box;
  width: 100%;
  transition: border-color 0.3s;
  box-shadow: none;
}

/* 获得焦点时边框颜色，无阴影 */
.optimization-input-wrapper.has-focus {
  border: 1px solid #00aaaa;
  box-shadow: none;
}

.optimization-input {
  flex: 1;
  margin-right: 10px;
}

.optimization-model-select {
  width: 120px;
  height: 32px;
  margin-right: 10px;
  flex-shrink: 0;
}

.optimization-model-select :deep(.el-input__wrapper) {
  background-color: #ffffff;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  box-shadow: none;
  padding: 0 8px;
  height: 32px;
}

.optimization-model-select :deep(.el-input__wrapper.is-focus) {
  border-color: #00aaaa;
  box-shadow: none;
}

.optimization-model-select :deep(.el-input__wrapper.is-disabled) {
  background-color: #f5f5f5;
  border-color: #d9d9d9;
  cursor: not-allowed;
}

.optimization-model-select :deep(.el-input__inner) {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 12px;
  color: #333333;
  height: 32px;
  line-height: 32px;
}

.optimization-model-select :deep(.el-input__inner)::placeholder {
  color: #cccccc;
}

.optimization-model-select :deep(.el-input__suffix) {
  height: 32px;
  line-height: 32px;
}

.optimization-model-select :deep(.el-select__caret) {
  color: #cccccc;
  font-size: 12px;
}

.optimization-input :deep(.el-textarea__inner) {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 15px;
  line-height: 19px;
  border: none;
  border-radius: 0;
  padding: 0;
  resize: none;
  background: transparent;
  color: #333333;
  min-height: auto;
  height: auto;
}

.optimization-input :deep(.el-textarea__inner):focus {
  border: none;
  box-shadow: none;
  outline: none;
}

.optimization-input :deep(.el-textarea__inner)::placeholder {
  color: #d9d9d9;
}

.optimization-button {
  width: 49px;
  height: 26px;
  background-color: #00aaaa;
  border: none;
  border-radius: 15px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.3s;
  flex-shrink: 0;
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 16px;
  font-weight: 400;
}

.optimization-button:hover:not(:disabled) {
  background-color: #009999;
}

.optimization-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.arrow-up {
  font-size: 16px;
  color: #ffffff;
  line-height: 1;
  font-weight: 400;
}

/* Element Plus下拉选项样式 */
:deep(.el-select-dropdown__item) {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 12px;
  color: #333333;
}

:deep(.el-select-dropdown__item:hover) {
  background-color: #f5f7fa;
}

:deep(.el-select-dropdown__item.is-selected) {
  color: #00aaaa;
  background-color: #e6f7f7;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .script-generation {
    padding: 16px;
    gap: 16px;
  }

  .history-list,
  .action-section {
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .action-controls {
    flex-wrap: wrap;
  }

  .control-select {
    width: calc(50% - 5px) !important;
  }

  .generate-button {
    width: 100%;
    margin-left: 0;
  }
}

/* 可拖动的分隔条 */
.resizer {
  width: 4px;
  background-color: #d9d9d9;
  cursor: ew-resize;
  position: relative;
  transition: background-color 0.2s;
  flex-shrink: 0;
}

.resizer:hover {
  background-color: #00aaaa;
}

.resizer::before {
  content: '';
  position: absolute;
  top: 0;
  left: -4px;
  right: -4px;
  bottom: 0;
}

/* 右侧关键帧面板 */
.keyframe-panel {
  min-width: 360px;
  max-width: 800px;
  background-color: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.panel-header {
  padding: 20px;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #00aaaa;
}

.panel-title {
  font-size: 16px;
  font-weight: 500;
  color: #fff;
  margin: 0;
}

.header-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.video-model-select {
  width: 180px;
  min-width: 180px;
  flex-shrink: 0;
}

.video-model-select :deep(.el-input__wrapper) {
  background-color: #fff;
  border: 1px solid #dcdfe6;
}

.video-model-select :deep(.el-input__wrapper:hover) {
  border-color: #00aaaa;
}

.video-model-select :deep(.el-input__wrapper.is-focus) {
  border-color: #00aaaa;
}

.video-model-select :deep(.el-input__inner) {
  color: #333;
  font-size: 14px;
}

.video-model-select :deep(.el-input__suffix) {
  color: #909399;
}

.confirm-video-btn {
  background-color: #fff;
  color: #00aaaa;
  border: none;
}

.confirm-video-btn:hover:not(:disabled) {
  background-color: #f0f0f0;
}

.back-btn, .save-btn, .next-step-btn {
  background-color: #fff;
  color: #00aaaa;
  border: 1px solid #fff;
}

.back-btn:hover, .save-btn:hover, .next-step-btn:hover {
  background-color: #f0f0f0;
}

.export-btn {
  background-color: #fff;
  color: #00aaaa;
  border: none;
}

.export-btn:hover:not(:disabled) {
  background-color: #f0f0f0;
}

.keyframes-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: #f9f9f9;
}

.keyframe-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.keyframe-card {
  background-color: #fff;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e8e8e8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.card-header {
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e8e8e8;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin: 0;
}

.card-actions {
  display: flex;
  gap: 12px;
}

.action-icon {
  font-size: 18px;
  color: #666;
  cursor: pointer;
  transition: color 0.2s;
}

.action-icon:hover {
  color: #00aaaa;
}

.card-image-area {
  position: relative;
  width: 100%;
  padding-bottom: 56.25%; /* 16:9 */
  background-color: #f5f5f5;
  overflow: hidden;
}

.image-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.keyframe-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.upload-overlay-btn {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity 0.3s;
}

.image-container:hover .upload-overlay-btn {
  opacity: 1;
}

.image-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.placeholder-icon {
  font-size: 48px;
  opacity: 0.6;
}

.upload-btn {
  background-color: #fff;
  color: #00aaaa;
  border: 1px solid #00aaaa;
}

.upload-btn:hover {
  background-color: #f0f0f0;
}

.card-description {
  padding: 16px;
}

.card-description p {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 视频容器 */
.videos-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background-color: #f9f9f9;
}

.video-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.video-card {
  background-color: #fff;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e8e8e8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.card-video-area {
  position: relative;
  width: 100%;
  padding-bottom: 56.25%; /* 16:9 */
  background-color: #000;
  overflow: hidden;
}

.video-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.video-player {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.loading-icon {
  font-size: 48px;
  color: #fff;
}

.loading-text {
  font-size: 14px;
  color: #fff;
}

.video-error {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  justify-content: center;
  background-color: #fff3f3;
}

.error-icon {
  font-size: 48px;
}

.error-text {
  font-size: 14px;
  color: #ff4d4f;
  text-align: center;
  padding: 0 20px;
}

.retry-btn {
  background-color: #ff4d4f;
  color: #fff;
  border: none;
}

.retry-btn:hover {
  background-color: #ff7875;
}

.video-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
