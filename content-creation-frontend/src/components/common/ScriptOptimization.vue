<template>
  <div class="script-optimization">
    <div class="script-optimization-card">
      <!-- 输入框区域 -->
      <div class="input-section">
        <el-input
          v-model="inputContent"
          type="textarea"
          :placeholder="placeholder"
          :maxlength="3000"
          :rows="8"
          :autosize="{ minRows: 8, maxRows: 20 }"
          class="script-input"
          @focus="handleFocus"
          @blur="handleBlur"
        />
      </div>

      <!-- 控制面板 -->
      <div class="control-panel">
        <div class="control-row">
          <!-- 选择脚本风格 -->
          <el-select
            v-model="formData.style"
            placeholder="选择脚本风格"
            class="control-select"
            clearable
          >
            <el-option
              v-for="style in scriptStyles"
              :key="style.id"
              :label="style.name"
              :value="style.id"
            />
          </el-select>

          <!-- 视频总时长 -->
          <el-input-number
            v-model="formData.totalDuration"
            :min="1"
            :max="3600"
            :step="1"
            placeholder="视频总时长"
            class="control-input"
            :controls="false"
          >
            <template #append>秒</template>
          </el-input-number>

          <!-- 单个视频时长 -->
          <el-input-number
            v-model="formData.segmentDuration"
            :min="5"
            :max="300"
            :step="1"
            placeholder="单个视频时长"
            class="control-input"
            :controls="false"
          >
            <template #append>秒</template>
          </el-input-number>

          <!-- 选择模型 -->
          <ModelSelect
            v-model="formData.model"
            type="script"
            placeholder="选择模型"
            class="control-select"
            clearable
            @change="handleModelChange"
          />

          <!-- 操作按钮 -->
          <el-button
            type="primary"
            :loading="loading"
            :disabled="loading"
            class="action-button"
            @click="handleSubmit"
          >
            {{ buttonText }}
          </el-button>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="errorMessage" class="error-message">
        <el-alert
          :title="errorMessage"
          type="error"
          :closable="false"
          show-icon
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { scriptApi, modelApi, projectApi } from '@/api'
import { useProjectStore } from '@/stores'
import type { GenerateScriptRequest } from '@/types'
import ModelSelect from './ModelSelect.vue'

interface Props {
  /** 输入框占位符 */
  placeholder: string
  /** 按钮文字 */
  buttonText: string
  /** 模式：inspiration（从灵感开始）或 script（从脚本开始） */
  mode: 'inspiration' | 'script'
  /** 初始内容（用于编辑场景） */
  initialContent?: string
}

const props = withDefaults(defineProps<Props>(), {
  initialContent: ''
})

const emit = defineEmits<{
  success: [data: any]
  error: [error: string]
}>()

const router = useRouter()
const projectStore = useProjectStore()

// 表单数据
const inputContent = ref(props.initialContent)
const formData = ref<{
  style: string
  totalDuration: number | null
  segmentDuration: number | null
  model: string
}>({
  style: '',
  totalDuration: null,
  segmentDuration: 6, // 默认6秒
  model: '' // 默认模型
})

// 状态
const loading = ref(false)
const errorMessage = ref('')
const isFocused = ref(false)

// 选项数据
const scriptStyles = ref<{ id: string; name: string; description: string }[]>([])

// 加载脚本风格选项
const loadScriptStyles = async () => {
  try {
    const response = await modelApi.getScriptStyles()
    // request拦截器已经返回了data部分，所以response就是data数组
    scriptStyles.value = Array.isArray(response) ? response : (response?.data || [])
  } catch (error) {
    console.error('加载脚本风格失败:', error)
  }
}

// 模型变化处理
const handleModelChange = (modelId: string) => {
  formData.value.model = modelId
}

// 监听视频总时长和单个视频时长变化，验证总时长必须大于单个视频时长
watch(
  [() => formData.value.totalDuration, () => formData.value.segmentDuration],
  ([totalDuration, segmentDuration]) => {
    if (totalDuration && segmentDuration && totalDuration <= segmentDuration) {
      errorMessage.value = `视频总时长必须大于单个视频时长（${segmentDuration}秒）`
    } else {
      errorMessage.value = ''
    }
  }
)

// 输入框聚焦处理
const handleFocus = () => {
  isFocused.value = true
  errorMessage.value = ''
}

// 输入框失焦处理
const handleBlur = () => {
  isFocused.value = false
}

