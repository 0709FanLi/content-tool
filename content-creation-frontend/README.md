# 内容创作前端

基于 Vue 3 + Element Plus + Vite + Pinia 构建的内容创作平台前端应用。

## 技术栈

- **Vue 3**: 使用 Composition API 和 `<script setup>` 语法
- **Element Plus**: 企业级 Vue 组件库
- **Vite**: 快速构建工具
- **Pinia**: Vue 3 官方状态管理库
- **Vue Router**: 单页应用路由管理
- **Axios**: HTTP 请求库
- **TypeScript**: 类型安全

## 项目结构

```
src/
├── api/                 # API 接口层
├── components/          # 组件
│   ├── common/         # 通用组件
│   └── layout/         # 布局组件
├── views/              # 页面组件
├── stores/             # Pinia 状态管理
├── router/             # 路由配置
├── types/              # TypeScript 类型定义
├── utils/              # 工具函数
├── composables/        # Vue 组合式函数
├── styles/             # 全局样式
└── assets/             # 静态资源
```

## 环境配置

复制 `.env.example` 文件为相应环境的配置文件：

```bash
# 开发环境
cp .env.example .env.development

# 生产环境
cp .env.example .env.production
```

### 环境变量

```env
# 应用标题
VITE_APP_TITLE=内容创作平台

# API 基础 URL
VITE_APP_API_BASE_URL=http://localhost:8000/api

# 环境标识
VITE_APP_ENV=development
```

## 安装依赖

```bash
npm install
```

## 开发运行

```bash
npm run dev
```

## 构建生产版本

```bash
npm run build
```

## 代码检查

```bash
# 类型检查
npm run type-check

# 代码格式化
npm run format

# ESLint 检查
npm run lint
```

## 主要功能

1. **输入灵感**: 用户输入创意描述，选择脚本风格和时长参数，生成脚本
2. **从脚本开始**: 用户直接输入或粘贴脚本，进行优化
3. **生成脚本**: 显示和编辑生成的脚本，配置AI模型参数
4. **生成关键帧**: 三栏布局，生成和编辑关键帧图片
5. **生成视频**: 生成视频片段，导出ZIP包

## 开发规范

- 使用 TypeScript 确保类型安全
- 遵循 Vue 3 Composition API 最佳实践
- 使用 ESLint + Prettier 保证代码风格一致性
- 组件化开发，提高代码复用性
- 状态管理使用 Pinia，按功能模块划分store

## 浏览器支持

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
