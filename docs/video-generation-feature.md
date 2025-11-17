# 视频生成功能开发文档

## 功能概述

本次开发实现了从关键帧生成视频的完整功能，包括：

1. 视频模型选择
2. 视频生成（使用首尾帧方法）
3. 视频展示和播放
4. 视频重新生成
5. 视频导出（zip格式）

## 技术实现

### 后端实现

#### 1. 视频生成逻辑（方案B）

根据脚本的关键帧，使用首尾帧方法生成N段视频：

- **第1段**：segment_0_first_frame → segment_0（使用segment_0的文本作为prompt）
- **第2段**：segment_0 → segment_1（使用segment_1的文本作为prompt）
- **第3段**：segment_1 → segment_2（使用segment_2的文本作为prompt）
- **第N段**：segment_(n-2) → segment_(n-1)（使用segment_(n-1)的文本作为prompt）

**注意**：不使用last_frame

#### 2. 默认配置

- **默认模型**：veo3.1-fast
- **视频时长**：固定6秒
- **视频比例**：16:9
- **Prompt**：使用段落原始文本

#### 3. API接口

```
GET  /api/videos/models                    # 获取可用的视频模型列表
POST /api/videos/generate                  # 生成视频
GET  /api/videos/script/{script_id}        # 获取脚本的视频列表
POST /api/videos/{id}/regenerate           # 重新生成单个视频
POST /api/videos/export                    # 导出所有视频为zip
```

#### 4. 视频生成服务

文件：`content-creation-backend/src/services/video_service.py`

主要方法：
- `generate_videos()` - 批量生成视频
- `_call_veo_api()` - 调用Veo API生成视频
- `_generate_single_video_with_session()` - 生成单个视频并转存到OSS
- `regenerate_video_segment()` - 重新生成单个视频片段
- `export_videos()` - 导出视频为zip文件

**视频转存OSS流程**：
1. 调用第三方API（Veo）生成视频，获取临时URL
2. 使用 `oss_service.upload_from_url()` 从临时URL下载视频
3. 将视频上传到阿里云OSS的 `videos` 目录
4. 保存OSS的永久URL到数据库
5. 前端显示OSS的URL（非临时URL）

### 前端实现

#### 1. 页面布局

文件：`content-creation-frontend/src/views/KeyframeGeneration.vue`

**关键帧视图**：
- 左侧：视频模型选择框
- 右侧："关键帧确认，生成视频"按钮

**视频视图**：
- 显示所有生成的视频片段
- 支持视频播放（HTML5 video标签）
- 显示生成状态（生成中、已完成、失败）
- 提供"上一步"、"保存"、"确认视频，导出（*zip）"按钮

#### 2. 视频状态管理

```typescript
// 视频相关状态
const showVideoView = ref<boolean>(false)           // 是否显示视频视图
const videoSegments = ref<VideoSegment[]>([])      // 视频片段列表
const videoModels = ref<any[]>([])                 // 可用的视频模型
const selectedVideoModel = ref<string>('veo3.1-fast') // 选中的视频模型
const generatingVideos = ref<boolean>(false)       // 是否正在生成视频
const exporting = ref<boolean>(false)              // 是否正在导出
```

#### 3. 核心功能

- **生成视频**：`handleGenerateVideos()`
- **返回关键帧**：`handleBackToKeyframes()`
- **重新生成**：`handleRefreshVideo()`
- **导出视频**：`handleExportVideos()`
- **轮询更新**：`startVideoPolling()` / `stopVideoPolling()`

#### 4. 类型定义

文件：`content-creation-frontend/src/types/api.ts`

```typescript
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
```

## 使用流程

### 1. 生成关键帧

用户先在关键帧生成页面完成关键帧的生成。

### 2. 选择视频模型

在右侧面板顶部的下拉框中选择视频生成模型（默认：veo3.1-fast）。

### 3. 生成视频

点击"关键帧确认，生成视频"按钮，系统将：
- 自动切换到视频视图
- 开始生成N段视频
- 显示生成进度
- 每3秒轮询一次更新状态

### 4. 视频展示

视频生成完成后：
- 可以点击播放查看视频
- 如果生成失败，可以点击重新生成
- 视频默认不自动播放

### 5. 返回关键帧

点击"上一步"按钮可以返回关键帧视图，查看或修改关键帧。

### 6. 导出视频

所有视频生成完成后：
- 点击"确认视频，导出（*zip）"按钮
- 系统将所有视频打包成zip文件
- 自动下载到本地

## 注意事项

### 1. 视频生成逻辑

- 采用方案B：生成N个视频（不使用last_frame）
- 假设有3个段落（segment_0, segment_1, segment_2）：
  - 关键帧：segment_0_first_frame, segment_0, segment_1, segment_2
  - 生成3个视频

### 2. 视频时长

- 固定为6秒
- 视频片段标题显示时间范围：如 `(0:0 - 6s) 第1段`

### 3. Prompt处理

- 使用段落原始文本作为prompt
- 不可修改（去除了修改图标）

### 4. 错误处理

- 如果某段视频生成失败，整个流程停止
- 用户需要手动点击重新生成失败的视频

### 5. 视频存储

- ✅ 视频生成后自动转存到阿里云OSS
- ✅ 前端显示的是OSS永久URL
- ✅ OSS配置在环境变量中（`.env`文件）：
  - `OSS_ACCESS_KEY_ID` - OSS访问密钥ID
  - `OSS_ACCESS_KEY_SECRET` - OSS访问密钥
  - `OSS_ENDPOINT` - OSS endpoint（如：oss-cn-shanghai.aliyuncs.com）
  - `OSS_BUCKET_NAME` - OSS bucket名称
  - `OSS_PUBLIC_READ` - 是否公共读（true/false）

## 测试建议

### 1. 功能测试

- [ ] 测试关键帧生成后切换到视频视图
- [ ] 测试视频模型选择功能
- [ ] 测试视频生成流程（N段视频）
- [ ] 测试视频播放功能
- [ ] 测试重新生成单个视频
- [ ] 测试返回关键帧视图
- [ ] 测试视频导出功能

### 2. 边界测试

- [ ] 测试关键帧未完成时的提示
- [ ] 测试视频生成失败的处理
- [ ] 测试网络异常时的错误提示
- [ ] 测试视频导出失败的处理
- [ ] 测试大量视频片段的性能

### 3. UI测试

- [ ] 测试视频模型选择框样式
- [ ] 测试视频列表布局
- [ ] 测试视频播放器显示
- [ ] 测试加载状态动画
- [ ] 测试错误状态显示
- [ ] 测试按钮状态（禁用/启用）

## 已知问题

1. 视频生成时间较长（每段视频约1-2分钟）
2. 视频上传到OSS需要额外时间（取决于视频大小和网络）
3. 轮询频率固定为3秒（可能需要优化）
4. OSS存储空间需要定期清理（可添加定时清理任务）

## 未来优化

1. 添加视频预览缩略图
2. 支持视频编辑功能
3. 支持批量重新生成
4. 优化轮询机制（使用WebSocket）
5. 添加视频生成进度条
6. 支持视频格式选择
7. 添加视频质量设置
8. 支持视频下载单个文件

## 开发总结

本次开发完成了从关键帧生成视频的完整功能链路，包括后端API、前端UI和业务逻辑。代码遵循了项目规范，使用了TypeScript类型定义，实现了良好的错误处理和用户体验。