// 表单验证
const validateForm = (): boolean => {
  errorMessage.value = ''

  // 验证输入内容
  if (!inputContent.value || inputContent.value.trim().length === 0) {
    errorMessage.value = props.mode === 'inspiration'
      ? '请输入创意描述'
      : '请输入脚本内容'
    return false
  }

  // 验证脚本风格
  if (!formData.value.style) {
    errorMessage.value = '请选择脚本风格'
    return false
  }

  // 验证视频总时长
  if (!formData.value.totalDuration || formData.value.totalDuration <= 0) {
    errorMessage.value = '请输入视频总时长'
    return false
  }

  // 验证单个视频时长
  if (!formData.value.segmentDuration || formData.value.segmentDuration <= 0) {
    errorMessage.value = '请输入单个视频时长'
    return false
  }

  // 验证视频总时长必须大于单个视频时长
  if (formData.value.totalDuration <= formData.value.segmentDuration) {
    errorMessage.value = `视频总时长必须大于单个视频时长（${formData.value.segmentDuration}秒）`
    return false
  }

  // 验证模型选择
  if (!formData.value.model) {
    errorMessage.value = '请选择模型'
    return false
  }

  return true
}

// 提交处理
const handleSubmit = async () => {
  if (!validateForm()) {
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const requestData: GenerateScriptRequest = {
      inspiration: inputContent.value.trim(),
      style: formData.value.style,
      totalDuration: formData.value.totalDuration!,
      segmentDuration: formData.value.segmentDuration!
    }

    // 注意：生成新脚本时，不传递项目ID，让后端自动创建新项目
    // 这样可以确保每次生成脚本都会创建新项目，而不是在现有项目中创建新脚本
    // 如果需要在现有项目中创建新脚本，应该使用优化脚本功能

    // 生成脚本前，清空当前项目和脚本（避免显示旧数据）
    projectStore.setCurrentProject(null)
    
    // 调用脚本生成API，后端会自动创建项目和脚本
    const script = await scriptApi.generateScript(requestData, formData.value.model)
    // request 拦截器已经返回了 data.data，所以 script 就是 Script 对象

    // 从后端获取完整的项目信息（包含脚本）
    if (script?.projectId) {
      try {
        const project = await projectApi.getProject(script.projectId)
        // request拦截器已经返回了data部分，所以project就是项目对象
        
        // 处理脚本数据：如果返回的是 scripts 数组，取第一个作为 script
        const projectWithScript = project as any
        if (projectWithScript.scripts && Array.isArray(projectWithScript.scripts) && projectWithScript.scripts.length > 0) {
          projectWithScript.script = projectWithScript.scripts[0]
        } else if (!projectWithScript.script && script) {
          // 如果没有 script 字段，使用返回的脚本数据
          projectWithScript.script = script
        }
        
        projectStore.setCurrentProject(projectWithScript)
        projectStore.addProject(projectWithScript) // 添加到项目列表
        
        // 更新最近项目列表
        try {
          const response = await projectApi.getProjects({ page: 1, pageSize: 10 })
          projectStore.setProjects(response.items || [])
        } catch (error) {
          console.error('获取最近项目列表失败:', error)
        }
      } catch (error) {
        console.error('获取项目信息失败:', error)
        // 如果获取项目失败，使用脚本信息构建项目对象作为后备方案
        const projectName = inputContent.value.trim()
        const displayName = projectName.length > 10 ? projectName.substring(0, 10) + '...' : projectName
        const fallbackProject = {
          id: script.projectId,
          name: displayName || '未命名项目',
          description: inputContent.value.trim().substring(0, 500),
          status: 'script_generated' as const,
          conversationContent: inputContent.value.trim(),
          script: script,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        }
        projectStore.setCurrentProject(fallbackProject)
        projectStore.addProject(fallbackProject as any)
      }
    }

    // 确保脚本内容正确更新到 store（强制更新，避免缓存问题）
    if (script && projectStore.currentProject) {
      // 强制更新脚本内容
      projectStore.updateScript(script)
      await nextTick()
    }

    ElMessage.success('脚本生成成功')
    emit('success', script)

    // 跳转到脚本生成页面，传递项目ID作为路由参数
    // 等待 store 更新完成
    await nextTick()
    await nextTick()
    
    // 额外等待，确保项目列表更新完成
    await new Promise(resolve => setTimeout(resolve, 100))
    
    const newProjectId = projectStore.currentProject?.id
    
    // 传递项目ID作为路由参数，确保页面正确加载新项目的数据
    if (newProjectId) {
      await router.push({ 
        name: 'ScriptGeneration',
        params: { projectId: newProjectId.toString() }
      })
    } else {
      // 如果没有项目ID，仍然跳转但不传递参数（后备方案）
      await router.push({ name: 'ScriptGeneration' })
    }
  } catch (error: any) {
    console.error('生成脚本失败:', error)
    console.error('错误详情:', {
      message: error?.message,
      response: error?.response,
      data: error?.response?.data,
      detail: error?.response?.data?.detail
    })
    
    // 优先显示后端返回的详细错误信息
    let errorMsg = '操作失败，请重试'
    if (error?.response?.data?.detail) {
      errorMsg = error.response.data.detail
    } else if (error?.response?.data?.message) {
      errorMsg = error.response.data.message
    } else if (error?.message) {
      errorMsg = error.message
    }
    
    errorMessage.value = errorMsg
    ElMessage.error(errorMsg)
    emit('error', errorMsg)
  } finally {
    loading.value = false
  }
}

// 初始化
onMounted(() => {
  loadScriptStyles()
})
</script>

<style scoped>
.script-optimization {
  width: 100%;
  height: 100%;
  background-color: #3f3f3f;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0;
  margin: 0;
}

.script-optimization-card {
  width: 800px;
  min-height: 270px;
  background-color: #ffffff;
  border: 1px solid #cccccc;
  border-radius: 10px;
  padding: 0;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: visible;
}

.input-section {
  flex: 1;
  padding: 24px 24px 16px 24px;
  display: flex;
  align-items: flex-start;
  min-height: 180px;
}

.script-input {
  width: 100%;
  height: 100%;
}

.script-input :deep(.el-textarea) {
  height: 100%;
}

.script-input :deep(.el-textarea__inner) {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 14px;
  line-height: 1.6;
  border: none;
  background: transparent;
  padding: 0;
  color: #333333;
  resize: none;
  box-shadow: none;
  height: 100% !important;
  min-height: auto;
}

.script-input :deep(.el-textarea__inner)::placeholder {
  color: #cccccc;
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
}

.script-input :deep(.el-textarea__inner):focus {
  border: none;
  box-shadow: none;
  outline: none;
}

.script-input :deep(.el-input__count) {
  display: none;
}

.control-panel {
  padding: 0 24px 24px 24px;
  flex-shrink: 0;
}

.control-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: nowrap;
}

.control-select {
  height: 32px;
  flex-shrink: 0;
}

.control-select:first-child {
  width: 150px;
}

.control-select:nth-of-type(2) {
  width: 130px;
}

.control-select:last-of-type {
  width: 120px;
}

.control-select :deep(.el-input__wrapper) {
  background-color: #f5f5f5;
  border: 1px solid #cccccc;
  border-radius: 4px;
  box-shadow: none;
  padding: 0 11px;
  height: 32px;
}

.control-select :deep(.el-input__wrapper.is-disabled) {
  background-color: #f5f5f5;
  border-color: #cccccc;
  cursor: not-allowed;
}

.control-select :deep(.el-input__inner.is-disabled) {
  color: #666666;
  -webkit-text-fill-color: #666666;
}

.control-select :deep(.el-input__inner) {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 12px;
  color: #999999;
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

.control-input {
  height: 32px;
  width: 130px;
  flex-shrink: 0;
}

.control-input :deep(.el-input__wrapper) {
  background-color: #ffffff;
  border: 1px solid #cccccc;
  border-radius: 4px;
  box-shadow: none !important;
  padding: 0 11px;
  height: 32px;
}

.control-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: none !important;
  border-color: #cccccc;
}

.control-input :deep(.el-input__wrapper:hover) {
  box-shadow: none !important;
}

.control-input :deep(.el-input__inner) {
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 12px;
  color: #333333;
  height: 32px;
  line-height: 32px;
  text-align: left;
  box-shadow: none !important;
}

.control-input :deep(.el-input__inner:focus) {
  box-shadow: none !important;
  outline: none !important;
}

.control-input :deep(.el-input__inner)::placeholder {
  color: #cccccc;
}

.control-input :deep(.el-input-group__append) {
  background-color: #ffffff;
  border: none;
  border-left: 1px solid #cccccc;
  color: #666666;
  font-size: 12px;
  padding: 0 11px;
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
}

.action-button {
  width: 100px;
  height: 32px;
  background-color: #00aaaa;
  border: none;
  border-radius: 4px;
  font-family: 'PingFangSC-Regular', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 400;
  color: #ffffff;
  padding: 0;
  flex-shrink: 0;
  margin-left: auto;
  transition: background-color 0.3s;
}

.action-button:hover:not(:disabled) {
  background-color: #009999;
}

.action-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  padding: 0 24px 12px 24px;
}

.error-message :deep(.el-alert) {
  border-radius: 4px;
  font-size: 12px;
}

/* 下拉选项样式 */
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
@media (max-width: 1200px) {
  .script-optimization-card {
    width: 90%;
    max-width: 800px;
  }
}

@media (max-width: 768px) {
  .script-optimization-card {
    width: 95%;
    min-height: auto;
  }

  .input-section {
    min-height: 150px;
  }

  .control-row {
    flex-wrap: wrap;
    gap: 8px;
  }

  .control-select,
  .control-input {
    width: calc(50% - 4px);
  }

  .action-button {
    width: 100%;
    margin-left: 0;
  }
}
</style>

